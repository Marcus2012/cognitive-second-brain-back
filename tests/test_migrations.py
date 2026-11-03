import os
import subprocess
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.config import get_settings
from app.db import make_engine


def test_postgresql_sql_is_fully_scoped_to_application():
    env = {
        **os.environ,
        "BRAIN_DATABASE_URL": "postgresql+psycopg://unused/brain",
        "BRAIN_DATABASE_SCHEMA": "cognitive_brain",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    sql = result.stdout
    for table in ("users", "workspaces", "memberships", "audit_events", "alembic_version"):
        assert f"CREATE TABLE cognitive_brain.{table}" in sql
    assert "REFERENCES cognitive_brain.users" in sql
    assert "REFERENCES cognitive_brain.workspaces" in sql
    assert "public." not in sql
    assert "auth." not in sql
    assert "DROP " not in sql


def test_migrations_upgrade_check_and_downgrade(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "migrations.db").as_posix()
    monkeypatch.setenv("BRAIN_DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        engine = make_engine(url)
        assert {"users", "workspaces", "memberships", "audit_events"}.issubset(
            inspect(engine).get_table_names(),
        )
        engine.dispose()
        command.check(config)
        command.downgrade(config, "base")
        engine = make_engine(url)
        assert inspect(engine).get_table_names() == ["alembic_version"]
        engine.dispose()
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()
