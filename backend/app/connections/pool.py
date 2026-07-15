"""Connection pool manager for maintaining reusable SQLAlchemy engines."""

import logging
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Manages a registry of SQLAlchemy Engine instances keyed by connection ID.

    Each connection gets at most one engine. Engines are created lazily and
    cached for reuse. Call dispose_pool / dispose_all to clean up.
    """

    def __init__(self) -> None:
        self._pools: dict[int, Engine] = {}

    def get_or_create_pool(self, connection_id: int, db_config: dict) -> Engine:
        """Return an existing engine or create a new one for the given connection.

        Args:
            connection_id: Unique identifier of the connection.
            db_config: Connection configuration dictionary with keys:
                       db_type, host, port, username, password, database_name.

        Returns:
            A SQLAlchemy Engine instance.
        """
        if connection_id in self._pools:
            return self._pools[connection_id]

        from app.connections.service import ConnectionService

        url = ConnectionService._build_url(db_config)

        db_type = db_config.get("db_type", "").lower()
        connect_args: dict = {}
        if db_type == "mysql":
            connect_args["connect_timeout"] = 10
        elif db_type == "postgresql":
            connect_args["connect_timeout"] = 10
        elif db_type == "oracle":
            connect_args["tcp_connect_timeout"] = 10

        engine = create_engine(
            url,
            pool_size=db_config.get("pool_size", 5),
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

        self._pools[connection_id] = engine
        logger.info("Created connection pool for connection_id=%d", connection_id)
        return engine

    def dispose_pool(self, connection_id: int) -> None:
        """Dispose and remove the engine for the given connection ID.

        Args:
            connection_id: The connection whose pool should be disposed.
        """
        engine = self._pools.pop(connection_id, None)
        if engine is not None:
            engine.dispose()
            logger.info("Disposed connection pool for connection_id=%d", connection_id)

    def dispose_all(self) -> None:
        """Dispose all managed engine pools."""
        for cid, engine in list(self._pools.items()):
            try:
                engine.dispose()
                logger.info("Disposed connection pool for connection_id=%d", cid)
            except Exception as exc:
                logger.warning("Error disposing pool for connection_id=%d: %s", cid, exc)
        self._pools.clear()

    async def health_check(self, engine: Engine) -> bool:
        """Check whether the engine can establish a connection.

        Args:
            engine: A SQLAlchemy Engine to test.

        Returns:
            True if a simple query succeeds, False otherwise.
        """
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("Health check failed: %s", exc)
            return False

    @property
    def pool_count(self) -> int:
        """Return the number of currently managed pools."""
        return len(self._pools)

    def get_pool(self, connection_id: int) -> Optional[Engine]:
        """Return the engine for a connection ID, or None."""
        return self._pools.get(connection_id)


# Module-level singleton instance
pool_manager = ConnectionPoolManager()
