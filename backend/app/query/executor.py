"""SQL query executor with pagination, timing, and timeout support."""

import asyncio
import logging
import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Executes SQL queries against a database engine with pagination and timing.

    Provides a single `execute` method that runs arbitrary SQL, extracts
    column metadata, paginates results, and measures execution duration.
    Blocking DB operations are offloaded to a thread pool via
    ``asyncio.to_thread`` and guarded by ``asyncio.wait_for`` to enforce
    a configurable timeout.
    """

    @staticmethod
    async def execute(
        connection: Engine,
        sql: str,
        page: int = 1,
        page_size: int = 50,
        timeout: Optional[int] = None,
    ) -> dict:
        """Execute a SQL statement and return paginated results.

        For SELECT queries the results are paginated. For DML statements
        (INSERT/UPDATE/DELETE) the affected row count is returned.

        Args:
            connection: A SQLAlchemy Engine to execute against.
            sql: The SQL statement to execute.
            page: 1-based page number for SELECT queries.
            page_size: Number of rows per page.
            timeout: Statement timeout in seconds. Defaults to
                ``settings.QUERY_TIMEOUT`` when not provided.

        Returns:
            Dictionary with keys:
                - columns: list of column name strings
                - rows: list of row lists (paginated for SELECT)
                - row_count: number of rows in the current page
                - total: total number of matching rows (for SELECT)
                - page: current page number
                - page_size: page size
                - duration_ms: execution time in milliseconds
                - error: (only on timeout) description of the timeout
        """
        if timeout is None:
            timeout = settings.QUERY_TIMEOUT

        start_time = time.time()
        sql_stripped = sql.strip().rstrip(";")
        first_keyword = sql_stripped.split()[0].upper() if sql_stripped.split() else ""

        is_select = first_keyword in ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")

        try:
            if is_select:
                # Offload the blocking SELECT work to a thread
                def _run_select():
                    with connection.connect() as conn:
                        result = conn.execute(text(sql_stripped))
                        columns = list(result.keys())
                        all_rows = [list(row) for row in result.fetchall()]
                        return columns, all_rows

                columns, all_rows = await asyncio.wait_for(
                    asyncio.to_thread(_run_select),
                    timeout=timeout,
                )

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
                # DML / DDL statements - also offload to a thread
                def _run_dml():
                    with connection.connect() as conn:
                        result = conn.execute(text(sql_stripped))
                        conn.commit()
                        affected = result.rowcount if result.rowcount >= 0 else 0
                        columns = list(result.keys()) if result.returns_rows else []
                        rows = (
                            [list(row) for row in result.fetchall()]
                            if result.returns_rows
                            else []
                        )
                        return affected, columns, rows

                affected, columns, rows = await asyncio.wait_for(
                    asyncio.to_thread(_run_dml),
                    timeout=timeout,
                )

                duration_ms = round((time.time() - start_time) * 1000, 2)

                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": affected,
                    "total": affected,
                    "page": 1,
                    "page_size": affected,
                    "duration_ms": duration_ms,
                }

        except asyncio.TimeoutError:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.warning("Query timed out after %s seconds", timeout)
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "duration_ms": duration_ms,
                "error": f"Query timed out after {timeout} seconds",
            }

        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.warning("Query execution failed: %s", exc)
            raise
