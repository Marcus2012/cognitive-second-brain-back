import pytest
from pydantic import ValidationError

from app.config import Settings


def test_database_url_fallback_and_driver(monkeypatch):
    monkeypatch.delenv("BRAIN_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db.example.supabase.co/postgres")
    settings = Settings(_env_file=None)
    assert settings.database_url == (
        "postgresql+psycopg://u:p@db.example.supabase.co/postgres?sslmode=require"
    )


def test_brain_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused/other")
    monkeypatch.setenv("BRAIN_DATABASE_URL", "sqlite://")
    assert Settings(_env_file=None).database_url == "sqlite://"


@pytest.mark.parametrize("schema", ["public", "auth", "storage", "pg_catalog", "bad;sql"])
def test_rejects_shared_or_invalid_schema(schema):
    with pytest.raises(ValidationError):
        Settings(database_schema=schema)


def test_production_rejects_sqlite_and_example_secret():
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(environment="production", database_url="sqlite://")
    with pytest.raises(ValidationError, match="example JWT"):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://db/brain",
            jwt_secret="replace-this-with-at-least-32-random-characters",
        )
