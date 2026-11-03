import os

os.environ["BRAIN_ENVIRONMENT"] = "test"
os.environ["BRAIN_JWT_SECRET"] = "test-only-secret-with-more-than-thirty-two-characters"
os.environ["BRAIN_DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session():
        with factory() as db:
            yield db

    api = create_app()
    api.dependency_overrides[get_db] = session
    with TestClient(api) as http:
        yield http
    engine.dispose()


@pytest.fixture
def account(client):
    def create(email="owner@example.com", password="test-password-12345"):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "name": "Example",
                "password": password,
            },
        )
        assert response.status_code == 201, response.text
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    return create
