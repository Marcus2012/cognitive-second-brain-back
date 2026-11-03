"""Identity, workspaces, membership and audit foundation."""

import sqlalchemy as sa
from alembic import op

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def schema():
    from app.config import get_settings

    if op.get_context().dialect.name == "postgresql":
        return get_settings().database_schema
    return None


def foreign_key(table):
    return f"{schema()}.{table}.id" if schema() else f"{table}.id"


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=schema(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema=schema())
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("plan", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=schema(),
    )
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id", sa.String(36), sa.ForeignKey(foreign_key("workspaces")), nullable=False
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey(foreign_key("users")), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id"),
        schema=schema(),
    )
    op.create_index("ix_memberships_workspace_id", "memberships", ["workspace_id"], schema=schema())
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], schema=schema())
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey(foreign_key("workspaces"))),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey(foreign_key("users")), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=schema(),
    )
    op.create_index(
        "ix_audit_events_workspace_id", "audit_events", ["workspace_id"], schema=schema()
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"], schema=schema())


def downgrade():
    op.drop_table("audit_events", schema=schema())
    op.drop_table("memberships", schema=schema())
    op.drop_table("workspaces", schema=schema())
    op.drop_table("users", schema=schema())
