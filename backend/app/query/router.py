"""FastAPI router for SQL query console endpoints."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.pool import pool_manager
from app.connections.service import ConnectionService
from app.database.session import get_db
from app.query.executor import QueryExecutor
from app.query.export import ExportService
from app.query.guard import QueryGuard
from app.query.history import QueryHistoryService
from app.utils.responses import ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

conn_svc = ConnectionService()
history_svc = QueryHistoryService()
export_svc = ExportService()


# --- Request / Response schemas ---


class ExecuteRequest(BaseModel):
    connection_id: int
    sql: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=5000)
    read_only: bool = Field(default=True, description="Enforce read-only mode")


class ExportRequest(BaseModel):
    connection_id: int
    sql: str
    format: str = Field(default="csv", description="Export format: csv, excel, json")


class FavoriteToggle(BaseModel):
    is_favorite: bool


# --- Helper ---


async def _get_engine(db: AsyncSession, connection_id: int):
    """Resolve connection and return its engine, or None."""
    connection = await conn_svc.get_connection_model(db, connection_id)
    if connection is None:
        return None
    config = {
        "db_type": connection.db_type,
        "host": connection.host,
        "port": connection.port,
        "username": connection.username,
        "password": ConnectionService.get_decrypted_password(connection),
        "database_name": connection.database_name,
        "extra_params": connection.get_extra_params(),
        "pool_size": connection.pool_size,
    }
    engine = pool_manager.get_or_create_pool(connection_id, config)
    return engine


# --- Endpoints ---


@router.post("/execute", response_model=None)
async def execute_query(
    req: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a SQL query and return paginated results.

    Records the execution in query history. In read-only mode,
    write statements are rejected by QueryGuard.
    """
    engine = await _get_engine(db, req.connection_id)
    if engine is None:
        return ErrorResponse(message="Connection not found.", code=404)

    # Guard check
    guard = QueryGuard(read_only=req.read_only)
    if not guard.is_allowed(req.sql):
        return ErrorResponse(
            message="This SQL statement is not allowed in read-only mode.",
            code=403,
        )

    executor = QueryExecutor()
    try:
        result = executor.execute(
            connection=engine,
            sql=req.sql,
            page=req.page,
            page_size=req.page_size,
        )

        # Record success in history
        await history_svc.record(
            session=db,
            connection_id=req.connection_id,
            sql_text=req.sql,
            duration_ms=result["duration_ms"],
            row_count=result["row_count"],
            status="success",
        )

        return SuccessResponse(data=result)

    except Exception as exc:
        # Record failure in history
        await history_svc.record(
            session=db,
            connection_id=req.connection_id,
            sql_text=req.sql,
            duration_ms=0,
            row_count=0,
            status="error",
            error_message=str(exc),
        )
        return ErrorResponse(message="Query execution failed.", detail=str(exc))


@router.post("/export", response_model=None)
async def export_query(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a SQL query and export the full results as a file download.

    Supported formats: csv, excel, json.
    """
    engine = await _get_engine(db, req.connection_id)
    if engine is None:
        return ErrorResponse(message="Connection not found.", code=404)

    # Only SELECT allowed for export
    guard = QueryGuard(read_only=True)
    if not guard.is_allowed(req.sql):
        return ErrorResponse(
            message="Only SELECT queries can be exported.", code=403
        )

    executor = QueryExecutor()
    try:
        # Execute with a large page_size to get all rows
        result = executor.execute(
            connection=engine,
            sql=req.sql,
            page=1,
            page_size=50000,
        )
    except Exception as exc:
        return ErrorResponse(message="Query execution failed.", detail=str(exc))

    columns = result["columns"]
    # For export we want all rows, not just the current page
    # Re-fetch all rows
    try:
        from sqlalchemy import text as sa_text
        with engine.connect() as conn:
            full_result = conn.execute(sa_text(req.sql.strip().rstrip(";")))
            all_rows = [list(row) for row in full_result.fetchall()]
    except Exception as exc:
        return ErrorResponse(message="Failed to fetch data for export.", detail=str(exc))

    fmt = req.format.lower()
    if fmt == "csv":
        content = export_svc.export_csv(columns, all_rows)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )
    elif fmt in ("excel", "xlsx"):
        content = export_svc.export_excel(columns, all_rows)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"},
        )
    elif fmt == "json":
        data = export_svc.export_json(columns, all_rows)
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        return Response(
            content=json_bytes,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=export.json"},
        )
    else:
        return ErrorResponse(
            message=f"Unsupported export format: '{fmt}'. Use csv, excel, or json.",
            code=400,
        )


@router.get("/history", response_model=None)
async def list_history(
    connection_id: Optional[int] = Query(default=None, description="Filter by connection"),
    keyword: Optional[str] = Query(default=None, description="Search keyword in SQL text"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List query history with optional filtering and pagination."""
    try:
        if keyword:
            entries = await history_svc.search_history(
                db, keyword=keyword, connection_id=connection_id
            )
        else:
            entries = await history_svc.list_history(
                db, connection_id=connection_id, page=page, page_size=page_size
            )
        return SuccessResponse(data=entries)
    except Exception as exc:
        return ErrorResponse(message="Failed to retrieve history.", detail=str(exc))


@router.patch("/history/{history_id}/favorite", response_model=None)
async def toggle_favorite(
    history_id: int,
    body: FavoriteToggle,
    db: AsyncSession = Depends(get_db),
):
    """Toggle the favorite status of a query history entry."""
    try:
        await history_svc.toggle_favorite(db, history_id, body.is_favorite)
        return SuccessResponse(message="Favorite status updated.")
    except Exception as exc:
        return ErrorResponse(message="Failed to update favorite.", detail=str(exc))


@router.delete("/history/{history_id}", response_model=None)
async def delete_history(
    history_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a query history entry."""
    deleted = await history_svc.delete_history(db, history_id)
    if not deleted:
        return ErrorResponse(message="History entry not found.", code=404)
    return SuccessResponse(message="History entry deleted.")
