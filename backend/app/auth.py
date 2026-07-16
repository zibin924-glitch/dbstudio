"""
API Key 认证中间件。

当 DBSTUDIO_API_KEY 环境变量被配置时，所有 /api/ 端点都需要
在请求头中包含 X-API-Key 并通过校验。

豁免端点：
- /api/health（健康检查）
- /gateway/{path:path}（动态网关，有独立的认证机制）
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# 豁免路径列表：这些路径不需要 API Key 认证
_EXEMPT_PATHS = [
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
]

# 动态网关路径前缀（/api/gateway/ 开头但排除 /api/gateway/apis/ 管理端点）
_DYNAMIC_GATEWAY_PREFIX = "/api/gateway/"
_MANAGEMENT_API_PREFIX = "/api/gateway/apis/"


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件。

    当 settings.API_KEY 非空时，对除豁免路径外的所有 /api/ 请求
    校验 X-API-Key 请求头。校验失败返回 401 Unauthorized。

    豁免规则：
    - /api/health 等固定路径
    - /api/gateway/{path} 动态网关路径（有独立认证机制）
    - 注意：/api/gateway/apis/ 管理端点不在豁免范围内
    """

    async def dispatch(self, request: Request, call_next):
        # 如果 API_KEY 未配置，跳过认证（向后兼容）
        if not settings.API_KEY:
            return await call_next(request)

        path = request.url.path

        # 非 /api/ 前缀的请求直接放行（如静态资源）
        if not path.startswith(settings.API_PREFIX):
            return await call_next(request)

        # 检查固定豁免路径
        for exempt in _EXEMPT_PATHS:
            if path == exempt or path.startswith(exempt + "/"):
                return await call_next(request)

        # 安全修复：动态网关路径豁免（有独立的 Bearer Token 认证），
        # 但管理端点 /api/gateway/apis/ 需要 API Key 保护
        if path.startswith(_DYNAMIC_GATEWAY_PREFIX) and not path.startswith(_MANAGEMENT_API_PREFIX):
            return await call_next(request)

        # 校验 X-API-Key 请求头
        api_key = request.headers.get("X-API-Key", "")
        if not api_key or api_key != settings.API_KEY:
            logger.warning(
                "API Key 认证失败: path=%s, ip=%s",
                path,
                request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "message": "Unauthorized: Invalid or missing X-API-Key header.",
                    "detail": None,
                },
            )

        return await call_next(request)
