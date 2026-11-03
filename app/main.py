import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api import router
from app.config import get_settings
from app.db import engine
from app.models import User

logger = logging.getLogger("brain.api")


def create_app() -> FastAPI:
    settings = get_settings()
    api = FastAPI(title="Cognitive Second Brain", version="0.1.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    attempts = defaultdict(deque)
    lock = Lock()

    @api.middleware("http")
    async def request_controls(request, call_next):
        request_id = str(uuid4())
        # Use the socket peer, never an untrusted X-Forwarded-For header.
        if request.url.path in ("/api/v1/auth/login", "/api/v1/auth/register"):
            peer = request.client.host if request.client else "unknown"
            current = monotonic()
            with lock:
                for key in list(attempts):
                    if not attempts[key] or attempts[key][-1] <= current - 60:
                        del attempts[key]
                bucket = attempts[peer]
                while bucket and bucket[0] <= current - 60:
                    bucket.popleft()
                limited = len(bucket) >= settings.auth_rate_limit
                if not limited:
                    bucket.append(current)
            if limited:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many attempts"},
                    headers={"Retry-After": "60", "X-Request-ID": request_id},
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request_id=%s method=%s path=%s status=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    @api.get("/health/live", tags=["health"])
    def live():
        return {"status": "ok"}

    @api.get("/health/ready", tags=["health"])
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(select(User.id).limit(1))
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ready"}

    api.include_router(router)
    return api


app = create_app()
