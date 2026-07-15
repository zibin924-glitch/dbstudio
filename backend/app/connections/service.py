"""Connection management service - handles CRUD operations and connection testing."""

import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.models import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionUpdate,
)
from app.database.models import Connection
from app.utils.crypto import decrypt, encrypt
from app.config import settings

logger = logging.getLogger(__name__)


def _key() -> str:
    """Return the encryption key from settings."""
    return settings.ENCRYPTION_KEY

# Port defaults per database type
DEFAULT_PORTS = {
    "mysql": 3306,
    "postgresql": 5432,
    "oracle": 1521,
}


class ConnectionService:
    """Service for managing database connections."""

    @staticmethod
    def _build_url(config: dict) -> str:
        """Build a SQLAlchemy connection URL from a configuration dict.

        Args:
            config: Dictionary with keys db_type, host, port, username, password, database_name,
                    and optional extra_params.

        Returns:
            A SQLAlchemy-compatible connection URL string.

        Raises:
            ValueError: If the db_type is not supported.
        """
        driver_map = {
            "mysql": "mysql+pymysql",
            "postgresql": "postgresql+psycopg2",
            "oracle": "oracle+oracledb",
        }

        db_type = config.get("db_type", "").lower()
        if db_type not in driver_map:
            raise ValueError(
                f"Unsupported database type: '{db_type}'. "
                f"Supported types: {', '.join(driver_map.keys())}"
            )

        username = config["username"]
        password = config["password"]
        host = config["host"]
        port = config["port"]
        database = config["database_name"]

        driver = driver_map[db_type]
        url = f"{driver}://{username}:{password}@{host}:{port}/{database}"

        # Append extra params as query string if provided
        extra = config.get("extra_params")
        if extra and isinstance(extra, dict):
            query_parts = [f"{k}={v}" for k, v in extra.items()]
            if query_parts:
                url += "?" + "&".join(query_parts)

        return url

    @staticmethod
    def test_connection(config: dict) -> dict:
        """Test a database connection without persisting it.

        Attempts to connect using SQLAlchemy's create_engine and execute a simple query.

        Args:
            config: Connection configuration dictionary.

        Returns:
            Dictionary with 'status' ('success' or 'error') and 'message'.
        """
        from sqlalchemy import create_engine, text

        try:
            url = ConnectionService._build_url(config)
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        engine = None
        try:
            engine = create_engine(url, connect_args={"connect_timeout": 10})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "success", "message": "Connection successful."}
        except Exception as exc:
            error_msg = str(exc).lower()
            # Map common errors to friendly messages
            if "access denied" in error_msg or "authentication failed" in error_msg:
                return {
                    "status": "error",
                    "message": "Authentication failed. Please check your username and password.",
                }
            elif (
                "timeout" in error_msg
                or "timed out" in error_msg
                or "can't connect" in error_msg
                or "could not connect" in error_msg
                or "connection refused" in error_msg
            ):
                return {
                    "status": "error",
                    "message": (
                        "Connection timed out or refused. "
                        "Please verify the host, port, and firewall settings."
                    ),
                }
            elif "unknown database" in error_msg or "does not exist" in error_msg:
                return {
                    "status": "error",
                    "message": f"Database '{config.get('database_name', '')}' not found on the server.",
                }
            elif "no module" in error_msg or "import" in error_msg:
                return {
                    "status": "error",
                    "message": (
                        "Required database driver is not installed. "
                        "Please install the appropriate driver package."
                    ),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Connection failed: {exc}",
                }
        finally:
            if engine is not None:
                engine.dispose()

    @staticmethod
    async def create_connection(session: AsyncSession, data: ConnectionCreate) -> dict:
        """Create a new connection record with an encrypted password.

        Args:
            session: Async database session.
            data: Connection creation data.

        Returns:
            Dictionary representation of the created connection (without password).
        """
        encrypted_password = encrypt(data.password, _key())

        connection = Connection(
            name=data.name,
            db_type=data.db_type,
            host=data.host,
            port=data.port,
            username=data.username,
            password_encrypted=encrypted_password,
            database_name=data.database_name,
            extra_params=json.dumps(data.extra_params) if data.extra_params else None,
            group_name=data.group_name,
            tags=json.dumps(data.tags),
            pool_size=5,
        )
        session.add(connection)
        await session.flush()
        await session.commit()
        await session.refresh(connection)

        return ConnectionService._to_response_dict(connection)

    @staticmethod
    async def get_connection(
        session: AsyncSession, connection_id: int
    ) -> Optional[dict]:
        """Retrieve a single connection by ID.

        Args:
            session: Async database session.
            connection_id: The connection's primary key.

        Returns:
            Connection response dictionary or None if not found.
        """
        result = await session.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            return None
        return ConnectionService._to_response_dict(connection)

    @staticmethod
    async def list_connections(
        session: AsyncSession, group_name: Optional[str] = None
    ) -> list[dict]:
        """List all connections, optionally filtered by group name.

        Args:
            session: Async database session.
            group_name: Optional group name filter.

        Returns:
            List of connection response dictionaries.
        """
        stmt = select(Connection).order_by(Connection.id)
        if group_name is not None:
            stmt = stmt.where(Connection.group_name == group_name)

        result = await session.execute(stmt)
        connections = result.scalars().all()
        return [ConnectionService._to_response_dict(c) for c in connections]

    @staticmethod
    async def update_connection(
        session: AsyncSession,
        connection_id: int,
        data: ConnectionUpdate,
    ) -> Optional[dict]:
        """Update an existing connection.

        Args:
            session: Async database session.
            connection_id: The connection's primary key.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated connection response dictionary, or None if not found.
        """
        result = await session.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "password" and value is not None:
                connection.password_encrypted = encrypt(value, _key())
            elif field == "tags" and value is not None:
                connection.tags = json.dumps(value)
            elif field == "extra_params":
                connection.extra_params = json.dumps(value) if value else None
            else:
                setattr(connection, field, value)

        await session.flush()
        await session.commit()
        await session.refresh(connection)
        return ConnectionService._to_response_dict(connection)

    @staticmethod
    async def delete_connection(session: AsyncSession, connection_id: int) -> bool:
        """Delete a connection record.

        Args:
            session: Async database session.
            connection_id: The connection's primary key.

        Returns:
            True if deleted, False if not found.
        """
        result = await session.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        if connection is None:
            return False

        await session.delete(connection)
        await session.flush()
        await session.commit()
        return True

    @staticmethod
    async def get_connection_model(
        session: AsyncSession, connection_id: int
    ) -> Optional[Connection]:
        """Retrieve the raw Connection ORM model (used by other modules).

        Args:
            session: Async database session.
            connection_id: The connection's primary key.

        Returns:
            The Connection ORM instance or None.
        """
        result = await session.execute(
            select(Connection).where(Connection.id == connection_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def get_decrypted_password(connection: Connection) -> str:
        """Decrypt and return the password from a Connection model."""
        return decrypt(connection.password_encrypted, _key())

    @staticmethod
    def _to_response_dict(connection: Connection) -> dict:
        """Convert a Connection ORM model to a response-safe dictionary."""
        tags = []
        if connection.tags:
            try:
                tags = json.loads(connection.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []

        return {
            "id": connection.id,
            "name": connection.name,
            "db_type": connection.db_type,
            "host": connection.host,
            "port": connection.port,
            "username": connection.username,
            "database_name": connection.database_name,
            "group_name": connection.group_name,
            "tags": tags,
            "pool_size": connection.pool_size,
            "created_at": connection.created_at,
            "updated_at": connection.updated_at,
        }
