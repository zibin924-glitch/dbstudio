"""SQL query executor with pagination and timing."""

import logging
import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Executes SQL queries against a database engine with pagination and timing.

    Provides a single `execute` method that runs arbitrary SQL, extracts
    column metadata, paginates results, and measures execution duration.
    """

    @staticmethod
    def execute(
        connection: Engine,
        sql: str,
        page: int = 1,
        page_size: int = 50,
        timeout: int = 30,
    ) -> dict:
        """Execute a SQL statement and return paginated results.

        For SELECT queries the results are paginated. For DML statements
        (INSERT/UPDATE/DELETE) the affected row count is returned.

        Args:
            connection: A SQLAlchemy Engine to execute against.
            sql: The SQL statement to execute.
            page: 1-based page number for SELECT queries.
            page_size: Number of rows per page.
            timeout: Statement timeout in seconds.

        Returns:
            Dictionary with keys:
                - columns: list of column name strings
                - rows: list of row lists (paginated for SELECT)
                - row_count: number of rows in the current page
                - total: total number of matching rows (for SELECT)
                - page: current page number
                - page_size: page size
                - duration_ms: execution time in milliseconds
        """
        start_time = time.time()
        sql_stripped = sql.strip().rstrip(";")
        first_keyword = sql_stripped.split()[0].upper() if sql_stripped.split() else ""

        is_select = first_keyword in ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")

        try:
            with connection.connect() as conn:
                if is_select:
                    # For SELECT-type queries, paginate results
                    result = conn.execute(text(sql_stripped))

                    # Extract column names from cursor description
                    columns = list(result.keys())

                    # Fetch all rows for total count and pagination
                    all_rows = [list(row) for row in result.fetchall()]
                    total = len(all_rows)

                    # Apply pagination
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_rows = all_rows[start_idx:end_idx]

                    duration_ms = round((time.time() - start_time) * 1000, 2)

                    return {
                        "columns": columns,
                        "rows": paginated_rows,
                        "row_count": len(paginated_rows),
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "duration_ms": duration_ms,
                    }
                else:
                    # DML / DDL statements
                    result = conn.execute(text(sql_stripped))
                    conn.commit()

                    affected = result.rowcount if result.rowcount >= 0 else 0
                    duration_ms = round((time.time() - start_time) * 1000, 2)

                    columns = list(result.keys()) if result.returns_rows else []
                    rows = (
                        [list(row) for row in result.fetchall()]
                        if result.returns_rows
                        else []
                    )

                    return {
                        "columns": columns,
                        "rows": rows,
                        "row_count": affected,
                        "total": affected,
                        "page": 1,
                        "page_size": affected,
                        "duration_ms": duration_ms,
                    }

        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.warning("Query execution failed: %s", exc)
            raise
