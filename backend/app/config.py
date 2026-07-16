"""
Application configuration using pydantic-settings.

All settings can be overridden via environment variables with the DBSTUDIO_ prefix.
For example: DBSTUDIO_DEBUG=true, DBSTUDIO_DATABASE_URL=sqlite+aiosqlite:///./custom.db
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    DBStudio application settings.

    Attributes:
        APP_NAME: Display name of the application.
        APP_VERSION: Semantic version string.
        DEBUG: Enable debug mode with verbose logging and auto-reload.
        DATABASE_URL: Async SQLAlchemy connection URL for the local SQLite store.
        ENCRYPTION_KEY: 64-character hex string (32 bytes) used for AES-256 encryption
                        of stored database passwords. Generate with:
                        python -c "import secrets; print(secrets.token_hex(32))"
        API_KEY: API Key for management endpoint authentication. Empty string disables
                 the check (backward compatible). When set, all /api/ endpoints
                 require X-API-Key header.
        API_PREFIX: URL prefix applied to all API routers.
        CORS_ORIGINS: List of allowed CORS origins. Defaults to localhost dev servers.
                      Never use ["*"] with allow_credentials=True in production.
        QUERY_TIMEOUT: Maximum seconds a remote database query may run before being cancelled.
        DEFAULT_PAGE_SIZE: Default number of rows returned per page in paginated endpoints.
        MAX_EXPORT_ROWS: Upper bound on rows included in CSV/Excel/JSON exports.
        LOG_LEVEL: Python logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """

    APP_NAME: str = "DBStudio"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./dbstudio.db"
    ENCRYPTION_KEY: str = ""
    # 安全修复：新增 API Key 配置，空字符串表示禁用（向后兼容）
    API_KEY: str = ""
    API_PREFIX: str = "/api"
    # 安全修复：CORS 默认使用本地开发地址，不再使用通配符 *
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]
    QUERY_TIMEOUT: int = 30
    DEFAULT_PAGE_SIZE: int = 50
    MAX_EXPORT_ROWS: int = 100000
    LOG_LEVEL: str = "INFO"

    model_config = {
        "env_prefix": "DBSTUDIO_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
