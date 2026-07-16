"""Query history service - records, lists, searches, and manages query history."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import QueryHistory

logger = logging.getLogger(__name__)


class QueryHistoryService:
    """Service for managing SQL query execution history records."""

    @staticmethod
    async def record(
        session: AsyncSession,
        connection_id: int,
        sql_text: str,
        duration_ms: float,
        row_count: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a query execution in history.

        Args:
            session: Async database session.
            connection_id: The connection used for the query.
            sql_text: The SQL that was executed.
            duration_ms: Execution time in milliseconds.
            row_count: Number of rows returned or affected.
            status: 'success' or 'error'.
            error_message: Error description if status is 'error'.
        """
        history = QueryHistory(
            connection_id=connection_id,
            sql_text=sql_text,
            execution_time=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            row_count=row_count,
            status=status,
            error_message=error_message,
            is_favorite=False,
        )
        session.add(history)
        await session.flush()

    @staticmethod
    async def list_history(
        session: AsyncSession,
        connection_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        """List query history with pagination.

        Args:
            session: Async database session.
            connection_id: Optional filter by connection.
            page: 1-based page number.
            page_size: Number of records per page.

        Returns:
            List of history entry dictionaries, newest first.
        """
        stmt = select(QueryHistory).order_by(QueryHistory.created_at.desc())

        if connection_id is not None:
            stmt = stmt.where(QueryHistory.connection_id == connection_id)

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await session.execute(stmt)
        entries = result.scalars().all()
        return [QueryHistoryService._to_dict(e) for e in entries]

    @staticmethod
    async def search_history(
        session: AsyncSession,
        keyword: str,
        connection_id: Optional[int] = None,
    ) -> list[dict]:
        """Search query history by SQL text keyword.

        Args:
            session: Async database session.
            keyword: Keyword to search for in SQL text.
            connection_id: Optional filter by connection.

        Returns:
            List of matching history entry dictionaries.
        """
        stmt = (
            select(QueryHistory)
            .where(QueryHistory.sql_text.ilike(f"%{keyword}%"))
            .order_by(QueryHistory.created_at.desc())
        )

        if connection_id is not None:
            stmt = stmt.where(QueryHistory.connection_id == connection_id)

        stmt = stmt.limit(100)

        result = await session.execute(stmt)
        entries = result.scalars().all()
        return [QueryHistoryService._to_dict(e) for e in entries]

    @staticmethod
    async def toggle_favorite(
        session: AsyncSession,
        history_id: int,
        is_favorite: bool,
    ) -> None:
        """Toggle the favorite status of a history entry.

        Args:
            session: Async database session.
            history_id: The history entry's primary key.
            is_favorite: True to mark as favorite, False to unmark.
        """
        result = await session.execute(
            select(QueryHistory).where(QueryHistory.id == history_id)
        )
        entry = result.scalar_one_or_none()
        if entry is not None:
            entry.is_favorite = is_favorite
            await session.flush()

    @staticmethod
    async def get_history(
        session: AsyncSession,
        history_id: int,
    ) -> Optional[dict]:
        """Get a single history entry by ID.

        Args:
            session: Async database session.
            history_id: The history entry's primary key.

        Returns:
            History entry dictionary or None if not found.
        """
        result = await session.execute(
            select(QueryHistory).where(QueryHistory.id == history_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return None
        return QueryHistoryService._to_dict(entry)

    @staticmethod
    async def delete_history(
        session: AsyncSession,
        history_id: int,
    ) -> bool:
        """Delete a history entry.

        Args:
            session: Async database session.
            history_id: The history entry's primary key.

        Returns:
            True if deleted, False if not found.
        """
        result = await session.execute(
            select(QueryHistory).where(QueryHistory.id == history_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return False

        await session.delete(entry)
        await session.flush()
        return True

    @staticmethod
    def _to_dict(entry: QueryHistory) -> dict:
        """Convert a QueryHistory ORM model to a dictionary."""
        return {
            "id": entry.id,
            "connection_id": entry.connection_id,
            "sql_text": entry.sql_text,
            "execution_time": entry.execution_time.isoformat() if entry.execution_time else None,
            "duration_ms": entry.duration_ms,
            "row_count": entry.row_count,
            "status": entry.status,
            "error_message": entry.error_message,
            "is_favorite": entry.is_favorite,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
