"""Oracle-specific dialect queries for metadata not covered by SQLAlchemy Inspector."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class OracleDialect:
    """Oracle-specific metadata queries.

    Provides access to sequences, stored procedures, triggers, and other
    Oracle-specific database objects using Oracle data dictionary views.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_sequences(self, schema: Optional[str] = None) -> list[dict]:
        """List sequences accessible to the current user.

        Args:
            schema: Owner/schema name. If None, uses the current user's objects.

        Returns:
            List of dicts with name, min_value, max_value, increment, etc.
        """
        if schema:
            sql = text(
                "SELECT SEQUENCE_NAME, MIN_VALUE, MAX_VALUE, INCREMENT_BY, "
                "CYCLE_FLAG, ORDER_FLAG, CACHE_SIZE, LAST_NUMBER "
                "FROM ALL_SEQUENCES "
                "WHERE SEQUENCE_OWNER = :schema "
                "ORDER BY SEQUENCE_NAME"
            )
            params = {"schema": schema.upper()}
        else:
            sql = text(
                "SELECT SEQUENCE_NAME, MIN_VALUE, MAX_VALUE, INCREMENT_BY, "
                "CYCLE_FLAG, ORDER_FLAG, CACHE_SIZE, LAST_NUMBER "
                "FROM USER_SEQUENCES "
                "ORDER BY SEQUENCE_NAME"
            )
            params = {}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "min_value": int(row[1]) if row[1] is not None else None,
                        "max_value": int(row[2]) if row[2] is not None else None,
                        "increment_by": int(row[3]) if row[3] is not None else 1,
                        "cycle": row[4] == "Y",
                        "order_flag": row[5] == "Y",
                        "cache_size": int(row[6]) if row[6] is not None else 0,
                        "last_number": int(row[7]) if row[7] is not None else None,
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get Oracle sequences: %s", exc)
            return []

    def get_stored_procedures(self, schema: Optional[str] = None) -> list[dict]:
        """List stored procedures and functions.

        Args:
            schema: Owner/schema name. If None, uses the current user's objects.

        Returns:
            List of dicts with name, type, status, and last_ddl_time.
        """
        if schema:
            sql = text(
                "SELECT OBJECT_NAME, OBJECT_TYPE, STATUS, LAST_DDL_TIME "
                "FROM ALL_OBJECTS "
                "WHERE OWNER = :schema AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION', 'PACKAGE') "
                "ORDER BY OBJECT_NAME"
            )
            params = {"schema": schema.upper()}
        else:
            sql = text(
                "SELECT OBJECT_NAME, OBJECT_TYPE, STATUS, LAST_DDL_TIME "
                "FROM USER_OBJECTS "
                "WHERE OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION', 'PACKAGE') "
                "ORDER BY OBJECT_NAME"
            )
            params = {}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "type": row[1],
                        "status": row[2],
                        "last_ddl_time": str(row[3]) if row[3] else None,
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get Oracle stored procedures: %s", exc)
            return []

    def get_triggers(self, schema: Optional[str] = None) -> list[dict]:
        """List triggers accessible to the current user.

        Args:
            schema: Owner/schema name. If None, uses the current user's objects.

        Returns:
            List of dicts with name, table, type, triggering_event, status.
        """
        if schema:
            sql = text(
                "SELECT TRIGGER_NAME, TABLE_NAME, TRIGGER_TYPE, "
                "TRIGGERING_EVENT, STATUS "
                "FROM ALL_TRIGGERS "
                "WHERE OWNER = :schema "
                "ORDER BY TRIGGER_NAME"
            )
            params = {"schema": schema.upper()}
        else:
            sql = text(
                "SELECT TRIGGER_NAME, TABLE_NAME, TRIGGER_TYPE, "
                "TRIGGERING_EVENT, STATUS "
                "FROM USER_TRIGGERS "
                "ORDER BY TRIGGER_NAME"
            )
            params = {}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "table": row[1],
                        "type": row[2],
                        "event": row[3],
                        "status": row[4],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get Oracle triggers: %s", exc)
            return []

    def get_tablespaces(self) -> list[dict]:
        """List tablespace information.

        Returns:
            List of dicts with name, status, contents, block_size, etc.
        """
        sql = text(
            "SELECT TABLESPACE_NAME, STATUS, CONTENTS, BLOCK_SIZE, "
            "LOGGING, EXTENT_MANAGEMENT, ALLOCATION_TYPE "
            "FROM DBA_TABLESPACES "
            "ORDER BY TABLESPACE_NAME"
        )
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "status": row[1],
                        "contents": row[2],
                        "block_size": int(row[3]) if row[3] else None,
                        "logging": row[4],
                        "extent_management": row[5],
                        "allocation_type": row[6],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get Oracle tablespaces: %s", exc)
            return []

    def get_table_statistics(self, schema: Optional[str] = None) -> list[dict]:
        """Get table statistics (row count, blocks, etc.).

        Args:
            schema: Owner/schema name. If None, uses the current user's objects.

        Returns:
            List of dicts with name, num_rows, blocks, avg_row_len, etc.
        """
        if schema:
            sql = text(
                "SELECT TABLE_NAME, NUM_ROWS, BLOCKS, AVG_ROW_LEN, "
                "LAST_ANALYZED, PARTITIONED "
                "FROM ALL_TABLES "
                "WHERE OWNER = :schema "
                "ORDER BY TABLE_NAME"
            )
            params = {"schema": schema.upper()}
        else:
            sql = text(
                "SELECT TABLE_NAME, NUM_ROWS, BLOCKS, AVG_ROW_LEN, "
                "LAST_ANALYZED, PARTITIONED "
                "FROM USER_TABLES "
                "ORDER BY TABLE_NAME"
            )
            params = {}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, params)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "num_rows": int(row[1]) if row[1] is not None else 0,
                        "blocks": int(row[2]) if row[2] is not None else 0,
                        "avg_row_len": int(row[3]) if row[3] is not None else 0,
                        "last_analyzed": str(row[4]) if row[4] else None,
                        "partitioned": row[5] == "YES",
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get Oracle table statistics: %s", exc)
            return []
