"""
DBStudio FastAPI application entry point.

Configures middleware, lifespan events, and mounts all API routers
under the /api prefix.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import init_db
from app.routers import connections, explorer, query, generator, api_gateway
from app.routers import audit as audit_router
from app.api_gateway.router import dynamic_router
# 安全修复：导入 API Key 认证中间件和请求体大小限制中间件
from app.auth import ApiKeyMiddleware
from app.main_middleware import RequestSizeLimitMiddleware


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    On startup: initialises the local SQLite database (creates tables that
    do not yet exist) and configures the root logger level. If Alembic
    migrations are available, they are applied automatically.

    On shutdown: currently a no-op; reserved for future pool / cache cleanup.

    Migration workflow:
        - To create a new migration:
            cd backend && alembic revision --autogenerate -m "describe change"
        - To apply pending migrations:
            cd backend && alembic upgrade head
        - To rollback one step:
            cd backend && alembic downgrade -1
        - Migrations are also applied automatically on application startup
          when the alembic package is available.
    """
    # ── Startup ────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    # ── Run Alembic migrations if available ────────────────────────────────
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        import os

        alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        if os.path.exists(alembic_ini):
            logger.info("Running Alembic migrations (upgrade head) ...")
            alembic_cfg = AlembicConfig(alembic_ini)
            # Convert async URL to sync for alembic
            _url = settings.DATABASE_URL
            _url = _url.replace("sqlite+aiosqlite://", "sqlite://")
            _url = _url.replace("postgresql+asyncpg://", "postgresql://")
            _url = _url.replace("mysql+aiomysql://", "mysql+pymysql://")
            alembic_cfg.set_main_option("sqlalchemy.url", _url)
            alembic_command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations applied successfully.")
        else:
            logger.info("No alembic.ini found; falling back to init_db (create_all).")
            await init_db()
    except ImportError:
        logger.info("Alembic not installed; falling back to init_db (create_all).")
        await init_db()
    except Exception as exc:
        logger.warning("Alembic migration failed (%s); falling back to init_db.", exc)
        await init_db()

    # Reload API tokens from database into in-memory TokenManager
    from app.database.session import AsyncSessionLocal
    from app.api_gateway.router import reload_tokens_from_db

    async with AsyncSessionLocal() as session:
        await reload_tokens_from_db(session)

    logger.info("DBStudio %s ready  (debug=%s)", settings.APP_VERSION, settings.DEBUG)

    yield  # ── Application runs ──────────────────────────────────────────

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("Shutting down DBStudio ...")


# ── Application instance ──────────────────────────────────────────────────────

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

# ── Middleware（注意：FastAPI 中后添加的中间件在外层，先执行）────────────
# 添加顺序：最内层先添加，最外层最后添加
# 执行顺序：CORS -> RequestSizeLimit -> ApiKey -> Router

# 安全修复：请求体大小限制中间件（10MB），内层
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=10 * 1024 * 1024)

# 安全修复：API Key 认证中间件，中层
app.add_middleware(ApiKeyMiddleware)

# CORS 中间件，最外层（优先处理 OPTIONS 预检请求）
# 安全修复：CORS 配置已优化，默认不再使用通配符 *
_cors_origins = settings.CORS_ORIGINS
_cors_credentials = True
# 安全修复：当 origins 包含 * 时不允许 credentials，避免安全风险
if "*" in _cors_origins:
    logger.warning(
        "CORS_ORIGINS 包含通配符 '*'，已自动禁用 allow_credentials 以防止安全风险。"
        "请在生产环境中配置具体的可信来源。"
    )
    _cors_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(connections.router, prefix=settings.API_PREFIX)
app.include_router(explorer.router, prefix=settings.API_PREFIX)
app.include_router(query.router, prefix=settings.API_PREFIX)
app.include_router(generator.router, prefix=settings.API_PREFIX)
app.include_router(api_gateway.router, prefix=settings.API_PREFIX)
app.include_router(audit_router.router, prefix=settings.API_PREFIX)
app.include_router(dynamic_router, prefix=settings.API_PREFIX)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get(f"{settings.API_PREFIX}/health", tags=["system"])
async def health_check():
    """
    Lightweight liveness probe.

    Returns the application name and version. Use this endpoint for
    load-balancer health checks and Kubernetes liveness/readiness probes.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
