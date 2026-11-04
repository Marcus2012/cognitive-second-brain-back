from sqlalchemy import MetaData, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.schema import CreateSchema

from app.config import get_settings


class Base(DeclarativeBase):
    metadata = MetaData(
        schema=(
            get_settings().database_schema
            if get_settings().database_url.startswith("postgresql")
            else None
        )
    )


def make_engine(url: str, **kwargs):
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        hide_parameters=True,
        **kwargs,
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def ensure_schema(connection, schema: str):
    # PostgreSQL checks database CREATE privilege even with IF NOT EXISTS.
    # Pre-provisioned schemas must work for a role without that privilege.
    if not inspect(connection).has_schema(schema):
        connection.execute(CreateSchema(schema, if_not_exists=True))


def get_db():
    with SessionLocal() as session:
        yield session
