from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash("dummy-password-for-constant-work")
bearer = HTTPBearer(auto_error=False)


def issue_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user.id,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": "cognitive-second-brain",
            "aud": "brain-api",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    error = HTTPException(
        401,
        "Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            audience="brain-api",
            issuer="cognitive-second-brain",
            options={"require": ["sub", "iat", "exp"]},
        )
        user = db.get(User, payload["sub"])
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise error from None
    if user is None or not user.is_active:
        raise error
    return user
