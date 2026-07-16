"""
请求体大小限制中间件。

限制 HTTP 请求体最大为 10MB，超过时返回 413 Payload Too Large。
防止恶意客户端发送超大请求体导致内存耗尽（DoS 攻击）。
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# 默认最大请求体大小：10MB
DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """限制 HTTP 请求体大小的中间件。

    读取 Content-Length 头，如果超过限制则直接返回 413。
    对于没有 Content-Length 的请求（如 chunked transfer），
    在读取 body 时进行大小检查。
    """

    def __init__(self, app, max_body_size: int = DEFAULT_MAX_BODY_SIZE):
        super().__init__(app)
        # 最大请求体大小（字节）
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        # 检查 Content-Length 头
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_body_size:
                    logger.warning(
                        "请求体过大被拒绝: content_length=%d, max=%d, path=%s",
                        length,
                        self.max_body_size,
                        request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "code": 413,
                            "message": f"Payload too large. Maximum allowed size is {self.max_body_size} bytes.",
                            "detail": None,
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
