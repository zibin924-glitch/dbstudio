"""API Gateway core - SQL parameter extraction, safety validation, and execution."""

import logging
import re
import time
from typing import Any

import sqlparse
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# SQL types allowed through the gateway
_ALLOWED_KEYWORDS = frozenset({"SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"})


class ApiGateway:
    """Core gateway logic for dynamic SQL-based API endpoints.

    Handles parameter extraction from SQL templates, SQL safety validation,
    parameter validation/type coercion, and query execution.
    """

    @staticmethod
    def extract_params(sql: str) -> list[str]:
        """Find all :param_name patterns in a SQL template.

        Args:
            sql: SQL template string with named parameters like :user_id, :name.

        Returns:
            Deduplicated list of parameter name strings (in order of first appearance).
        """
        # Match :param_name but not :: (PostgreSQL cast) or inside strings
        pattern = r"(?<!:):(\w+)"
        matches = re.findall(pattern, sql)

        # Deduplicate while preserving order
        seen: set[str] = set()
        params: list[str] = []
        for name in matches:
            if name not in seen:
                seen.add(name)
                params.append(name)
        return params

    @staticmethod
    def is_safe_sql(sql: str) -> bool:
        """Validate that a SQL template contains only safe (read-only) statements.

        Only SELECT-like queries are allowed. Multiple statements are blocked.

        Args:
            sql: The SQL template to validate.

        Returns:
            True if the SQL is safe, False otherwise.
        """
        if not sql or not sql.strip():
            return False

        # Strip comments
        cleaned = sqlparse.format(sql, strip_comments=True).strip()
        if not cleaned:
            return False

        # Block multiple statements
        statements = sqlparse.split(cleaned)
        if len(statements) > 1:
            logger.warning("Multiple SQL statements detected in API template")
            return False

        # Check for semicolons (additional guard)
        if ";" in cleaned.rstrip(";").rstrip():
            logger.warning("Semicolon detected in SQL template (possible injection)")
            return False

        # Detect first keyword
        parsed = sqlparse.parse(cleaned)
        if not parsed:
            return False

        for token in parsed[0].tokens:
            if token.is_whitespace:
                continue
            keyword = token.value.upper().strip()
            if keyword in _ALLOWED_KEYWORDS:
                return True
            # WITH clause (CTE)
            if keyword.startswith("WITH"):
                return True
            break

        logger.warning("Non-SELECT SQL detected in API template: %s", cleaned[:100])
        return False

    @staticmethod
    def validate_params(
        params_def: list[dict],
        params: dict,
    ) -> dict:
        """Validate and type-coerce parameters against their definitions.

        Applies defaults for missing optional parameters, checks required
        parameters, and coerces types.

        Args:
            params_def: List of parameter definition dicts, each with keys:
                        name, type, required, default.
            params: Dictionary of provided parameter values.

        Returns:
            Validated and coerced parameter dictionary.

        Raises:
            ValueError: If a required parameter is missing or type coercion fails.
        """
        validated: dict[str, Any] = {}

        for pdef in params_def:
            name = pdef["name"]
            ptype = pdef.get("type", "string").lower()
            required = pdef.get("required", False)
            default = pdef.get("default")

            if name in params:
                value = params[name]
            elif default is not None:
                value = default
            elif required:
                raise ValueError(f"Required parameter '{name}' is missing.")
            else:
                # Optional and not provided - skip (SQL should handle NULL)
                continue

            # Type coercion
            try:
                if ptype == "int" or ptype == "integer":
                    validated[name] = int(value)
                elif ptype == "float" or ptype == "number":
                    validated[name] = float(value)
                elif ptype == "bool" or ptype == "boolean":
                    if isinstance(value, str):
                        validated[name] = value.lower() in ("true", "1", "yes")
                    else:
                        validated[name] = bool(value)
                elif ptype == "string":
                    validated[name] = str(value)
                else:
                    validated[name] = str(value)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Parameter '{name}' expects type '{ptype}' "
                    f"but got '{value}' ({type(value).__name__}): {exc}"
                )

        return validated

    @staticmethod
    def execute_api(
        sql_template: str,
        params: dict,
        connection: Engine,
    ) -> dict:
        """Execute a parameterized SQL query via the gateway.

        Substitutes :param placeholders with validated parameter values
        using SQLAlchemy's text() binding.

        Args:
            sql_template: SQL template with :param_name placeholders.
            params: Validated parameter dictionary.
            connection: SQLAlchemy Engine to execute against.

        Returns:
            Dictionary with 'data' (list of row dicts), 'total', and 'duration_ms'.
        """
        start_time = time.time()

        # Remove trailing semicolon for execution
        sql = sql_template.strip().rstrip(";")

        with connection.connect() as conn:
            result = conn.execute(text(sql), params)
            columns = list(result.keys())
            rows = result.fetchall()

            # Convert rows to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for col_idx, col_name in enumerate(columns):
                    val = row[col_idx]
                    # Convert non-serializable types
                    if val is not None and not isinstance(val, (str, int, float, bool)):
                        val = str(val)
                    row_dict[col_name] = val
                data.append(row_dict)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "data": data,
            "total": len(data),
            "duration_ms": int(duration_ms),
        }
