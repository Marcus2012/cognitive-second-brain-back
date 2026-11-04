from alembic import context
from sqlalchemy import pool

from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base, ensure_schema, make_engine

config = context.config
settings = get_settings()
url = settings.database_url
schema = settings.database_schema if url.startswith("postgresql") else None


def include_name(name, type_, parent_names):
    # Never autogenerate drops for another application's tables.
    if type_ == "schema":
        return name == schema
    if type_ == "table":
        return parent_names.get("schema_name") == schema and name in {
            table.name for table in Base.metadata.tables.values()
        }
    return True


options = dict(
    target_metadata=Base.metadata,
    include_schemas=schema is not None,
    include_name=include_name,
    version_table_schema=schema,
    render_as_batch=schema is None,
)

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, **options)
    with context.begin_transaction():
        if schema:
            context.execute("-- Prerequisite: application schema provisioned by administrator")
        context.run_migrations()
else:
    engine = make_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            **options,
        )
        with context.begin_transaction():
            if schema:
                ensure_schema(connection, schema)
            context.run_migrations()
