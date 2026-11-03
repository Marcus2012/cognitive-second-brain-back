from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BRAIN_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = Field(
        default="sqlite:///./brain.db",
        validation_alias=AliasChoices("BRAIN_DATABASE_URL", "DATABASE_URL"),
    )
    database_schema: str = Field(default="cognitive_brain", pattern=r"^[a-z][a-z0-9_]{0,62}$")
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = ["http://localhost:3000"]
    auth_rate_limit: int = Field(default=20, ge=1)

    @field_validator("database_url")
    @classmethod
    def normalize_connection(cls, value):
        url = make_url(value)
        if url.drivername in {"postgres", "postgresql", "postgresql+asyncpg"}:
            url = url.set(drivername="postgresql+psycopg")
        if url.host and url.host.endswith((".supabase.co", ".supabase.com")):
            if "sslmode" not in url.query:
                url = url.update_query_dict({"sslmode": "require"})
        return url.render_as_string(hide_password=False)

    @model_validator(mode="after")
    def production_settings(self):
        if self.database_schema in {
            "public",
            "auth",
            "storage",
            "extensions",
            "information_schema",
        } or self.database_schema.startswith("pg_"):
            raise ValueError("Use a dedicated application schema")
        if self.environment == "production":
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
            if self.jwt_secret.startswith("replace-"):
                raise ValueError("Replace the example JWT secret")
            if "*" in self.cors_origins:
                raise ValueError("Production requires explicit CORS origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
