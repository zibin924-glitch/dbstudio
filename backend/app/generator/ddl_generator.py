"""DDL generator - produces CREATE TABLE statements from table metadata."""

import logging
import re

logger = logging.getLogger(__name__)


class DDLGenerator:
    """Generates DDL (CREATE TABLE) statements from table metadata dictionaries."""

    @staticmethod
    def generate_create_table(
        table: dict,
        include_indexes: bool = True,
        include_foreign_keys: bool = True,
    ) -> str:
        """Generate a CREATE TABLE statement for a single table.

        Args:
            table: Table metadata dict with keys:
                   name, columns, indexes (optional), foreign_keys (optional),
                   db_type (optional, for dialect-specific syntax).
            include_indexes: Whether to include CREATE INDEX statements.
            include_foreign_keys: Whether to include FOREIGN KEY constraints
                                  in the CREATE TABLE statement.

        Returns:
            A string containing the DDL statement(s).
        """
        table_name = table.get("name", "unknown_table")
        columns = table.get("columns", [])
        indexes = table.get("indexes", [])
        foreign_keys = table.get("foreign_keys", [])
        comment = table.get("comment", "")
        db_type = table.get("db_type", "mysql").lower()

        lines: list[str] = []
        lines.append(f"CREATE TABLE `{table_name}` (")

        column_defs: list[str] = []
        pk_columns: list[str] = []

        for col in columns:
            col_name = col["name"]
            col_type = col.get("type", "VARCHAR(255)")
            nullable = col.get("nullable", True)
            default = col.get("default")
            is_pk = col.get("primary_key", False)
            auto_inc = col.get("auto_increment", False)
            col_comment = col.get("comment", "")

            parts = [f"    `{col_name}` {col_type}"]

            if not nullable:
                parts.append("NOT NULL")

            if default is not None:
                # Handle numeric vs string defaults
                try:
                    float(default)
                    parts.append(f"DEFAULT {default}")
                except (ValueError, TypeError):
                    if default.upper() in ("CURRENT_TIMESTAMP", "NOW()", "NULL", "TRUE", "FALSE"):
                        parts.append(f"DEFAULT {default}")
                    else:
                        parts.append(f"DEFAULT '{default}'")

            if auto_inc:
                if db_type == "postgresql":
                    # PostgreSQL uses SERIAL type instead
                    pass
                elif db_type == "oracle":
                    # Oracle uses sequences + triggers or GENERATED ALWAYS AS IDENTITY
                    parts.append("GENERATED ALWAYS AS IDENTITY")
                else:
                    parts.append("AUTO_INCREMENT")

            if include_foreign_keys and col_comment:
                pass  # comments are added at the table level below

            if is_pk:
                pk_columns.append(col_name)

            column_defs.append(" ".join(parts))

        # Primary key constraint
        if pk_columns:
            pk_list = ", ".join(f"`{c}`" for c in pk_columns)
            column_defs.append(f"    PRIMARY KEY ({pk_list})")

        # Foreign key constraints
        if include_foreign_keys and foreign_keys:
            # Group FKs by name (multi-column FKs)
            fk_groups: dict[str, list[dict]] = {}
            for fk in foreign_keys:
                fk_name = fk.get("name", "")
                if fk_name not in fk_groups:
                    fk_groups[fk_name] = []
                fk_groups[fk_name].append(fk)

            for fk_name, fk_list in fk_groups.items():
                source_cols = ", ".join(f"`{fk['source_column']}`" for fk in fk_list)
                target_table = fk_list[0].get("target_table", "")
                target_cols = ", ".join(f"`{fk['target_column']}`" for fk in fk_list)
                on_update = fk_list[0].get("on_update", "NO ACTION")
                on_delete = fk_list[0].get("on_delete", "NO ACTION")

                constraint_name = fk_name or f"fk_{table_name}_{fk_list[0]['source_column']}"
                fk_def = (
                    f"    CONSTRAINT `{constraint_name}` "
                    f"FOREIGN KEY ({source_cols}) "
                    f"REFERENCES `{target_table}` ({target_cols})"
                )
                if on_update and on_update != "NO ACTION":
                    fk_def += f" ON UPDATE {on_update}"
                if on_delete and on_delete != "NO ACTION":
                    fk_def += f" ON DELETE {on_delete}"

                column_defs.append(fk_def)

        lines.append(",\n".join(column_defs))
        lines.append(");")

        # Table comment
        if comment and db_type == "mysql":
            lines.append(f"ALTER TABLE `{table_name}` COMMENT = '{comment}';")

        # Column comments (MySQL style via ALTER TABLE)
        if db_type == "mysql":
            for col in columns:
                col_comment = col.get("comment", "")
                if col_comment:
                    lines.append(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN "
                        f"`{col['name']}` {col.get('type', 'VARCHAR(255)')} "
                        f"COMMENT '{col_comment}';"
                    )

        # Indexes (as separate CREATE INDEX statements)
        if include_indexes and indexes:
            lines.append("")
            for idx in indexes:
                idx_name = idx.get("name", f"idx_{table_name}")
                unique = "UNIQUE " if idx.get("unique") else ""
                idx_cols = ", ".join(f"`{c}`" for c in idx.get("columns", []))
                if idx_cols:
                    lines.append(
                        f"CREATE {unique}INDEX `{idx_name}` "
                        f"ON `{table_name}` ({idx_cols});"
                    )

        return "\n".join(lines)

    @staticmethod
    def generate_schema(tables: list[dict]) -> str:
        """Generate DDL for multiple tables.

        Args:
            tables: List of table metadata dicts.

        Returns:
            All CREATE TABLE statements concatenated with separators.
        """
        ddl_parts: list[str] = []

        for table in tables:
            ddl = DDLGenerator.generate_create_table(table)
            ddl_parts.append(ddl)

        return "\n\n".join(ddl_parts)
