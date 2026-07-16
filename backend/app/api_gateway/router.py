"""FastAPI router for API Gateway management and dynamic execution endpoints."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_gateway.auth import token_manager
from app.api_gateway.gateway import ApiGateway
from app.api_gateway.models import (
    ApiCallRequest,
    ApiCallResponse,
    ApiCreate,
    ApiResponse,
    ApiUpdate,
    ExtractParamsRequest,
    ToggleEnabledRequest,
)
from app.api_gateway.rate_limiter import rate_limiter
from app.connections.pool import pool_manager
from app.connections.service import ConnectionService
from app.database.models import ApiCallLog, ApiDefinition
from app.database.session import get_db
from app.utils.responses import ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

# Management endpoints router
router = APIRouter(prefix="/gateway/apis", tags=["API Gateway"])

# Dynamic gateway router (separate, no prefix - handled by path)
dynamic_router = APIRouter(tags=["API Gateway"])

gateway = ApiGateway()
conn_svc = ConnectionService()


# --- Helpers ---


def _to_response_dict(api: ApiDefinition) -> dict:
    """Convert ApiDefinition ORM model to response dictionary."""
    params_def = []
    if api.params_definition:
        try:
            params_def = json.loads(api.params_definition)
        except (json.JSONDecodeError, TypeError):
            params_def = []

    return {
        "id": api.id,
        "name": api.name,
        "method": api.method,
        "url_path": api.url_path,
        "sql_template": api.sql_template,
        "params_definition": params_def,
        "connection_id": api.connection_id,
        "result_limit": api.result_limit,
        "cache_seconds": api.cache_seconds,
        "auth_type": api.auth_type,
        "token": api.auth_token,
        "is_enabled": api.is_enabled,
        "created_at": api.created_at,
        "updated_at": api.updated_at,
    }


# --- Management Endpoints ---


@router.post("/", response_model=None)
async def create_api(
    data: ApiCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new API definition.

    Validates that the SQL template is a safe SELECT query. If auth_type
    is 'token', auto-generates and stores an authentication token.
    """
    # Validate SQL safety
    if not gateway.is_safe_sql(data.sql_template):
        return ErrorResponse(
            message="SQL template must be a SELECT query. DML/DDL statements are not allowed.",
            code=400,
        )

    # Generate token if auth_type is token
    token = None
    if data.auth_type == "token":
        token = token_manager.generate_token()

    api = ApiDefinition(
        name=data.name,
        method=data.method.upper(),
        url_path=data.url_path,
        sql_template=data.sql_template,
        params_definition=json.dumps([p.model_dump() for p in data.params_definition]),
        connection_id=data.connection_id,
        result_limit=data.result_limit,
        cache_seconds=data.cache_seconds,
        auth_type=data.auth_type,
        auth_token=token,
        is_enabled=True,
    )

    db.add(api)
    await session_flush(db)
    await db.refresh(api)

    # Register token in the token manager
    if token:
        token_manager.register_token(api.id, token)

    return SuccessResponse(data=_to_response_dict(api), message="API created successfully.", code=201)


async def session_flush(db: AsyncSession):
    """Helper to flush session."""
    await db.flush()


@router.get("/", response_model=None)
async def list_apis(db: AsyncSession = Depends(get_db)):
    """List all API definitions."""
    try:
        result = await db.execute(select(ApiDefinition).order_by(ApiDefinition.id))
        apis = result.scalars().all()
        return SuccessResponse(data=[_to_response_dict(a) for a in apis])
    except Exception as exc:
        return ErrorResponse(message="Failed to list APIs.", detail=str(exc))


@router.get("/{api_id}", response_model=None)
async def get_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single API definition by ID."""
    result = await db.execute(select(ApiDefinition).where(ApiDefinition.id == api_id))
    api = result.scalar_one_or_none()
    if api is None:
        return ErrorResponse(message="API definition not found.", code=404)
    return SuccessResponse(data=_to_response_dict(api))


@router.put("/{api_id}", response_model=None)
async def update_api(
    api_id: int,
    data: ApiUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing API definition."""
    result = await db.execute(select(ApiDefinition).where(ApiDefinition.id == api_id))
    api = result.scalar_one_or_none()
    if api is None:
        return ErrorResponse(message="API definition not found.", code=404)

    update_data = data.model_dump(exclude_unset=True)

    # If SQL template is being updated, validate it
    if "sql_template" in update_data and update_data["sql_template"] is not None:
        if not gateway.is_safe_sql(update_data["sql_template"]):
            return ErrorResponse(
                message="SQL template must be a SELECT query.",
                code=400,
            )

    for field, value in update_data.items():
        if field == "params_definition" and value is not None:
            api.params_definition = json.dumps([p.model_dump() if hasattr(p, "model_dump") else p for p in value])
        elif field == "auth_type":
            old_auth = api.auth_type
            api.auth_type = value
            # Auto-generate token if switching to token auth
            if value == "token" and old_auth != "token":
                token = token_manager.generate_token()
                api.auth_token = token
                token_manager.register_token(api.id, token)
            elif value != "token" and api.auth_token:
                token_manager.revoke_all_for_api(api.id)
                api.auth_token = None
        else:
            setattr(api, field, value)

    await db.flush()
    await db.refresh(api)
    return SuccessResponse(data=_to_response_dict(api), message="API updated successfully.")


