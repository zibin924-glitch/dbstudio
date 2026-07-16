"""Initial schema -- create all DBStudio tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

Creates: connections, query_histories, api_definitions, api_call_logs, audit_logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- connections --
    op.create_table(
        "connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, comment="Display name"),
        sa.Column(
            "db_type",
            sa.String(length=20),
            nullable=False,
            comment="One of: mysql, postgresql, oracle",
        ),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column(
            "password_encrypted",
            sa.Text(),
            nullable=False,
            comment="AES-256 encrypted password (base64)",
        ),
        sa.Column("database_name", sa.String(length=100), nullable=True),
        sa.Column(
            "extra_params",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded driver-specific parameters",
        ),
        sa.Column("group_name", sa.String(length=50), nullable=False, server_default="default"),
        sa.Column(
            "tags", sa.Text(), nullable=True, comment="JSON-encoded list of tag strings"
        ),
        sa.Column("pool_size", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "read_only", sa.Boolean(), nullable=False, server_default="0",
            comment="Server-side read-only mode: enforces SELECT-only queries regardless of request parameter",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # -- query_histories --
    op.create_table(
        "query_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column("execution_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=True, comment="success or error"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_histories_connection_id", "query_histories", ["connection_id"])

    # -- api_definitions --
    op.create_table(
        "api_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False, server_default="GET"),
        sa.Column(
            "url_path",
            sa.String(length=255),
            unique=True,
            nullable=False,
            comment="Public URL path",
        ),
        sa.Column("sql_template", sa.Text(), nullable=False),
        sa.Column(
            "params_definition",
            sa.Text(),
            nullable=True,
            comment="JSON schema describing accepted parameters",
        ),
        sa.Column(
            "connection_id",
            sa.Integer(),
            sa.ForeignKey("connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("result_limit", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("cache_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "auth_type",
            sa.String(length=20),
            nullable=False,
            server_default="none",
            comment="none | token | basic",
        ),
        sa.Column("auth_token", sa.String(length=255), nullable=True),
        sa.Column(
            "ip_whitelist",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded list of allowed CIDR blocks",
        ),
        sa.Column(
            "rate_limit",
            sa.Text(),
            nullable=True,
            comment="JSON object for rate limiting config",
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("version", sa.String(length=20), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_definitions_connection_id", "api_definitions", ["connection_id"])

    # -- api_call_logs --
    op.create_table(
        "api_call_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "api_id",
            sa.Integer(),
            sa.ForeignKey("api_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "request_params",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded request parameters",
        ),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("caller_ip", sa.String(length=50), nullable=True),
        sa.Column("called_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_call_logs_api_id", "api_call_logs", ["api_id"])

    # -- audit_logs --
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "action",
            sa.String(length=20),
            nullable=False,
            comment="Action type: create, update, delete",
        ),
        sa.Column(
            "resource_type",
            sa.String(length=50),
            nullable=False,
            comment="Resource type: connection, api, query, ddl_export",
        ),
        sa.Column(
            "resource_id",
            sa.String(length=100),
            nullable=True,
            comment="Primary key or identifier of the affected resource",
        ),
        sa.Column(
            "user_info",
            sa.String(length=255),
            nullable=True,
            comment="User identifier or system label",
        ),
        sa.Column(
            "details",
            sa.JSON(),
            nullable=True,
            comment="Arbitrary JSON details about the action",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("api_call_logs")
    op.drop_table("api_definitions")
    op.drop_table("query_histories")
    op.drop_table("connections")
