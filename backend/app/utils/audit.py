"""Audit logging utility for recording CRUD operations across DBStudio resources.

Provides a simple ``log_audit`` coroutine that creates an ``AuditLog`` row
in the local metadata store.  Call this from any router handler after a
successful write operation.
"""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(
    session: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[Any] = None,
    user_info: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """Create an audit log entry and commit it to the database.

    Args:
        session: The active async database session.
        action: The action type — typically ``"create"``, ``"update"``,
                or ``"delete"``.
        resource_type: The resource category, e.g. ``"connection"``,
                       ``"api"``, ``"query"``, ``"ddl_export"``.
        resource_id: Optional identifier of the affected resource.
        user_info: Optional user identifier or system label.
        details: Optional dictionary of additional context stored as JSON.

    Returns:
        The persisted ``AuditLog`` ORM instance.
    """
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        user_info=user_info,
        details=details,
    )
    session.add(entry)
    try:
        await session.flush()
    except Exception:
        logger.warning("Failed to flush audit log entry: %s", entry, exc_info=True)
    return entry