@router.patch("/{api_id}", response_model=None)
async def toggle_api(
    api_id: int,
    body: ToggleEnabledRequest,
    db: AsyncSession = Depends(get_db),
):
    """Toggle an API definition's enabled/disabled state."""
    result = await db.execute(select(ApiDefinition).where(ApiDefinition.id == api_id))
    api = result.scalar_one_or_none()
    if api is None:
        return ErrorResponse(message="API definition not found.", code=404)

    api.is_enabled = body.is_enabled
    await db.flush()
    await db.refresh(api)

    status = "enabled" if body.is_enabled else "disabled"
    return SuccessResponse(data=_to_response_dict(api), message=f"API {status}.")


@router.delete("/{api_id}", status_code=204)
async def delete_api(
    api_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an API definition. Returns 204 on success."""
    result = await db.execute(select(ApiDefinition).where(ApiDefinition.id == api_id))
    api = result.scalar_one_or_none()
    if api is None:
        return ErrorResponse(message="API definition not found.", code=404)

    # Revoke tokens
    if api.auth_token:
        token_manager.revoke_all_for_api(api.id)

    await db.delete(api)
    await db.flush()
    return None


@router.post("/extract-params", response_model=None)
async def extract_params(req: ExtractParamsRequest):
    """Extract parameter names from a SQL template.

    Finds all :param_name patterns and returns a deduplicated list.
    """
    params = gateway.extract_params(req.sql)
    return SuccessResponse(data={"params": params, "sql": req.sql})


# --- Dynamic Gateway Endpoint ---


@dynamic_router.api_route("/gateway/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def dynamic_gateway(
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    """Route incoming requests to matching API definitions.

    Matches the URL path to a registered API definition, verifies
    authentication, validates parameters, executes the SQL template,
    and returns results. Logs every call.
    """
    # Find matching API definition by url_path
    url_path = f"/{path}" if not path.startswith("/") else path
    result = await db.execute(
        select(ApiDefinition).where(ApiDefinition.url_path == url_path)
    )
    api = result.scalar_one_or_none()

    if api is None:
        return ErrorResponse(message=f"No API found for path: {url_path}", code=404)

    # Check if API is enabled
    if not api.is_enabled:
        return ErrorResponse(message="This API is currently disabled.", code=503)

    # Rate limiting
    rate_key = f"api_{api.id}"
    if not rate_limiter.is_allowed(rate_key):
        return ErrorResponse(message="Rate limit exceeded. Please try again later.", code=429)

    # Authentication
    token = None
    if authorization:
        # Support "Bearer <token>" or raw token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

    if not token_manager.verify_token(token or "", api.id, auth_type=api.auth_type):
        return ErrorResponse(message="Authentication failed. Invalid or missing token.", code=401)

    # Extract parameters from request (query params + body)
    params: dict = {}
    if request.query_params:
        params.update(dict(request.query_params))
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
            if isinstance(body, dict) and "params" in body:
                params.update(body["params"])
            elif isinstance(body, dict):
                params.update(body)
        except Exception:
            pass

    # Validate parameters
    params_def = []
    if api.params_definition:
        try:
            params_def = json.loads(api.params_definition)
        except (json.JSONDecodeError, TypeError):
            params_def = []

    try:
        validated_params = gateway.validate_params(params_def, params)
    except ValueError as exc:
        return ErrorResponse(message=f"Parameter validation failed: {exc}", code=400)

    # Get database connection
    connection = await conn_svc.get_connection_model(db, api.connection_id)
    if connection is None:
        return ErrorResponse(message="Associated database connection not found.", code=500)

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
    engine = pool_manager.get_or_create_pool(api.connection_id, config)

    # Execute the query
    try:
        result_data = gateway.execute_api(api.sql_template, validated_params, engine)

        # Apply result limit
        if len(result_data["data"]) > api.result_limit:
            result_data["data"] = result_data["data"][: api.result_limit]
            result_data["total"] = len(result_data["data"])

        # Log the call
        call_log = ApiCallLog(
            api_id=api.id,
            request_params=json.dumps(validated_params, default=str),
            response_status=200,
            duration_ms=result_data["duration_ms"],
            caller_ip=request.client.host if request.client else None,
        )
        db.add(call_log)

        return SuccessResponse(data=result_data)

    except Exception as exc:
        # Log the failure
        call_log = ApiCallLog(
            api_id=api.id,
            request_params=json.dumps(validated_params, default=str),
            response_status=500,
            duration_ms=0,
            caller_ip=request.client.host if request.client else None,
        )
        db.add(call_log)

        logger.warning("API execution failed for api_id=%d: %s", api.id, exc)
        return ErrorResponse(message="Query execution failed.", detail=str(exc))
