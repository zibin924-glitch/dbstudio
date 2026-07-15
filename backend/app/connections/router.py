"""FastAPI router for connection management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.models import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConnectionUpdate,
)
from app.connections.service import ConnectionService
from app.database.session import get_db
from app.utils.responses import ErrorResponse, SuccessResponse

router = APIRouter(prefix="/connections", tags=["Connections"])

svc = ConnectionService()


@router.post("/", response_model=None)
async def create_connection(
    data: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new database connection.

    The password is encrypted before storage. Returns the connection
    details without the password field.
    """
    try:
        result = await svc.create_connection(db, data)
        return SuccessResponse(data=result, message="Connection created successfully.", code=201)
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
    db: AsyncSession = Depends(get_db),
):
    """Update an existing connection.

    Only the provided fields are updated. If the password field is included
    it will be re-encrypted.
    """
    result = await svc.update_connection(db, connection_id, data)
    if result is None:
        return ErrorResponse(message="Connection not found.", code=404)
    return SuccessResponse(data=result, message="Connection updated successfully.")


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a connection by ID.

    Returns 204 No Content on success, 404 if not found.
    """
    deleted = await svc.delete_connection(db, connection_id)
    if not deleted:
        return ErrorResponse(message="Connection not found.", code=404)
    return None


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
