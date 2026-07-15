"""Database metadata explorer service using SQLAlchemy Inspector."""

import logging
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Inspector

logger = logging.getLogger(__name__)


class ExplorerService:
    """Provides database metadata exploration via SQLAlchemy Inspector.

    Takes a SQLAlchemy Inspector (created from an engine) and exposes
    methods for retrieving schemas, tables, columns, indexes, foreign keys,
    views, and aggregate statistics.
    """

    def __init__(self, inspector: Inspector) -> None:
        self.inspector = inspector

    def get_schema_list(self) -> list[str]:
        """Return a list of schema names in the database.

        Falls back to an empty list if the dialect doesn't support schemas.
        """
        try:
            return self.inspector.get_schema_names()
        except Exception as exc:
            logger.warning("Failed to list schemas: %s", exc)
            return []

    def get_table_list(self, schema: Optional[str] = None) -> list[str]:
        """Return a list of table names, optionally filtered by schema.

        Args:
            schema: Optional schema name to filter tables.

        Returns:
            Sorted list of table name strings.
        """
        try:
            return sorted(self.inspector.get_table_names(schema=schema))
        except Exception as exc:
            logger.warning("Failed to list tables for schema=%s: %s", schema, exc)
            return []

    def get_columns(self, table_name: str, schema: Optional[str] = None) -> list[dict]:
        """Return detailed column information for a table.

        Args:
            table_name: Name of the table to inspect.
            schema: Optional schema name.

        Returns:
            List of dicts with keys: name, type, nullable, default,
            primary_key, auto_increment, comment.
        """
        try:
            raw_columns = self.inspector.get_columns(table_name, schema=schema)
        except Exception as exc:
            logger.warning("Failed to get columns for %s: %s", table_name, exc)
            return []

        # Determine primary key columns
        try:
            pk_constraint = self.inspector.get_pk_constraint(table_name, schema=schema)
            pk_columns = set(pk_constraint.get("constrained_columns", []))
        except Exception:
            pk_columns = set()

        columns = []
        for col in raw_columns:
            col_type = str(col.get("type", ""))
            auto_increment = False

            # Detect auto-increment from dialect-specific flags
            dialect_opts = col.get("dialect_options", {})
            if isinstance(dialect_opts, dict):
                mysql_auto = dialect_opts.get("mysql_autoincrement", False)
                pg_identity = dialect_opts.get("postgresql_identity", None)
                if mysql_auto or pg_identity is not None:
                    auto_increment = True

            # Also check the column's 'autoincrement' key if present
            if col.get("autoincrement") is True:
                auto_increment = True

            columns.append({
                "name": col["name"],
                "type": col_type,
                "nullable": col.get("nullable", True),
                "default": str(col["default"]) if col.get("default") is not None else None,
                "primary_key": col["name"] in pk_columns,
                "auto_increment": auto_increment,
                "comment": col.get("comment", None),
            })

        return columns

    def get_indexes(self, table_name: str, schema: Optional[str] = None) -> list[dict]:
        """Return index information for a table.

        Args:
            table_name: Name of the table to inspect.
            schema: Optional schema name.

        Returns:
            List of dicts with keys: name, type, columns, unique.
        """
        try:
            raw_indexes = self.inspector.get_indexes(table_name, schema=schema)
        except Exception as exc:
            logger.warning("Failed to get indexes for %s: %s", table_name, exc)
            return []

        indexes = []
        for idx in raw_indexes:
            index_type = "UNIQUE" if idx.get("unique", False) else "NORMAL"
            indexes.append({
                "name": idx.get("name", ""),
                "type": index_type,
                "columns": idx.get("column_names", []),
                "unique": idx.get("unique", False),
            })

        return indexes

    def get_foreign_keys(
        self, table_name: str, schema: Optional[str] = None
    ) -> list[dict]:
        """Return foreign key information for a table.

        Args:
            table_name: Name of the table to inspect.
            schema: Optional schema name.

        Returns:
            List of dicts with keys: name, source_column, target_table,
            target_column, on_update, on_delete.
        """
        try:
            raw_fks = self.inspector.get_foreign_keys(table_name, schema=schema)
        except Exception as exc:
            logger.warning("Failed to get foreign keys for %s: %s", table_name, exc)
            return []

        foreign_keys = []
        for fk in raw_fks:
            constrained_columns = fk.get("constrained_columns", [])
            referred_columns = fk.get("referred_columns", [])

            # A FK can span multiple columns; we emit one entry per column pair.
            for src_col, tgt_col in zip(constrained_columns, referred_columns):
                foreign_keys.append({
                    "name": fk.get("name", ""),
                    "source_column": src_col,
                    "target_table": fk.get("referred_table", ""),
                    "target_column": tgt_col,
                    "on_update": fk.get("options", {}).get("onupdate", "NO ACTION"),
                    "on_delete": fk.get("options", {}).get("ondelete", "NO ACTION"),
                })

        return foreign_keys

    def get_view_list(self, schema: Optional[str] = None) -> list[str]:
        """Return a list of view names, optionally filtered by schema.

        Args:
            schema: Optional schema name.

        Returns:
            Sorted list of view name strings.
        """
        try:
            return sorted(self.inspector.get_view_names(schema=schema))
        except Exception as exc:
            logger.warning("Failed to list views for schema=%s: %s", schema, exc)
            return []

    def get_table_properties(
        self, table_name: str, schema: Optional[str] = None
    ) -> dict:
        """Return estimated properties for a table (e.g., row count estimate).

        This uses INFORMATION_SCHEMA or similar system tables where available,
        and falls back to basic metadata otherwise.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.

        Returns:
            Dictionary with table properties such as row_count_estimate.
        """
        properties: dict = {
            "table_name": table_name,
            "schema": schema,
            "row_count_estimate": None,
            "column_count": 0,
        }

        try:
            columns = self.get_columns(table_name, schema)
            properties["column_count"] = len(columns)
        except Exception:
            pass

        # Try to get row count estimate via the engine
        try:
            engine = self.inspector.engine
            dialect_name = engine.dialect.name.lower()

            if dialect_name == "postgresql":
                # Use pg_stat for estimate
                sql = text(
                    "SELECT reltuples::bigint AS estimate "
                    "FROM pg_class WHERE relname = :table_name"
                )
                with engine.connect() as conn:
                    result = conn.execute(sql, {"table_name": table_name})
                    row = result.fetchone()
                    if row:
                        properties["row_count_estimate"] = max(int(row[0]), 0)
            elif dialect_name == "mysql":
                sql = text(
                    "SELECT TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_NAME = :table_name"
                )
                params: dict = {"table_name": table_name}
                if schema:
                    sql = text(
                        "SELECT TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_NAME = :table_name AND TABLE_SCHEMA = :schema"
                    )
                    params["schema"] = schema
                with engine.connect() as conn:
                    result = conn.execute(sql, params)
                    row = result.fetchone()
                    if row:
                        properties["row_count_estimate"] = int(row[0]) if row[0] else 0
            else:
                # Generic fallback: COUNT(*) (may be slow on large tables)
                qualified = f"{schema}.{table_name}" if schema else table_name
                sql = text(f"SELECT COUNT(*) FROM {qualified}")
                with engine.connect() as conn:
                    result = conn.execute(sql)
                    row = result.fetchone()
                    if row:
                        properties["row_count_estimate"] = int(row[0])
        except Exception as exc:
            logger.debug("Could not get row count estimate for %s: %s", table_name, exc)

        return properties

    def get_database_stats(self, schema: Optional[str] = None) -> dict:
        """Return aggregate statistics for the database or schema.

        Args:
            schema: Optional schema name to scope statistics.

        Returns:
            Dictionary with table_count, view_count, total_rows estimate, etc.
        """
        tables = self.get_table_list(schema=schema)
        views = self.get_view_list(schema=schema)

        total_rows = 0
        for table in tables:
            try:
                props = self.get_table_properties(table, schema=schema)
                estimate = props.get("row_count_estimate", 0) or 0
                total_rows += estimate
            except Exception:
                pass

        return {
            "schema": schema,
            "table_count": len(tables),
            "view_count": len(views),
            "total_rows_estimate": total_rows,
            "tables": tables,
            "views": views,
        }
