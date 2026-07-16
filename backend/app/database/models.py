"""
SQLAlchemy 2.0 ORM models for DBStudio's local metadata store.

All tables live in a single SQLite database managed by the application.
Remote database credentials are never stored in plain text; the
``password_encrypted`` column holds an AES-256 ciphertext produced by
``app.utils.crypto``.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """Shared declarative base for all DBStudio models."""


# ──────────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────────

class Connection(Base):
    """
    A saved remote database connection.

    Stores everything needed to reconnect to a MySQL, PostgreSQL, or Oracle
    instance: host, port, credentials (encrypted), database name, and
    optional tuning knobs such as pool size and connection parameters.
    """

    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Display name")
    db_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="One of: mysql, postgresql, oracle",
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(
        Text, nullable=False, comment="AES-256 encrypted password (base64)"
    )
    database_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_params: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON-encoded driver-specific parameters"
    )
    group_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default", server_default="default"
    )
    tags: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON-encoded list of tag strings"
    )
    pool_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    query_histories: Mapped[list["QueryHistory"]] = relationship(
        "QueryHistory", back_populates="connection", cascade="all, delete-orphan"
    )
    api_definitions: Mapped[list["ApiDefinition"]] = relationship(
        "ApiDefinition", back_populates="connection", cascade="all, delete-orphan"
    )

    def get_extra_params(self) -> dict:
        """Parse JSON-encoded extra_params into a dict."""
        import json as _json

        if self.extra_params:
            try:
                return _json.loads(self.extra_params)
            except (_json.JSONDecodeError, TypeError):
                pass
        return {}

    def get_tags(self) -> list:
        """Parse JSON-encoded tags into a list."""
        import json as _json

        if self.tags:
            try:
                return _json.loads(self.tags)
            except (_json.JSONDecodeError, TypeError):
                pass
        return []

    def __repr__(self) -> str:
        return f"<Connection id={self.id} name={self.name!r} db_type={self.db_type!r}>"


# ──────────────────────────────────────────────────────────────────────────────
# QueryHistory
# ──────────────────────────────────────────────────────────────────────────────

class QueryHistory(Base):
    """
    Audit trail entry for a SQL statement executed through the query console.

    Records the raw SQL, wall-clock duration, row count, and any error
    that occurred. Users can mark frequently-used queries as favourites.
    """

    __tablename__ = "query_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    execution_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="success or error"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    connection: Mapped["Connection"] = relationship(
        "Connection", back_populates="query_histories"
    )

    def __repr__(self) -> str:
        return (
            f"<QueryHistory id={self.id} status={self.status!r} "
            f"duration_ms={self.duration_ms} created_at={self.created_at!r}>"
        )


# ──────────────────────────────────────────────────────────────────────────────
# ApiDefinition
# ──────────────────────────────────────────────────────────────────────────────

class ApiDefinition(Base):
    """
    A SQL query published as a versioned, access-controlled REST endpoint.

    The ``sql_template`` may contain named placeholders (e.g. ``:user_id``)
    that are filled from query-string or path parameters at call time.
    Security is enforced via ``auth_type``, ``auth_token``, ``ip_whitelist``,
    and ``rate_limit`` fields.
    """

    __tablename__ = "api_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="GET", server_default="GET"
    )
    url_path: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="Public URL path, e.g. /users/active"
    )
    sql_template: Mapped[str] = mapped_column(Text, nullable=False)
    params_definition: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON schema describing accepted parameters"
    )
    connection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000, server_default="1000"
    )
    cache_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    auth_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="none",
        server_default="none",
        comment="none | token | basic",
    )
    auth_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_whitelist: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON-encoded list of allowed CIDR blocks"
    )
    rate_limit: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment='JSON object, e.g. {"rpm": 60, "burst": 10}'
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="v1", server_default="v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    connection: Mapped["Connection"] = relationship(
        "Connection", back_populates="api_definitions"
    )
    call_logs: Mapped[list["ApiCallLog"]] = relationship(
        "ApiCallLog", back_populates="api_definition", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<ApiDefinition id={self.id} name={self.name!r} "
            f"method={self.method!r} url_path={self.url_path!r}>"
        )


# ──────────────────────────────────────────────────────────────────────────────
# ApiCallLog
# ──────────────────────────────────────────────────────────────────────────────

class ApiCallLog(Base):
    """
    Audit record for a single invocation of a published API endpoint.

    Captured for observability, rate-limit accounting, and debugging.
    """

    __tablename__ = "api_call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_params: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON-encoded request parameters"
    )
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    caller_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    called_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    api_definition: Mapped["ApiDefinition"] = relationship(
        "ApiDefinition", back_populates="call_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<ApiCallLog id={self.id} api_id={self.api_id} "
            f"status={self.response_status}>"
        )


# ──────────────────────────────────────────────────────────────────────────────
# AuditLog
# ──────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    General-purpose audit log for tracking create/update/delete actions
    across application resources (connections, API definitions, DDL exports, etc.).

    Each entry records the action type, the affected resource, optional user
    information, a timestamp, and arbitrary JSON details for context.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Action type: create, update, delete",
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Resource type: connection, api, query, ddl_export",
        index=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary key or identifier of the affected resource",
    )
    user_info: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User identifier or system label (e.g. 'system', IP address)",
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Arbitrary JSON details about the action",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"resource_type={self.resource_type!r} resource_id={self.resource_id!r}>"
        )
