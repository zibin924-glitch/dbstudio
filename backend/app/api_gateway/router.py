"""FastAPI router for API Gateway management and dynamic execution endpoints."""

import hashlib
import json
import logging
import time
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

# Simple in-memory response cache: {hash: {"data": ..., "timestamp": ...}}
_response_cache: dict[str, dict] = {}


def _cache_key(api_id: int, params: dict) -> str:
    """Build a deterministic cache key from API id and validated params."""
    raw = json.dumps({"api_id": api_id, "params": params}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str, ttl: int) -> dict | None:
    """Return cached data if present and not expired, else None."""
    if ttl <= 0 or key not in _response_cache:
        return None
    entry = _response_cache[key]
    if time.time() - entry["timestamp"] > ttl:
        del _response_cache[key]
        return None
    return entry["data"]


def _set_cache(key: str, data: dict) -> None:
    """Store data in the response cache with the current timestamp."""
    _response_cache[key] = {"data": data, "timestamp": time.time()}


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


@router.get("/{api_id}/logs", response_model=None)
async def get_call_logs(
    api_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List call logs for an API definition."""
    from sqlalchemy import func as sa_func

    # Count total
    count_stmt = (
        select(sa_func.count())
        .select_from(ApiCallLog)
        .where(ApiCallLog.api_id == api_id)
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch page
    stmt = (
        select(ApiCallLog)
        .where(ApiCallLog.api_id == api_id)
        .order_by(ApiCallLog.called_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return SuccessResponse(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": log.id,
                "api_id": log.api_id,
                "request_params": log.request_params,
                "response_status": log.response_status,
                "duration_ms": log.duration_ms,
                "caller_ip": log.caller_ip,
                "called_at": log.called_at.isoformat() if log.called_at else None,
            }
            for log in logs
        ],
    })


@router.get("/{api_id}/stats", response_model=None)
async def get_api_stats(api_id: int, db: AsyncSession = Depends(get_db)):
    """Get aggregated call statistics for an API."""
    from sqlalchemy import case, func as sa_func

    stmt = select(
        sa_func.count().label("total_calls"),
        sa_func.avg(ApiCallLog.duration_ms).label("avg_duration_ms"),
        sa_func.sum(
            case((ApiCallLog.response_status >= 400, 1), else_=0)
        ).label("error_count"),
    ).where(ApiCallLog.api_id == api_id)

    result = await db.execute(stmt)
    row = result.one()

    total_calls = row.total_calls or 0
    error_count = row.error_count or 0

    return SuccessResponse(data={
        "total_calls": total_calls,
        "avg_duration_ms": round(row.avg_duration_ms, 2) if row.avg_duration_ms else 0,
        "error_count": error_count,
        "error_rate": round(error_count / total_calls * 100, 2) if total_calls > 0 else 0,
    })


@router.post("/{api_id}/regenerate-token", response_model=None)
async def regenerate_token(api_id: int, db: AsyncSession = Depends(get_db)):
    """Regenerate the authentication token for an API."""
    api = await db.get(ApiDefinition, api_id)
    if not api:
        return ErrorResponse(message="API definition not found.", code=404)

    # Revoke old token
    if api.auth_token:
        token_manager.revoke_all_for_api(api.id)

    # Generate new token
    new_token = token_manager.generate_token()
    api.auth_token = new_token
    token_manager.register_token(api.id, new_token)

    await db.commit()
    await db.refresh(api)

    return SuccessResponse(data={"token": new_token}, message="Token regenerated.")


async def reload_tokens_from_db(db: AsyncSession) -> None:
    """Reload all API tokens from database into TokenManager on startup."""
    stmt = select(ApiDefinition).where(
        ApiDefinition.auth_type == "token",
        ApiDefinition.auth_token.isnot(None),
    )
    result = await db.execute(stmt)
    apis = result.scalars().all()

    for api in apis:
        token_manager.register_token(api.id, api.auth_token)

    logger.info("Reloaded %d token(s) from database into TokenManager.", len(apis))


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

    # IP whitelist check
    if api.ip_whitelist:
        try:
            whitelist = (
                json.loads(api.ip_whitelist)
                if isinstance(api.ip_whitelist, str)
                else api.ip_whitelist
            )
        except (json.JSONDecodeError, TypeError):
            whitelist = []

        if whitelist:
            client_ip = request.client.host if request.client else None
            if client_ip not in whitelist:
                return ErrorResponse(
                    message=f"IP {client_ip} is not in the whitelist.",
                    code=403,
                )

    # Rate limiting - use per-API config if available
    if api.rate_limit:
        try:
            rl_config = (
                json.loads(api.rate_limit)
                if isinstance(api.rate_limit, str)
                else api.rate_limit
            )
            rpm = rl_config.get("rpm", 60)
        except (json.JSONDecodeError, TypeError):
            rpm = 60
    else:
        rpm = 60

    rate_key = f"api_{api.id}"
    if not rate_limiter.is_allowed(rate_key, max_requests=rpm):
        return ErrorResponse(
            message="Rate limit exceeded. Please try again later.",
            code=429,
            detail={"remaining": rate_limiter.get_remaining(rate_key, max_requests=rpm)},
        )

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

    # Check cache
    if api.cache_seconds > 0:
        ck = _cache_key(api.id, validated_params)
        cached = _get_cached(ck, api.cache_seconds)
        if cached:
            return SuccessResponse(data=cached)

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

        # Store in cache
        if api.cache_seconds > 0:
            _set_cache(ck, result_data)

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
