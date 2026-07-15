import os
# Set test encryption key before any app imports
os.environ["DBSTUDIO_ENCRYPTION_KEY"] = "a" * 64  # 64 hex chars = 32 bytes

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database.models import Base
from app.database.session import get_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def encryption_key():
    # 64 hex chars = 32 bytes for AES-256
    return "a" * 64


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_db():
        async with session_factory() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_connection_config():
    return {
        "name": "Test MySQL",
        "db_type": "mysql",
        "host": "127.0.0.1",
        "port": 3306,
        "username": "root",
        "password": "test_password",
        "database_name": "test_db",
        "extra_params": {"charset": "utf8mb4"},
        "group_name": "dev",
        "tags": ["mysql", "test"],
    }


@pytest.fixture
def sample_table_metadata():
    return {
        "name": "users",
        "schema": "public",
        "table_name": "users",
        "columns": [
            {"name": "id", "type": "INTEGER", "nullable": False, "default": None,
             "primary_key": True, "auto_increment": True, "comment": "Primary key"},
            {"name": "username", "type": "VARCHAR(50)", "nullable": False, "default": None,
             "primary_key": False, "auto_increment": False, "comment": "Username"},
            {"name": "email", "type": "VARCHAR(100)", "nullable": True, "default": None,
             "primary_key": False, "auto_increment": False, "comment": "Email"},
            {"name": "status", "type": "TINYINT", "nullable": False, "default": "1",
             "primary_key": False, "auto_increment": False, "comment": "Status"},
            {"name": "created_at", "type": "DATETIME", "nullable": False,
             "default": "CURRENT_TIMESTAMP", "primary_key": False,
             "auto_increment": False, "comment": "Created time"},
        ],
        "indexes": [
            {"name": "PRIMARY", "type": "PRIMARY", "columns": ["id"], "unique": True},
            {"name": "uk_username", "type": "UNIQUE", "columns": ["username"], "unique": True},
            {"name": "idx_email", "type": "INDEX", "columns": ["email"], "unique": False},
        ],
        "foreign_keys": [],
        "properties": {
            "engine": "InnoDB", "charset": "utf8mb4", "collation": "utf8mb4_general_ci",
            "row_count": 1500, "data_size": 65536, "index_size": 16384, "comment": "Users table",
        },
    }


@pytest.fixture
def sample_table_with_fk():
    return {
        "name": "orders",
        "schema": "public",
        "table_name": "orders",
        "columns": [
            {"name": "id", "type": "INTEGER", "nullable": False, "default": None,
             "primary_key": True, "auto_increment": True, "comment": "PK"},
            {"name": "user_id", "type": "INTEGER", "nullable": False, "default": None,
             "primary_key": False, "auto_increment": False, "comment": "User ID"},
            {"name": "amount", "type": "DECIMAL(10,2)", "nullable": False, "default": "0.00",
             "primary_key": False, "auto_increment": False, "comment": "Amount"},
        ],
        "indexes": [
            {"name": "PRIMARY", "type": "PRIMARY", "columns": ["id"], "unique": True},
        ],
        "foreign_keys": [
            {"name": "fk_orders_user", "source_column": "user_id",
             "target_table": "users", "target_column": "id",
             "on_update": "CASCADE", "on_delete": "RESTRICT"},
        ],
        "properties": {
            "engine": "InnoDB", "charset": "utf8mb4",
            "row_count": 5000, "data_size": 131072, "comment": "Orders table",
        },
    }


@pytest.fixture
def sample_api_definition():
    return {
        "name": "get-user-orders",
        "method": "GET",
        "url_path": "/api/v1/user-orders",
        "sql_template": "SELECT * FROM orders WHERE user_id = :user_id AND status = :status",
        "params_definition": [
            {"name": "user_id", "type": "int", "required": True, "default": None},
            {"name": "status", "type": "str", "required": False, "default": "paid"},
        ],
        "connection_id": 1,
        "result_limit": 1000,
        "cache_seconds": 60,
        "auth_type": "token",
    }
