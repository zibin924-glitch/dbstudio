"""FastAPI router for connection management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.models import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConnectionUpdate,
)
from app.connections.pool import pool_manager
from app.connections.service import ConnectionService
from app.database.models import ApiDefinition, Connection, QueryHistory
from app.database.session import get_db
from app.utils.audit import log_audit
from app.utils.responses import ErrorResponse, SuccessResponse

router = APIRouter(prefix="/connections", tags=["Connections"])

svc = ConnectionService()


@router.post("/", status_code=201, response_model=None)
async def create_connection(
    data: ConnectionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new database connection.

    The password is encrypted before storage. Returns the connection
    details without the password field.
    """
    try:
        result = await svc.create_connection(db, data)
        await log_audit(
            db,
            action="create",
            resource_type="connection",
            resource_id=result.get("id"),
            user_info=request.client.host if request.client else None,
            details={"name": data.name, "db_type": data.db_type},
        )
        await db.commit()
        return SuccessResponse(data=result, message="Connection created successfully.")
    except Exception as exc:
        return ErrorResponse(message="Failed to create connection.", detail=str(exc))


@router.get("/", response_model=None)
async def list_connections(
    group_name: Optional[str] = Query(default=None, description="Filter by group name"),
    db: AsyncSession = Depends(get_db),
):
    """List all connections, optionally filtered by group name."""
    try:
        connections = await svc.list_connections(db, group_name=group_name)
        return SuccessResponse(data=connections)
    except Exception as exc:
        return ErrorResponse(message="Failed to list connections.", detail=str(exc))


@router.get("/{connection_id}", response_model=None)
async def get_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single connection by ID.

    Returns 404 if the connection does not exist.
    """
    connection = await svc.get_connection(db, connection_id)
    if connection is None:
        return ErrorResponse(message="Connection not found.", code=404)
    return SuccessResponse(data=connection)


@router.put("/{connection_id}", response_model=None)
async def update_connection(
    connection_id: int,
    data: ConnectionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing connection.

    Only the provided fields are updated. If the password field is included
    it will be re-encrypted.
    """
    result = await svc.update_connection(db, connection_id, data)
    if result is None:
        return ErrorResponse(message="Connection not found.", code=404)
    pool_manager.dispose_pool(connection_id)
    await log_audit(
        db,
        action="update",
        resource_type="connection",
        resource_id=connection_id,
        user_info=request.client.host if request.client else None,
        details={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
    )
    await db.commit()
    return SuccessResponse(data=result, message="Connection updated successfully.")


@router.delete("/{connection_id}", response_model=None)
async def delete_connection(
    connection_id: int,
    request: Request,
    confirm: bool = Query(
        default=False,
        description="Must be true to delete when related records exist.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Delete a connection by ID.

    If the connection has related QueryHistory or ApiDefinition records,
    a 409 Conflict is returned with the counts unless confirm=true is passed.
    When confirm=true (or no related records exist), the connection is deleted
    and related FK columns are set to NULL.

    Returns 200 with affected counts on success, 404 if not found, 409 on conflict.
    """
    # Check the connection exists
    result = await db.execute(
        select(Connection).where(Connection.id == connection_id)
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        return ErrorResponse(message="Connection not found.", code=404)

    # Count related records
    qh_count_stmt = (
        select(sa_func.count())
        .select_from(QueryHistory)
        .where(QueryHistory.connection_id == connection_id)
    )
    qh_count = (await db.execute(qh_count_stmt)).scalar() or 0

    api_count_stmt = (
        select(sa_func.count())
        .select_from(ApiDefinition)
        .where(ApiDefinition.connection_id == connection_id)
    )
    api_count = (await db.execute(api_count_stmt)).scalar() or 0

    affected = {
        "query_history": qh_count,
        "api_definitions": api_count,
    }
    has_related = (qh_count + api_count) > 0

    # If there are related records and the caller hasn't confirmed, reject
    if has_related and not confirm:
        raise HTTPException(
            status_code=409,
            detail={
                "code": 409,
                "message": (
                    f"This connection has {qh_count} query history record(s) and "
                    f"{api_count} API definition(s) that will be orphaned. "
                    f"Pass confirm=true to proceed."
                ),
                "affected": affected,
            },
        )

    # Perform the delete (FK columns on related rows will be SET NULL by the DB)
    await db.delete(connection)
    await db.flush()

    pool_manager.dispose_pool(connection_id)

    await log_audit(
        db,
        action="delete",
        resource_type="connection",
        resource_id=connection_id,
        user_info=request.client.host if request.client else None,
        details={"affected": affected},
    )
    await db.commit()

    return SuccessResponse(
        data={"deleted": True, "affected": affected},
        message="Connection deleted successfully.",
    )


@router.post("/test", response_model=None)
async def test_connection(data: ConnectionTestRequest):
    """Test a database connection without saving it.

    Attempts to connect to the specified database and returns the result.
    """
    config = data.model_dump()
    result = svc.test_connection(config)
    response = ConnectionTestResponse(**result)
    if response.status == "success":
        return SuccessResponse(data=response.model_dump(), message=response.message)
    return ErrorResponse(message=response.message, code=400)


@router.post("/{connection_id}/test", response_model=None)
async def test_saved_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Test an existing saved connection.

    Loads the connection from the database, decrypts the password,
    and attempts to connect.
    """
    conn = await svc.get_connection_model(db, connection_id)
    if not conn:
        return ErrorResponse(message="Connection not found.", code=404)

    password = svc.get_decrypted_password(conn)
    config = {
        "db_type": conn.db_type,
        "host": conn.host,
        "port": conn.port,
        "username": conn.username,
        "password": password,
        "database_name": conn.database_name,
        "extra_params": conn.extra_params,
    }

    result = svc.test_connection(config)
    if result["status"] == "success":
        return SuccessResponse(data=result)
    return ErrorResponse(message=result["message"], code=400)
