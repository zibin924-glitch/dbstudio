"""FastAPI router for querying audit logs with pagination and filters."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog
from app.database.session import get_db
from app.utils.responses import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=None)
async def list_audit_logs(
    resource_type: Optional[str] = Query(
        default=None,
        description="Filter by resource type (connection, api, query, ddl_export)",
    ),
    action: Optional[str] = Query(
        default=None,
        description="Filter by action type (create, update, delete)",
    ),
    date_from: Optional[datetime] = Query(
        default=None,
        description="Start of date range (ISO 8601)",
    ),
    date_to: Optional[datetime] = Query(
        default=None,
        description="End of date range (ISO 8601)",
    ),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries with pagination and optional filters.

    Supports filtering by resource_type, action, and date range.
    Results are ordered by timestamp descending (most recent first).
    """
    # Build base query
    base_conditions = []
    if resource_type:
        base_conditions.append(AuditLog.resource_type == resource_type)
    if action:
        base_conditions.append(AuditLog.action == action)
    if date_from:
        base_conditions.append(AuditLog.timestamp >= date_from)
    if date_to:
        base_conditions.append(AuditLog.timestamp <= date_to)

    # Count total
    count_stmt = select(sa_func.count()).select_from(AuditLog)
    for cond in base_conditions:
        count_stmt = count_stmt.where(cond)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch page
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    for cond in base_conditions:
        stmt = stmt.where(cond)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    items = [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "user_info": log.user_info,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
