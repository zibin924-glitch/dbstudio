"""FastAPI router for database metadata exploration endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.pool import pool_manager
from app.connections.service import ConnectionService
from app.database.session import get_db
from app.explorer.service import ExplorerService
from app.utils.responses import ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explorer", tags=["Explorer"])

svc = ConnectionService()


def _get_engine_and_inspector(connection_id: int, connection_model, db_config: dict):
    """Build an engine (via pool manager) and return an Inspector."""
    engine = pool_manager.get_or_create_pool(connection_id, db_config)
    inspector = inspect(engine)
    return engine, inspector


def _build_config_from_model(connection_model) -> dict:
    """Build a connection config dict from a Connection ORM model."""
    return {
        "db_type": connection_model.db_type,
        "host": connection_model.host,
        "port": connection_model.port,
        "username": connection_model.username,
        "password": ConnectionService.get_decrypted_password(connection_model),
        "database_name": connection_model.database_name,
        "extra_params": connection_model.get_extra_params(),
        "pool_size": connection_model.pool_size,
    }


async def _resolve_connection(db: AsyncSession, connection_id: int):
    """Resolve a connection and return (connection_model, config, engine, inspector) or raise."""
    connection = await svc.get_connection_model(db, connection_id)
    if connection is None:
        return None
    config = _build_config_from_model(connection)
    engine, inspector = _get_engine_and_inspector(connection_id, connection, config)
    return connection, config, engine, inspector


@router.get("/{connection_id}/schemas", response_model=None)
async def list_schemas(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all schemas in the connected database."""
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    explorer = ExplorerService(inspector)
    schemas = explorer.get_schema_list()
    return SuccessResponse(data=schemas)


@router.get("/{connection_id}/tables", response_model=None)
async def list_tables(
    connection_id: int,
    schema: Optional[str] = Query(default=None, description="Schema name filter"),
    db: AsyncSession = Depends(get_db),
):
    """List all tables in the connected database, optionally filtered by schema."""
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    explorer = ExplorerService(inspector)
    tables = explorer.get_table_list(schema=schema)
    return SuccessResponse(data=tables)


@router.get("/{connection_id}/tables/{table_name}/columns", response_model=None)
async def get_columns(
    connection_id: int,
    table_name: str,
    schema: Optional[str] = Query(default=None, description="Schema name"),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed column information for a specific table."""
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    explorer = ExplorerService(inspector)
    columns = explorer.get_columns(table_name, schema=schema)
    if not columns:
        return ErrorResponse(
            message=f"Table '{table_name}' not found or has no columns.", code=404
        )
    return SuccessResponse(data=columns)


@router.get("/{connection_id}/tables/{table_name}/indexes", response_model=None)
async def get_indexes(
    connection_id: int,
    table_name: str,
    schema: Optional[str] = Query(default=None, description="Schema name"),
    db: AsyncSession = Depends(get_db),
):
    """Get index information for a specific table."""
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    explorer = ExplorerService(inspector)
    indexes = explorer.get_indexes(table_name, schema=schema)
    return SuccessResponse(data=indexes)


@router.get("/{connection_id}/tables/{table_name}/foreign-keys", response_model=None)
async def get_foreign_keys(
    connection_id: int,
    table_name: str,
    schema: Optional[str] = Query(default=None, description="Schema name"),
    db: AsyncSession = Depends(get_db),
):
    """Get foreign key information for a specific table."""
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    explorer = ExplorerService(inspector)
    fks = explorer.get_foreign_keys(table_name, schema=schema)
    return SuccessResponse(data=fks)


@router.get("/{connection_id}/tables/{table_name}/data", response_model=None)
async def preview_table_data(
    connection_id: int,
    table_name: str,
    schema: Optional[str] = Query(default=None, description="Schema name"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Rows per page"),
    db: AsyncSession = Depends(get_db),
):
    """Preview data from a table with pagination.

    Returns column names, rows, and pagination metadata.
    """
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    offset = (page - 1) * page_size

    qualified_name = f"{schema}.{table_name}" if schema else table_name

    try:
        with engine.connect() as conn:
            # Get total count
            count_sql = text(f"SELECT COUNT(*) FROM {qualified_name}")
            count_result = conn.execute(count_sql)
            total = count_result.scalar() or 0

            # Get paginated data
            data_sql = text(
                f"SELECT * FROM {qualified_name} LIMIT :limit OFFSET :offset"
            )
            result = conn.execute(data_sql, {"limit": page_size, "offset": offset})
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]

        return SuccessResponse(data={
            "columns": columns,
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    except Exception as exc:
        logger.warning("Failed to preview data for %s: %s", qualified_name, exc)
        return ErrorResponse(
            message=f"Failed to retrieve data from '{table_name}': {exc}", code=400
        )


@router.get("/{connection_id}/stats", response_model=None)
async def get_database_stats(
    connection_id: int,
    schema: Optional[str] = Query(default=None, description="Schema name"),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate database statistics (table count, row estimates, etc.)."""
    resolved = await _resolve_connection(db, connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, config, engine, inspector = resolved
    explorer = ExplorerService(inspector)
    stats = explorer.get_database_stats(schema=schema)
    return SuccessResponse(data=stats)
