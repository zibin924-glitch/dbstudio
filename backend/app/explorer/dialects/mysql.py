"""MySQL-specific dialect queries for metadata not covered by SQLAlchemy Inspector."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class MySQLDialect:
    """MySQL-specific metadata queries using INFORMATION_SCHEMA.

    Provides access to stored procedures, triggers, and other MySQL-specific
    database objects that SQLAlchemy's Inspector doesn't expose.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_stored_procedures(self, schema: Optional[str] = None) -> list[dict]:
        """List stored procedures in the given schema.

        Args:
            schema: Database/schema name. If None, uses the current database.

        Returns:
            List of dicts with name, type, created, modified, and definition.
        """
        sql = (
            "SELECT ROUTINE_NAME, ROUTINE_TYPE, CREATED, LAST_ALTERED, ROUTINE_DEFINITION "
            "FROM INFORMATION_SCHEMA.ROUTINES "
            "WHERE ROUTINE_SCHEMA = :schema"
        )
        params: dict = {}

        if schema:
            params["schema"] = schema
        else:
            sql = sql.replace("= :schema", "= DATABASE()")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "type": row[1],
                        "created": str(row[2]) if row[2] else None,
                        "modified": str(row[3]) if row[3] else None,
                        "definition": row[4],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get MySQL stored procedures: %s", exc)
            return []

    def get_triggers(self, schema: Optional[str] = None) -> list[dict]:
        """List triggers in the given schema.

        Args:
            schema: Database/schema name. If None, uses the current database.

        Returns:
            List of dicts with name, event, table, timing, and definition.
        """
        sql = (
            "SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, "
            "ACTION_TIMING, ACTION_STATEMENT "
            "FROM INFORMATION_SCHEMA.TRIGGERS "
            "WHERE TRIGGER_SCHEMA = :schema"
        )
        params: dict = {}

        if schema:
            params["schema"] = schema
        else:
            sql = sql.replace("= :schema", "= DATABASE()")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "event": row[1],
                        "table": row[2],
                        "timing": row[3],
                        "definition": row[4],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get MySQL triggers: %s", exc)
            return []

    def get_table_status(self, schema: Optional[str] = None) -> list[dict]:
        """Get table status information from INFORMATION_SCHEMA.TABLES.

        Returns engine, row count, data size, etc.
        """
        sql = (
            "SELECT TABLE_NAME, ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, "
            "AUTO_INCREMENT, TABLE_COLLATION, TABLE_COMMENT "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = :schema"
        )
        params: dict = {}

        if schema:
            params["schema"] = schema
        else:
            sql = sql.replace("= :schema", "= DATABASE()")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "engine": row[1],
                        "row_count": int(row[2]) if row[2] else 0,
                        "data_length": int(row[3]) if row[3] else 0,
                        "index_length": int(row[4]) if row[4] else 0,
                        "auto_increment": int(row[5]) if row[5] else None,
                        "collation": row[6],
                        "comment": row[7] or "",
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get MySQL table status: %s", exc)
            return []

    def get_events(self, schema: Optional[str] = None) -> list[dict]:
        """List scheduled events in the given schema."""
        sql = (
            "SELECT EVENT_NAME, EVENT_TYPE, EXECUTE_AT, INTERVAL_VALUE, "
            "INTERVAL_FIELD, STATUS "
            "FROM INFORMATION_SCHEMA.EVENTS "
            "WHERE EVENT_SCHEMA = :schema"
        )
        params: dict = {}

        if schema:
            params["schema"] = schema
        else:
            sql = sql.replace("= :schema", "= DATABASE()")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "type": row[1],
                        "execute_at": str(row[2]) if row[2] else None,
                        "interval_value": row[3],
                        "interval_field": row[4],
                        "status": row[5],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get MySQL events: %s", exc)
            return []
