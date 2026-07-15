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


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    On startup: initialises the local SQLite database (creates tables that
    do not yet exist) and configures the root logger level.

    On shutdown: currently a no-op; reserved for future pool / cache cleanup.
    """
    # ── Startup ────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    logger.info("Initialising local database tables …")
    await init_db()
    logger.info("DBStudio %s ready  (debug=%s)", settings.APP_VERSION, settings.DEBUG)

    yield  # ── Application runs ──────────────────────────────────────────

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("Shutting down DBStudio …")


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

# ── CORS middleware ────────────────────────────────────────────────────────────
# In production, replace ["*"] with explicit trusted origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(connections.router, prefix=settings.API_PREFIX)
app.include_router(explorer.router, prefix=settings.API_PREFIX)
app.include_router(query.router, prefix=settings.API_PREFIX)
app.include_router(generator.router, prefix=settings.API_PREFIX)
app.include_router(api_gateway.router, prefix=settings.API_PREFIX)


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
