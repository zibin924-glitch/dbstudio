"""PostgreSQL-specific dialect queries for metadata not covered by SQLAlchemy Inspector."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class PostgreSQLDialect:
    """PostgreSQL-specific metadata queries.

    Provides access to sequences, functions, and other PG-specific
    database objects.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_sequences(self, schema: Optional[str] = None) -> list[dict]:
        """List sequences in the given schema.

        Args:
            schema: Schema name. Defaults to 'public' if not specified.

        Returns:
            List of dicts with name, schema, start_value, increment, etc.
        """
        schema = schema or "public"
        sql = text(
            "SELECT sequence_name, start_value, minimum_value, maximum_value, "
            "increment, cycle_option "
            "FROM information_schema.sequences "
            "WHERE sequence_schema = :schema"
        )
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, {"schema": schema})
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "schema": schema,
                        "start_value": int(row[1]) if row[1] else 1,
                        "min_value": int(row[2]) if row[2] else 1,
                        "max_value": int(row[3]) if row[3] else None,
                        "increment": int(row[4]) if row[4] else 1,
                        "cycle": row[5] == "YES",
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get PostgreSQL sequences: %s", exc)
            return []

    def get_functions(self, schema: Optional[str] = None) -> list[dict]:
        """List functions/procedures in the given schema.

        Args:
            schema: Schema name. Defaults to 'public' if not specified.

        Returns:
            List of dicts with name, language, return_type, and definition.
        """
        schema = schema or "public"
        sql = text(
            "SELECT p.proname AS name, "
            "l.lanname AS language, "
            "pg_get_function_result(p.oid) AS return_type, "
            "pg_get_functiondef(p.oid) AS definition, "
            "CASE p.prokind "
            "  WHEN 'f' THEN 'function' "
            "  WHEN 'p' THEN 'procedure' "
            "  WHEN 'a' THEN 'aggregate' "
            "  WHEN 'w' THEN 'window' "
            "  ELSE 'unknown' "
            "END AS kind "
            "FROM pg_proc p "
            "JOIN pg_namespace n ON p.pronamespace = n.oid "
            "JOIN pg_language l ON p.prolang = l.oid "
            "WHERE n.nspname = :schema "
            "AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY p.proname"
        )
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, {"schema": schema})
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "language": row[1],
                        "return_type": row[2],
                        "definition": row[3],
                        "kind": row[4],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get PostgreSQL functions: %s", exc)
            return []

    def get_extensions(self) -> list[dict]:
        """List installed PostgreSQL extensions.

        Returns:
            List of dicts with name, version, and schema.
        """
        sql = text(
            "SELECT extname, extversion, "
            "n.nspname AS schema "
            "FROM pg_extension e "
            "JOIN pg_namespace n ON e.extnamespace = n.oid "
            "ORDER BY extname"
        )
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql)
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "version": row[1],
                        "schema": row[2],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get PostgreSQL extensions: %s", exc)
            return []

    def get_triggers(self, schema: Optional[str] = None) -> list[dict]:
        """List triggers in the given schema.

        Args:
            schema: Schema name. Defaults to 'public'.

        Returns:
            List of dicts with name, table, event, timing, definition.
        """
        schema = schema or "public"
        sql = text(
            "SELECT trigger_name, event_object_table, event_manipulation, "
            "action_timing, action_statement "
            "FROM information_schema.triggers "
            "WHERE trigger_schema = :schema "
            "ORDER BY trigger_name"
        )
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, {"schema": schema})
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "table": row[1],
                        "event": row[2],
                        "timing": row[3],
                        "definition": row[4],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get PostgreSQL triggers: %s", exc)
            return []

    def get_table_sizes(self, schema: Optional[str] = None) -> list[dict]:
        """Get table sizes (total, table, index) for the schema."""
        schema = schema or "public"
        sql = text(
            "SELECT "
            "c.relname AS table_name, "
            "pg_total_relation_size(c.oid) AS total_size, "
            "pg_relation_size(c.oid) AS table_size, "
            "pg_indexes_size(c.oid) AS index_size, "
            "c.reltuples::bigint AS row_estimate "
            "FROM pg_class c "
            "JOIN pg_namespace n ON c.relnamespace = n.oid "
            "WHERE n.nspname = :schema "
            "AND c.relkind = 'r' "
            "ORDER BY pg_total_relation_size(c.oid) DESC"
        )
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sql, {"schema": schema})
                rows = result.fetchall()
                return [
                    {
                        "name": row[0],
                        "total_size": int(row[1]),
                        "table_size": int(row[2]),
                        "index_size": int(row[3]),
                        "row_estimate": int(row[4]),
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.warning("Failed to get PostgreSQL table sizes: %s", exc)
            return []
