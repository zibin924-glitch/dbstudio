# DBStudio — 数据库开发工具 测试计划与用例文档

## 文档基本信息

| 项目 | 内容 |
|------|------|
| 项目名称 | DBStudio — 数据库开发工具 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-15 |
| 关联文档 | 《DBStudio 需求规格说明书》、《DBStudio 项目整体计划》 |

---

## 一、测试策略总览

### 1.1 测试分层

```
┌─────────────────────────────────────────┐
│           E2E 测试（Playwright）          │  ← 全流程用户场景（可选）
├─────────────────────────────────────────┤
│       集成测试（pytest + httpx）          │  ← API 端到端，含数据库交互
├─────────────────────────────────────────┤
│    单元测试（pytest + pytest-asyncio）    │  ← Service 层、工具函数、类型映射
└─────────────────────────────────────────┘
```

### 1.2 测试工具

| 工具 | 用途 | 版本要求 |
|------|------|----------|
| pytest | 测试框架 | ≥ 7.4 |
| pytest-asyncio | 异步测试支持 | ≥ 0.21 |
| httpx (AsyncClient) | FastAPI 集成测试 | ≥ 0.24 |
| pytest-cov | 覆盖率统计 | ≥ 4.1 |
| pytest-mock | Mock 工具 | ≥ 3.11 |
| factory-boy | 测试数据工厂 | ≥ 3.3 |
| aiosqlite | 异步 SQLite 测试 | ≥ 0.19 |

### 1.3 覆盖率目标

| 层级 | 行覆盖率目标 | 说明 |
|------|-------------|------|
| 工具函数（crypto、类型映射等） | ≥ 95% | 核心逻辑，需高度覆盖 |
| Service 层 | ≥ 85% | 业务逻辑主体 |
| API Router 层 | ≥ 80% | 接口参数校验和响应格式 |
| 整体后端覆盖率 | ≥ 80% | 全项目整体要求 |

### 1.4 Mock 策略

| 被测对象 | Mock 方式 | 说明 |
|----------|----------|------|
| MySQL / PostgreSQL / Oracle 驱动 | `unittest.mock.patch` 或 `pytest-mock` | 单元测试中 Mock 数据库连接，避免依赖真实数据库 |
| SQLAlchemy Engine | 使用内存 SQLite 替代 | 集成测试中使用 `sqlite:///:memory:` 做本地存储测试 |
| 加密模块 | 直接调用 | 加密解密为纯函数，无需 Mock |
| 文件系统 | `tmp_path` fixture | 文档/代码生成测试中使用临时目录 |

---

## 二、测试环境搭建

### 2.1 安装测试依赖

```bash
# backend/requirements-test.txt
pytest>=7.4
pytest-asyncio>=0.21
pytest-cov>=4.1
pytest-mock>=3.11
httpx>=0.24
factory-boy>=3.3
aiosqlite>=0.19
```

```bash
pip install -r requirements-test.txt
```

### 2.2 测试目录结构

```
backend/
├── tests/
│   ├── conftest.py                    # 全局 fixtures
│   ├── factories.py                   # 测试数据工厂
│   │
│   ├── unit/                          # 单元测试
│   │   ├── __init__.py
│   │   ├── test_crypto.py             # 加密模块
│   │   ├── test_connection_service.py # 连接管理 Service
│   │   ├── test_connection_pool.py    # 连接池管理
│   │   ├── test_explorer_service.py   # 结构浏览 Service
│   │   ├── test_query_executor.py     # SQL 执行引擎
│   │   ├── test_query_guard.py        # 只读保护
│   │   ├── test_query_history.py      # 查询历史
│   │   ├── test_doc_generator.py      # 文档生成
│   │   ├── test_code_generator.py     # 代码生成
│   │   ├── test_ddl_generator.py      # DDL 生成
│   │   ├── test_ddl_converter.py      # DDL 跨库转换
│   │   ├── test_api_gateway.py        # API 网关引擎
│   │   ├── test_api_auth.py           # API 认证
│   │   ├── test_rate_limiter.py       # 限流
│   │   └── test_type_mapping.py       # 类型映射
│   │
│   ├── integration/                   # 集成测试
│   │   ├── __init__.py
│   │   ├── test_connections_api.py    # 连接管理 API
│   │   ├── test_explorer_api.py       # 结构浏览 API
│   │   ├── test_query_api.py          # SQL 查询 API
│   │   ├── test_generator_api.py      # 文档/代码生成 API
│   │   ├── test_api_gateway_api.py    # SQL-to-API 管理接口
│   │   ├── test_api_gateway_call.py   # 发布后的 API 调用
│   │   └── test_export_api.py         # 导出接口
│   │
│   └── security/                      # 安全测试
│       ├── __init__.py
│       ├── test_sql_injection.py      # SQL 注入防护
│       └── test_auth_security.py      # 认证安全
│
├── pytest.ini                         # pytest 配置
└── requirements-test.txt
```

### 2.3 pytest 配置

```ini
# backend/pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts =
    -v
    --tb=short
    --strict-markers
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov

markers =
    unit: 单元测试
    integration: 集成测试
    security: 安全测试
    slow: 耗时较长的测试（可通过 -m "not slow" 跳过）
```

---

## 三、全局 Fixtures 与测试数据工厂

### 3.1 conftest.py — 全局 Fixtures

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.models import Base
from app.config import Settings


@pytest.fixture(scope="session")
def anyio_backend():
    """使用 asyncio 作为异步后端"""
    return "asyncio"


@pytest.fixture
def encryption_key() -> str:
    """测试用 AES-256 加密密钥（32 字节 hex）"""
    return "a" * 64  # 64 个 hex 字符 = 32 字节


@pytest_asyncio.fixture
async def db_engine():
    """创建内存 SQLite 引擎，用于集成测试"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """创建测试用数据库会话"""
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """创建 FastAPI 测试客户端，注入测试数据库"""
    # 覆写数据库依赖
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    from app.database.deps import get_db
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_connection_config():
    """MySQL 连接配置样本"""
    return {
        "name": "测试MySQL连接",
        "db_type": "mysql",
        "host": "127.0.0.1",
        "port": 3306,
        "username": "root",
        "password": "test_password",
        "database_name": "test_db",
        "extra_params": {"charset": "utf8mb4"},
        "group_name": "开发环境",
        "tags": ["mysql", "dev"],
    }


@pytest.fixture
def sample_pg_connection_config():
    """PostgreSQL 连接配置样本"""
    return {
        "name": "测试PG连接",
        "db_type": "postgresql",
        "host": "127.0.0.1",
        "port": 5432,
        "username": "postgres",
        "password": "test_password",
        "database_name": "test_db",
        "extra_params": {},
        "group_name": "测试环境",
        "tags": ["pg", "test"],
    }


@pytest.fixture
def sample_table_metadata():
    """模拟表元数据（用于结构浏览、文档生成、代码生成测试）"""
    return {
        "schema": "public",
        "table_name": "users",
        "columns": [
            {"name": "id", "type": "INTEGER", "nullable": False, "default": None,
             "primary_key": True, "auto_increment": True, "comment": "主键ID"},
            {"name": "username", "type": "VARCHAR(50)", "nullable": False, "default": None,
             "primary_key": False, "auto_increment": False, "comment": "用户名"},
            {"name": "email", "type": "VARCHAR(100)", "nullable": True, "default": None,
             "primary_key": False, "auto_increment": False, "comment": "邮箱"},
            {"name": "status", "type": "TINYINT", "nullable": False, "default": "1",
             "primary_key": False, "auto_increment": False, "comment": "状态: 0禁用 1启用"},
            {"name": "created_at", "type": "DATETIME", "nullable": False,
             "default": "CURRENT_TIMESTAMP", "primary_key": False,
             "auto_increment": False, "comment": "创建时间"},
        ],
        "indexes": [
            {"name": "PRIMARY", "type": "PRIMARY", "columns": ["id"], "unique": True},
            {"name": "uk_username", "type": "UNIQUE", "columns": ["username"], "unique": True},
            {"name": "idx_email", "type": "INDEX", "columns": ["email"], "unique": False},
        ],
        "foreign_keys": [],
        "properties": {
            "engine": "InnoDB",
            "charset": "utf8mb4",
            "collation": "utf8mb4_general_ci",
            "row_count": 1500,
            "data_size": 65536,
            "index_size": 16384,
            "comment": "用户表",
        },
    }


@pytest.fixture
def sample_table_with_fk():
    """带外键的表元数据（orders 表）"""
    return {
        "schema": "public",
        "table_name": "orders",
        "columns": [
            {"name": "id", "type": "INTEGER", "nullable": False, "default": None,
             "primary_key": True, "auto_increment": True, "comment": "主键"},
            {"name": "user_id", "type": "INTEGER", "nullable": False, "default": None,
             "primary_key": False, "auto_increment": False, "comment": "用户ID"},
            {"name": "amount", "type": "DECIMAL(10,2)", "nullable": False, "default": "0.00",
             "primary_key": False, "auto_increment": False, "comment": "订单金额"},
            {"name": "status", "type": "VARCHAR(20)", "nullable": False, "default": "'pending'",
             "primary_key": False, "auto_increment": False, "comment": "订单状态"},
        ],
        "indexes": [
            {"name": "PRIMARY", "type": "PRIMARY", "columns": ["id"], "unique": True},
            {"name": "idx_user_id", "type": "INDEX", "columns": ["user_id"], "unique": False},
        ],
        "foreign_keys": [
            {"name": "fk_orders_user", "source_column": "user_id",
             "target_table": "users", "target_column": "id",
             "on_update": "CASCADE", "on_delete": "RESTRICT"},
        ],
        "properties": {
            "engine": "InnoDB", "charset": "utf8mb4",
            "collation": "utf8mb4_general_ci",
            "row_count": 5000, "data_size": 131072, "index_size": 32768,
            "comment": "订单表",
        },
    }


@pytest.fixture
def sample_api_definition():
    """API 定义样本"""
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
```

### 3.2 factories.py — 测试数据工厂

```python
# tests/factories.py
import factory
from datetime import datetime


class ConnectionFactory(factory.Factory):
    """连接配置工厂"""
    class Meta:
        model = dict

    name = factory.Sequence(lambda n: f"连接-{n}")
    db_type = "mysql"
    host = "127.0.0.1"
    port = 3306
    username = "root"
    password = "password123"
    database_name = "test_db"
    extra_params = {}
    group_name = "默认分组"
    tags = []
    pool_size = 5


class PostgreSQLConnectionFactory(ConnectionFactory):
    """PostgreSQL 连接工厂"""
    db_type = "postgresql"
    port = 5432
    username = "postgres"


class OracleConnectionFactory(ConnectionFactory):
    """Oracle 连接工厂"""
    db_type = "oracle"
    port = 1521
    username = "system"


class QueryHistoryFactory(factory.Factory):
    """查询历史工厂"""
    class Meta:
        model = dict

    connection_id = 1
    sql_text = "SELECT 1"
    execution_time = factory.LazyFunction(datetime.now)
    duration_ms = 50
    row_count = 1
    status = "success"
    error_message = None
    is_favorite = False


class ApiDefinitionFactory(factory.Factory):
    """API 定义工厂"""
    class Meta:
        model = dict

    name = factory.Sequence(lambda n: f"api-{n}")
    method = "GET"
    url_path = factory.LazyAttribute(lambda o: f"/api/v1/{o.name}")
    sql_template = "SELECT * FROM test_table WHERE id = :id"
    params_definition = [
        {"name": "id", "type": "int", "required": True, "default": None}
    ]
    connection_id = 1
    result_limit = 1000
    cache_seconds = 0
    auth_type = "none"
    is_enabled = True
    version = "v1"
```

---

## 四、单元测试

### 4.1 加密模块 — `test_crypto.py`

> 对应需求：1.2 连接保存（密码 AES-256 加密）

```python
# tests/unit/test_crypto.py
import pytest

pytestmark = pytest.mark.unit


class TestAESCrypto:
    """AES-256 加密/解密工具测试"""

    def test_encrypt_decrypt_roundtrip(self, encryption_key):
        """加密后解密应得到原文"""
        from app.utils.crypto import encrypt, decrypt

        plaintext = "my_secret_password"
        encrypted = encrypt(plaintext, encryption_key)
        decrypted = decrypt(encrypted, encryption_key)

        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_produces_different_ciphertext(self, encryption_key):
        """同一明文多次加密应产生不同密文（IV 随机）"""
        from app.utils.crypto import encrypt

        plaintext = "same_password"
        encrypted_1 = encrypt(plaintext, encryption_key)
        encrypted_2 = encrypt(plaintext, encryption_key)

        assert encrypted_1 != encrypted_2

    def test_decrypt_with_wrong_key_fails(self, encryption_key):
        """使用错误密钥解密应抛出异常"""
        from app.utils.crypto import encrypt, decrypt

        plaintext = "password"
        encrypted = encrypt(plaintext, encryption_key)
        wrong_key = "b" * 64

        with pytest.raises(Exception):
            decrypt(encrypted, wrong_key)

    def test_encrypt_empty_string(self, encryption_key):
        """空字符串也应能正常加密解密"""
        from app.utils.crypto import encrypt, decrypt

        encrypted = encrypt("", encryption_key)
        decrypted = decrypt(encrypted, encryption_key)
        assert decrypted == ""

    def test_encrypt_unicode_characters(self, encryption_key):
        """支持中文和特殊字符"""
        from app.utils.crypto import encrypt, decrypt

        plaintext = "密码测试🔐!@#$%^&*()"
        encrypted = encrypt(plaintext, encryption_key)
        decrypted = decrypt(encrypted, encryption_key)
        assert decrypted == plaintext

    def test_encrypt_long_password(self, encryption_key):
        """支持超长密码（256 字符以上）"""
        from app.utils.crypto import encrypt, decrypt

        plaintext = "A" * 500
        encrypted = encrypt(plaintext, encryption_key)
        decrypted = decrypt(encrypted, encryption_key)
        assert decrypted == plaintext

    def test_invalid_key_length_raises_error(self):
        """密钥长度不合法时应抛出 ValueError"""
        from app.utils.crypto import encrypt

        with pytest.raises(ValueError):
            encrypt("password", "short_key")
```

---

### 4.2 连接管理 Service — `test_connection_service.py`

> 对应需求：1.1 连接配置、1.2 连接生命周期、1.3 连接分组与标签

```python
# tests/unit/test_connection_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.unit


class TestConnectionService:
    """连接管理业务逻辑测试"""

    # --- 连接测试 ---

    @pytest.mark.asyncio
    async def test_test_connection_mysql_success(self, sample_connection_config):
        """MySQL 连接测试成功"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        with patch.object(service, "_create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_engine.return_value.dispose = MagicMock()

            result = await service.test_connection(sample_connection_config)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_test_connection_auth_failure(self, sample_connection_config):
        """连接测试 — 认证失败应返回明确错误"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        config = {**sample_connection_config, "password": "wrong_password"}

        with patch.object(service, "_create_engine") as mock_engine:
            mock_engine.return_value.connect.side_effect = Exception("Access denied for user 'root'")

            result = await service.test_connection(config)

            assert result["status"] == "error"
            assert "认证失败" in result["message"] or "Access denied" in result["message"]

    @pytest.mark.asyncio
    async def test_test_connection_timeout(self, sample_connection_config):
        """连接测试 — 超时应返回明确错误"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        config = {**sample_connection_config, "host": "192.0.2.1"}  # 不可达地址

        with patch.object(service, "_create_engine") as mock_engine:
            mock_engine.return_value.connect.side_effect = TimeoutError("Connection timed out")

            result = await service.test_connection(config)

            assert result["status"] == "error"
            assert "超时" in result["message"] or "timed out" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_connection_db_not_found(self, sample_connection_config):
        """连接测试 — 数据库不存在"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        config = {**sample_connection_config, "database_name": "nonexistent_db"}

        with patch.object(service, "_create_engine") as mock_engine:
            mock_engine.return_value.connect.side_effect = Exception("Unknown database 'nonexistent_db'")

            result = await service.test_connection(config)

            assert result["status"] == "error"
            assert "数据库" in result["message"] or "Unknown database" in result["message"]

    # --- 连接 CRUD ---

    @pytest.mark.asyncio
    async def test_create_connection_encrypts_password(self, db_session, sample_connection_config):
        """创建连接时密码应被加密存储"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        result = await service.create_connection(db_session, sample_connection_config)

        assert result["id"] is not None
        assert result["name"] == sample_connection_config["name"]
        # 密码不应以明文存储
        assert result.get("password") is None or result["password"] != sample_connection_config["password"]

    @pytest.mark.asyncio
    async def test_create_connection_validates_required_fields(self, db_session):
        """缺少必填字段时应返回校验错误"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        invalid_config = {"name": "", "host": ""}

        with pytest.raises(Exception):  # 应为 ValidationError
            await service.create_connection(db_session, invalid_config)

    @pytest.mark.asyncio
    async def test_get_connection_by_id(self, db_session, sample_connection_config):
        """通过 ID 获取连接应返回正确数据"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        created = await service.create_connection(db_session, sample_connection_config)
        fetched = await service.get_connection(db_session, created["id"])

        assert fetched["name"] == sample_connection_config["name"]
        assert fetched["db_type"] == sample_connection_config["db_type"]

    @pytest.mark.asyncio
    async def test_list_connections_with_group_filter(self, db_session):
        """按分组过滤连接列表"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        # 创建两个不同分组的连接
        config_dev = {"name": "dev-db", "db_type": "mysql", "host": "localhost",
                      "port": 3306, "username": "root", "password": "p",
                      "database_name": "dev", "group_name": "开发环境", "tags": []}
        config_prod = {"name": "prod-db", "db_type": "mysql", "host": "10.0.0.1",
                       "port": 3306, "username": "root", "password": "p",
                       "database_name": "prod", "group_name": "生产环境", "tags": []}

        await service.create_connection(db_session, config_dev)
        await service.create_connection(db_session, config_prod)

        dev_list = await service.list_connections(db_session, group_name="开发环境")
        assert len(dev_list) == 1
        assert dev_list[0]["name"] == "dev-db"

    @pytest.mark.asyncio
    async def test_delete_connection(self, db_session, sample_connection_config):
        """删除连接后应无法获取"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        created = await service.create_connection(db_session, sample_connection_config)
        await service.delete_connection(db_session, created["id"])

        result = await service.get_connection(db_session, created["id"])
        assert result is None

    @pytest.mark.asyncio
    async def test_update_connection_name(self, db_session, sample_connection_config):
        """更新连接名称"""
        from app.connections.service import ConnectionService

        service = ConnectionService()
        created = await service.create_connection(db_session, sample_connection_config)
        updated = await service.update_connection(db_session, created["id"], {"name": "新名称"})

        assert updated["name"] == "新名称"
```

---

### 4.3 连接池管理 — `test_connection_pool.py`

> 对应需求：1.2 连接池管理、连接健康检查

```python
# tests/unit/test_connection_pool.py
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


class TestConnectionPool:
    """连接池管理测试"""

    def test_pool_creation_default_size(self):
        """默认连接池大小为 5"""
        from app.connections.pool import ConnectionPoolManager

        manager = ConnectionPoolManager()
        pool = manager.get_or_create_pool(connection_id=1, db_config={"pool_size": 5})

        assert pool.size == 5

    def test_pool_reuse(self):
        """相同 connection_id 应复用已有连接池"""
        from app.connections.pool import ConnectionPoolManager

        manager = ConnectionPoolManager()
        config = {"pool_size": 3}
        pool_1 = manager.get_or_create_pool(connection_id=1, db_config=config)
        pool_2 = manager.get_or_create_pool(connection_id=1, db_config=config)

        assert pool_1 is pool_2

    def test_pool_different_connections(self):
        """不同 connection_id 应有独立连接池"""
        from app.connections.pool import ConnectionPoolManager

        manager = ConnectionPoolManager()
        config = {"pool_size": 3}
        pool_1 = manager.get_or_create_pool(connection_id=1, db_config=config)
        pool_2 = manager.get_or_create_pool(connection_id=2, db_config=config)

        assert pool_1 is not pool_2

    def test_pool_dispose(self):
        """销毁连接池后应重新创建"""
        from app.connections.pool import ConnectionPoolManager

        manager = ConnectionPoolManager()
        config = {"pool_size": 3}
        pool_1 = manager.get_or_create_pool(connection_id=1, db_config=config)
        manager.dispose_pool(connection_id=1)
        pool_2 = manager.get_or_create_pool(connection_id=1, db_config=config)

        assert pool_1 is not pool_2

    def test_pool_dispose_all(self):
        """销毁所有连接池"""
        from app.connections.pool import ConnectionPoolManager

        manager = ConnectionPoolManager()
        config = {"pool_size": 3}
        manager.get_or_create_pool(connection_id=1, db_config=config)
        manager.get_or_create_pool(connection_id=2, db_config=config)
        manager.dispose_all()

        assert manager.pool_count == 0

    @pytest.mark.asyncio
    async def test_health_check_detects_dead_connection(self):
        """健康检查应检测到失效连接"""
        from app.connections.pool import ConnectionPoolManager

        manager = ConnectionPoolManager()
        # 模拟一个已断开的连接
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection lost")

        is_alive = await manager.health_check(mock_engine)
        assert is_alive is False
```

---

### 4.4 结构浏览 Service — `test_explorer_service.py`

> 对应需求：2.1 数据库概览、2.2 表结构详情、2.3 视图/存储过程/函数/触发器

```python
# tests/unit/test_explorer_service.py
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


class TestExplorerService:
    """数据库结构浏览服务测试"""

    def test_get_table_list(self):
        """获取表列表"""
        from app.explorer.service import ExplorerService

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["users", "orders", "products"]

        service = ExplorerService(inspector=mock_inspector)
        tables = service.get_table_list(schema="public")

        assert len(tables) == 3
        assert "users" in tables
        mock_inspector.get_table_names.assert_called_once_with(schema="public")

    def test_get_columns(self, sample_table_metadata):
        """获取表字段信息"""
        from app.explorer.service import ExplorerService

        mock_inspector = MagicMock()
        mock_inspector.get_columns.return_value = [
            {"name": "id", "type": MagicMock(__str__=lambda s: "INTEGER"),
             "nullable": False, "default": None, "comment": "主键ID"},
            {"name": "username", "type": MagicMock(__str__=lambda s: "VARCHAR(50)"),
             "nullable": False, "default": None, "comment": "用户名"},
        ]
        mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}

        service = ExplorerService(inspector=mock_inspector)
        columns = service.get_columns(table_name="users", schema="public")

        assert len(columns) == 2
        assert columns[0]["name"] == "id"
        assert columns[0]["primary_key"] is True
        assert columns[1]["name"] == "username"

    def test_get_indexes(self):
        """获取索引信息"""
        from app.explorer.service import ExplorerService

        mock_inspector = MagicMock()
        mock_inspector.get_indexes.return_value = [
            {"name": "idx_email", "column_names": ["email"], "unique": False},
            {"name": "uk_username", "column_names": ["username"], "unique": True},
        ]

        service = ExplorerService(inspector=mock_inspector)
        indexes = service.get_indexes(table_name="users", schema="public")

        assert len(indexes) == 2
        assert any(idx["name"] == "uk_username" and idx["unique"] for idx in indexes)

    def test_get_foreign_keys(self):
        """获取外键信息"""
        from app.explorer.service import ExplorerService

        mock_inspector = MagicMock()
        mock_inspector.get_foreign_keys.return_value = [
            {"name": "fk_orders_user", "constrained_columns": ["user_id"],
             "referred_table": "users", "referred_columns": ["id"],
             "options": {"onupdate": "CASCADE", "ondelete": "RESTRICT"}},
        ]

        service = ExplorerService(inspector=mock_inspector)
        fks = service.get_foreign_keys(table_name="orders", schema="public")

        assert len(fks) == 1
        assert fks[0]["target_table"] == "users"
        assert fks[0]["on_delete"] == "RESTRICT"

    def test_get_view_list(self):
        """获取视图列表"""
        from app.explorer.service import ExplorerService

        mock_inspector = MagicMock()
        mock_inspector.get_view_names.return_value = ["v_active_users", "v_order_summary"]

        service = ExplorerService(inspector=mock_inspector)
        views = service.get_view_list(schema="public")

        assert len(views) == 2
        assert "v_active_users" in views

    def test_get_schema_list(self):
        """获取 Schema 列表"""
        from app.explorer.service import ExplorerService

        mock_inspector = MagicMock()
        mock_inspector.get_schema_names.return_value = ["public", "information_schema", "pg_catalog"]

        service = ExplorerService(inspector=mock_inspector)
        schemas = service.get_schema_list()

        assert "public" in schemas
        assert len(schemas) == 3
```

---

### 4.5 SQL 执行引擎 — `test_query_executor.py`

> 对应需求：4.2 查询执行与结果展示

```python
# tests/unit/test_query_executor.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

pytestmark = pytest.mark.unit


class TestQueryExecutor:
    """SQL 查询执行引擎测试"""

    @pytest.mark.asyncio
    async def test_execute_select_returns_results(self):
        """执行 SELECT 语句返回结果集"""
        from app.query.executor import QueryExecutor

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.rowcount = 2
        mock_connection.cursor.return_value = mock_cursor

        executor = QueryExecutor()
        result = await executor.execute(mock_connection, "SELECT id, name FROM users")

        assert result["row_count"] == 2
        assert len(result["rows"]) == 2
        assert result["columns"] == ["id", "name"]

    @pytest.mark.asyncio
    async def test_execute_with_pagination(self):
        """分页查询 — 只返回指定页的数据"""
        from app.query.executor import QueryExecutor

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        # 模拟第 2 页，每页 50 行
        mock_cursor.fetchall.return_value = [(i, f"user_{i}") for i in range(51, 101)]
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.rowcount = 200
        mock_connection.cursor.return_value = mock_cursor

        executor = QueryExecutor()
        result = await executor.execute(
            mock_connection,
            "SELECT id, name FROM users",
            page=2,
            page_size=50,
        )

        assert len(result["rows"]) == 50
        assert result["total"] == 200
        assert result["page"] == 2

    @pytest.mark.asyncio
    async def test_execute_returns_duration(self):
        """执行结果应包含耗时信息"""
        from app.query.executor import QueryExecutor

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        mock_cursor.rowcount = 0
        mock_connection.cursor.return_value = mock_cursor

        executor = QueryExecutor()
        result = await executor.execute(mock_connection, "SELECT 1")

        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], (int, float))
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execute_timeout_raises_error(self):
        """超时查询应抛出 TimeoutError"""
        from app.query.executor import QueryExecutor

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = TimeoutError("Query execution timed out")
        mock_connection.cursor.return_value = mock_cursor

        executor = QueryExecutor()

        with pytest.raises(TimeoutError):
            await executor.execute(mock_connection, "SELECT SLEEP(60)", timeout=5)

    @pytest.mark.asyncio
    async def test_execute_returns_columns_metadata(self):
        """返回结果应包含列名和类型信息"""
        from app.query.executor import QueryExecutor

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "Alice", "2024-01-01")]
        mock_cursor.description = [
            ("id", "INT"), ("name", "VARCHAR"), ("created_at", "DATETIME")
        ]
        mock_cursor.rowcount = 1
        mock_connection.cursor.return_value = mock_cursor

        executor = QueryExecutor()
        result = await executor.execute(mock_connection, "SELECT * FROM users LIMIT 1")

        assert result["columns"] == ["id", "name", "created_at"]
```

---

### 4.6 只读保护 — `test_query_guard.py`

> 对应需求：4.2 只读保护

```python
# tests/unit/test_query_guard.py
import pytest

pytestmark = pytest.mark.unit


class TestQueryGuard:
    """SQL 只读保护测试"""

    def test_select_is_allowed(self):
        """SELECT 语句应被允许"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("SELECT * FROM users") is True
        assert guard.is_allowed("  SELECT id FROM orders  ") is True

    def test_insert_is_blocked(self):
        """INSERT 语句在只读模式下应被阻止"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        result = guard.is_allowed("INSERT INTO users (name) VALUES ('test')")
        assert result is False

    def test_update_is_blocked(self):
        """UPDATE 语句在只读模式下应被阻止"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("UPDATE users SET name = 'test' WHERE id = 1") is False

    def test_delete_is_blocked(self):
        """DELETE 语句在只读模式下应被阻止"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("DELETE FROM users WHERE id = 1") is False

    def test_drop_is_blocked(self):
        """DROP 语句在只读模式下应被阻止"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("DROP TABLE users") is False

    def test_alter_is_blocked(self):
        """ALTER 语句在只读模式下应被阻止"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("ALTER TABLE users ADD COLUMN age INT") is False

    def test_truncate_is_blocked(self):
        """TRUNCATE 语句在只读模式下应被阻止"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("TRUNCATE TABLE users") is False

    def test_case_insensitive_detection(self):
        """SQL 关键字检测不区分大小写"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        assert guard.is_allowed("select * from users") is True
        assert guard.is_allowed("INSERT into users VALUES (1)") is False
        assert guard.is_allowed("DROP table USERS") is False

    def test_comment_bypass_prevention(self):
        """防止通过注释绕过检测"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=True)
        # 试图用注释隐藏写操作
        assert guard.is_allowed("/* DROP TABLE users */ SELECT 1") is True
        assert guard.is_allowed("-- comment\nDROP TABLE users") is False

    def test_non_read_only_mode_allows_writes(self):
        """非只读模式下写操作应被允许"""
        from app.query.guard import QueryGuard

        guard = QueryGuard(read_only=False)
        assert guard.is_allowed("INSERT INTO users (name) VALUES ('test')") is True
        assert guard.is_allowed("DELETE FROM users WHERE id = 1") is True
```

---

### 4.7 查询历史 — `test_query_history.py`

> 对应需求：4.3 查询历史

```python
# tests/unit/test_query_history.py
import pytest

pytestmark = pytest.mark.unit


class TestQueryHistory:
    """查询历史服务测试"""

    @pytest.mark.asyncio
    async def test_record_history(self, db_session):
        """执行查询后应自动记录历史"""
        from app.query.history import QueryHistoryService

        service = QueryHistoryService()
        await service.record(
            session=db_session,
            connection_id=1,
            sql_text="SELECT * FROM users",
            duration_ms=120,
            row_count=50,
            status="success",
        )

        history = await service.list_history(db_session, connection_id=1)
        assert len(history) == 1
        assert history[0]["sql_text"] == "SELECT * FROM users"
        assert history[0]["duration_ms"] == 120

    @pytest.mark.asyncio
    async def test_search_history_by_keyword(self, db_session):
        """按关键词搜索历史记录"""
        from app.query.history import QueryHistoryService

        service = QueryHistoryService()
        await service.record(db_session, 1, "SELECT * FROM users", 50, 10, "success")
        await service.record(db_session, 1, "SELECT * FROM orders", 80, 20, "success")
        await service.record(db_session, 1, "INSERT INTO logs VALUES (1)", 30, 1, "success")

        results = await service.search_history(db_session, keyword="SELECT")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_toggle_favorite(self, db_session):
        """收藏/取消收藏历史记录"""
        from app.query.history import QueryHistoryService

        service = QueryHistoryService()
        await service.record(db_session, 1, "SELECT 1", 10, 1, "success")
        history = await service.list_history(db_session, connection_id=1)
        history_id = history[0]["id"]

        # 收藏
        await service.toggle_favorite(db_session, history_id, is_favorite=True)
        updated = await service.get_history(db_session, history_id)
        assert updated["is_favorite"] is True

        # 取消收藏
        await service.toggle_favorite(db_session, history_id, is_favorite=False)
        updated = await service.get_history(db_session, history_id)
        assert updated["is_favorite"] is False

    @pytest.mark.asyncio
    async def test_record_error_history(self, db_session):
        """执行失败也应记录"""
        from app.query.history import QueryHistoryService

        service = QueryHistoryService()
        await service.record(
            session=db_session,
            connection_id=1,
            sql_text="SELECT * FROM nonexistent_table",
            duration_ms=15,
            row_count=0,
            status="error",
            error_message="Table 'nonexistent_table' doesn't exist",
        )

        history = await service.list_history(db_session, connection_id=1)
        assert len(history) == 1
        assert history[0]["status"] == "error"
        assert "nonexistent_table" in history[0]["error_message"]
```

---

### 4.8 文档生成 — `test_doc_generator.py`

> 对应需求：3.1 数据库文档生成

```python
# tests/unit/test_doc_generator.py
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit


class TestDocGenerator:
    """数据库文档生成测试"""

    def test_generate_markdown_contains_table_info(self, sample_table_metadata, tmp_path):
        """生成的 Markdown 文档应包含表信息"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        content = generator.generate_markdown(
            tables=[sample_table_metadata],
            db_name="test_db",
            db_type="mysql",
        )

        assert "# test_db 数据库设计文档" in content
        assert "## users" in content
        assert "id" in content
        assert "username" in content
        assert "VARCHAR(50)" in content
        assert "主键ID" in content

    def test_generate_markdown_contains_indexes(self, sample_table_metadata):
        """Markdown 文档应包含索引信息"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        content = generator.generate_markdown(
            tables=[sample_table_metadata], db_name="test_db", db_type="mysql"
        )

        assert "uk_username" in content
        assert "UNIQUE" in content
        assert "idx_email" in content

    def test_generate_markdown_contains_foreign_keys(self, sample_table_metadata, sample_table_with_fk):
        """Markdown 文档应包含外键信息"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        content = generator.generate_markdown(
            tables=[sample_table_metadata, sample_table_with_fk],
            db_name="test_db",
            db_type="mysql",
        )

        assert "fk_orders_user" in content
        assert "users" in content
        assert "CASCADE" in content

    def test_generate_markdown_multiple_tables(self, sample_table_metadata, sample_table_with_fk):
        """多表文档 — 每张表应有独立章节"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        content = generator.generate_markdown(
            tables=[sample_table_metadata, sample_table_with_fk],
            db_name="test_db",
            db_type="mysql",
        )

        assert content.count("## ") >= 2  # 至少两个表章节

    def test_generate_docx_creates_file(self, sample_table_metadata, tmp_path):
        """生成 Word 文档应创建 .docx 文件"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        output_path = tmp_path / "test_doc.docx"
        generator.generate_docx(
            tables=[sample_table_metadata],
            db_name="test_db",
            db_type="mysql",
            output_path=str(output_path),
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_pdf_creates_file(self, sample_table_metadata, tmp_path):
        """生成 PDF 文档应创建 .pdf 文件"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        output_path = tmp_path / "test_doc.pdf"
        generator.generate_pdf(
            tables=[sample_table_metadata],
            db_name="test_db",
            db_type="mysql",
            output_path=str(output_path),
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_markdown_with_empty_tables(self):
        """空表列表应生成仅含概要的文档"""
        from app.generator.doc_generator import DocGenerator

        generator = DocGenerator()
        content = generator.generate_markdown(tables=[], db_name="empty_db", db_type="mysql")

        assert "# empty_db" in content
        assert "表数量" in content or "0" in content
```

---

### 4.9 代码生成 — `test_code_generator.py`

> 对应需求：3.3 代码生成

```python
# tests/unit/test_code_generator.py
import pytest

pytestmark = pytest.mark.unit


class TestCodeGenerator:
    """代码生成器测试"""

    def test_generate_sqlalchemy_model(self, sample_table_metadata):
        """生成 SQLAlchemy Model"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(
            table=sample_table_metadata,
            target="sqlalchemy",
        )

        assert "class Users(Base):" in code
        assert "__tablename__" in code
        assert "Column(Integer" in code or "Column(INTEGER" in code
        assert "primary_key=True" in code
        assert "username" in code

    def test_generate_django_model(self, sample_table_metadata):
        """生成 Django Model"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(table=sample_table_metadata, target="django")

        assert "class Users(models.Model):" in code
        assert "models.IntegerField" in code or "models.AutoField" in code
        assert "models.CharField" in code
        assert "max_length" in code

    def test_generate_pydantic_schema(self, sample_table_metadata):
        """生成 Pydantic Schema"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(table=sample_table_metadata, target="pydantic")

        assert "class Users(BaseModel):" in code or "class UsersSchema(BaseModel):" in code
        assert "int" in code
        assert "str" in code

    def test_generate_typescript_interface(self, sample_table_metadata):
        """生成 TypeScript Interface"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(table=sample_table_metadata, target="typescript")

        assert "interface Users" in code or "interface User" in code
        assert "number" in code or "string" in code

    def test_generate_go_struct(self, sample_table_metadata):
        """生成 Go Struct"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(table=sample_table_metadata, target="go")

        assert "type Users struct" in code or "type User struct" in code
        assert "gorm:" in code  # 应包含 GORM tag

    def test_generate_java_entity(self, sample_table_metadata):
        """生成 Java Entity"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(table=sample_table_metadata, target="java")

        assert "class Users" in code or "class User" in code
        assert "@Id" in code or "@Column" in code

    def test_naming_style_camel_case(self, sample_table_metadata):
        """命名风格转换 — snake_case → camelCase"""
        from app.generator.code_generator import CodeGenerator

        # 使用一个包含 snake_case 字段名的表
        table = {**sample_table_metadata, "table_name": "user_profiles"}
        generator = CodeGenerator()
        code = generator.generate(table=table, target="typescript", naming_style="camelCase")

        assert "userProfiles" in code or "UserProfiles" in code

    def test_naming_style_pascal_case(self, sample_table_metadata):
        """命名风格转换 — snake_case → PascalCase"""
        from app.generator.code_generator import CodeGenerator

        table = {**sample_table_metadata, "table_name": "user_profiles"}
        generator = CodeGenerator()
        code = generator.generate(table=table, target="typescript", naming_style="PascalCase")

        assert "UserProfiles" in code

    def test_include_comments(self, sample_table_metadata):
        """包含注释映射"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        code = generator.generate(
            table=sample_table_metadata, target="sqlalchemy", include_comments=True
        )

        assert "主键ID" in code or "主键" in code

    def test_type_mapping_integer(self):
        """类型映射 — INTEGER"""
        from app.generator.code_generator import TypeMapper

        mapper = TypeMapper()
        assert mapper.map_type("INTEGER", "python") == "int"
        assert mapper.map_type("INTEGER", "typescript") == "number"
        assert mapper.map_type("INTEGER", "go") == "int64" or mapper.map_type("INTEGER", "go") == "int"
        assert mapper.map_type("INTEGER", "java") == "Integer" or mapper.map_type("INTEGER", "java") == "Long"

    def test_type_mapping_varchar(self):
        """类型映射 — VARCHAR"""
        from app.generator.code_generator import TypeMapper

        mapper = TypeMapper()
        assert mapper.map_type("VARCHAR(50)", "python") == "str"
        assert mapper.map_type("VARCHAR(50)", "typescript") == "string"
        assert mapper.map_type("VARCHAR(50)", "go") == "string"
        assert mapper.map_type("VARCHAR(50)", "java") == "String"

    def test_type_mapping_datetime(self):
        """类型映射 — DATETIME"""
        from app.generator.code_generator import TypeMapper

        mapper = TypeMapper()
        assert mapper.map_type("DATETIME", "python") == "datetime"
        assert mapper.map_type("DATETIME", "typescript") == "Date" or mapper.map_type("DATETIME", "typescript") == "string"
        assert mapper.map_type("DATETIME", "go") == "time.Time"

    def test_type_mapping_decimal(self):
        """类型映射 — DECIMAL"""
        from app.generator.code_generator import TypeMapper

        mapper = TypeMapper()
        assert mapper.map_type("DECIMAL(10,2)", "python") in ("Decimal", "float")
        assert mapper.map_type("DECIMAL(10,2)", "java") in ("BigDecimal", "Double")

    def test_unsupported_target_raises_error(self, sample_table_metadata):
        """不支持的目标语言应报错"""
        from app.generator.code_generator import CodeGenerator

        generator = CodeGenerator()
        with pytest.raises(ValueError, match="不支持"):
            generator.generate(table=sample_table_metadata, target="rust")
```

---

### 4.10 DDL 生成与跨库转换 — `test_ddl_generator.py` / `test_ddl_converter.py`

> 对应需求：3.2 DDL 生成、DDL 跨库转换

```python
# tests/unit/test_ddl_generator.py
import pytest

pytestmark = pytest.mark.unit


class TestDDLGenerator:
    """DDL 生成测试"""

    def test_generate_create_table(self, sample_table_metadata):
        """生成 CREATE TABLE 语句"""
        from app.generator.ddl_generator import DDLGenerator

        generator = DDLGenerator()
        ddl = generator.generate_create_table(sample_table_metadata)

        assert "CREATE TABLE" in ddl
        assert "users" in ddl
        assert "id" in ddl
        assert "INTEGER" in ddl
        assert "PRIMARY KEY" in ddl
        assert "VARCHAR(50)" in ddl

    def test_generate_create_table_with_indexes(self, sample_table_metadata):
        """包含索引的 DDL"""
        from app.generator.ddl_generator import DDLGenerator

        generator = DDLGenerator()
        ddl = generator.generate_create_table(sample_table_metadata, include_indexes=True)

        assert "CREATE UNIQUE INDEX" in ddl or "UNIQUE" in ddl
        assert "idx_email" in ddl

    def test_generate_create_table_without_indexes(self, sample_table_metadata):
        """不包含索引的 DDL"""
        from app.generator.ddl_generator import DDLGenerator

        generator = DDLGenerator()
        ddl = generator.generate_create_table(sample_table_metadata, include_indexes=False)

        assert "idx_email" not in ddl
        assert "uk_username" not in ddl

    def test_generate_create_table_with_foreign_keys(self, sample_table_with_fk):
        """包含外键的 DDL"""
        from app.generator.ddl_generator import DDLGenerator

        generator = DDLGenerator()
        ddl = generator.generate_create_table(sample_table_with_fk, include_foreign_keys=True)

        assert "FOREIGN KEY" in ddl or "REFERENCES" in ddl
        assert "users" in ddl

    def test_generate_schema_export(self, sample_table_metadata, sample_table_with_fk):
        """整个 Schema 导出为 .sql 文件"""
        from app.generator.ddl_generator import DDLGenerator

        generator = DDLGenerator()
        sql = generator.generate_schema(
            tables=[sample_table_metadata, sample_table_with_fk]
        )

        assert sql.count("CREATE TABLE") == 2
```

```python
# tests/unit/test_ddl_converter.py
import pytest

pytestmark = pytest.mark.unit


class TestDDLConverter:
    """DDL 跨库转换测试"""

    def test_mysql_to_postgresql_auto_increment(self):
        """MySQL AUTO_INCREMENT → PostgreSQL SERIAL"""
        from app.generator.ddl_converter import DDLConverter

        converter = DDLConverter()
        mysql_ddl = "CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50))"
        pg_ddl = converter.convert(mysql_ddl, source="mysql", target="postgresql")

        assert "SERIAL" in pg_ddl or "GENERATED" in pg_ddl
        assert "AUTO_INCREMENT" not in pg_ddl

    def test_mysql_to_postgresql_tinyint(self):
        """MySQL TINYINT → PostgreSQL SMALLINT"""
        from app.generator.ddl_converter import DDLConverter

        converter = DDLConverter()
        mysql_ddl = "CREATE TABLE config (id INT PRIMARY KEY, flag TINYINT)"
        pg_ddl = converter.convert(mysql_ddl, source="mysql", target="postgresql")

        assert "SMALLINT" in pg_ddl or "BOOLEAN" in pg_ddl
        assert "TINYINT" not in pg_ddl

    def test_mysql_to_oracle_varchar(self):
        """MySQL VARCHAR → Oracle VARCHAR2"""
        from app.generator.ddl_converter import DDLConverter

        converter = DDLConverter()
        mysql_ddl = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50))"
        oracle_ddl = converter.convert(mysql_ddl, source="mysql", target="oracle")

        assert "VARCHAR2" in oracle_ddl

    def test_mysql_to_postgresql_datetime(self):
        """MySQL DATETIME → PostgreSQL TIMESTAMP"""
        from app.generator.ddl_converter import DDLConverter

        converter = DDLConverter()
        mysql_ddl = "CREATE TABLE logs (id INT PRIMARY KEY, created_at DATETIME)"
        pg_ddl = converter.convert(mysql_ddl, source="mysql", target="postgresql")

        assert "TIMESTAMP" in pg_ddl

    def test_postgresql_to_mysql_serial(self):
        """PostgreSQL SERIAL → MySQL AUTO_INCREMENT"""
        from app.generator.ddl_converter import DDLConverter

        converter = DDLConverter()
        pg_ddl = "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(50))"
        mysql_ddl = converter.convert(pg_ddl, source="postgresql", target="mysql")

        assert "AUTO_INCREMENT" in mysql_ddl

    def test_unsupported_conversion_raises_error(self):
        """不支持的转换方向应报错"""
        from app.generator.ddl_converter import DDLConverter

        converter = DDLConverter()
        with pytest.raises(ValueError):
            converter.convert("CREATE TABLE t (id INT)", source="mysql", target="sqlite")
```

---

### 4.11 API 网关引擎 — `test_api_gateway.py`

> 对应需求：5.1 API 定义、5.2 参数绑定与安全

```python
# tests/unit/test_api_gateway.py
import pytest
from unittest.mock import MagicMock, AsyncMock

pytestmark = pytest.mark.unit


class TestApiGateway:
    """API 网关引擎测试"""

    def test_extract_params_from_sql(self):
        """从 SQL 模板中提取参数占位符"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        sql = "SELECT * FROM orders WHERE user_id = :user_id AND status = :status"
        params = gateway.extract_params(sql)

        assert "user_id" in params
        assert "status" in params
        assert len(params) == 2

    def test_extract_params_no_params(self):
        """无参数的 SQL 应返回空列表"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        sql = "SELECT * FROM users"
        params = gateway.extract_params(sql)

        assert len(params) == 0

    def test_validate_params_type_int(self, sample_api_definition):
        """参数类型校验 — int 类型"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        # 正确的 int
        result = gateway.validate_params(
            sample_api_definition["params_definition"],
            {"user_id": "123", "status": "paid"},
        )
        assert result["user_id"] == 123
        assert result["status"] == "paid"

    def test_validate_params_type_error(self, sample_api_definition):
        """参数类型不匹配应返回错误"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        with pytest.raises(ValueError, match="类型"):
            gateway.validate_params(
                sample_api_definition["params_definition"],
                {"user_id": "not_a_number", "status": "paid"},
            )

    def test_validate_params_required_missing(self, sample_api_definition):
        """必填参数缺失应返回错误"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        with pytest.raises(ValueError, match="必填"):
            gateway.validate_params(
                sample_api_definition["params_definition"],
                {"status": "paid"},  # 缺少 user_id
            )

    def test_apply_default_params(self, sample_api_definition):
        """可选参数未传时应使用默认值"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        result = gateway.validate_params(
            sample_api_definition["params_definition"],
            {"user_id": "123"},  # status 未传，应使用默认值 'paid'
        )
        assert result["status"] == "paid"

    def test_only_select_allowed(self):
        """API 网关只允许 SELECT 语句"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        assert gateway.is_safe_sql("SELECT * FROM users WHERE id = :id") is True
        assert gateway.is_safe_sql("DROP TABLE users") is False
        assert gateway.is_safe_sql("INSERT INTO users VALUES (:name)") is False
        assert gateway.is_safe_sql("DELETE FROM users WHERE id = :id") is False
        assert gateway.is_safe_sql("UPDATE users SET name = :name") is False

    @pytest.mark.asyncio
    async def test_execute_api_returns_results(self, sample_api_definition):
        """执行 API 应返回查询结果"""
        from app.api_gateway.gateway import ApiGateway

        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {
            "columns": ["id", "user_id", "amount", "status"],
            "rows": [(1, 123, 99.99, "paid")],
            "row_count": 1,
        }

        gateway = ApiGateway(executor=mock_executor)
        result = await gateway.execute_api(
            sql_template=sample_api_definition["sql_template"],
            params={"user_id": 123, "status": "paid"},
            connection=MagicMock(),
        )

        assert result["row_count"] == 1
        mock_executor.execute.assert_called_once()
```

---

### 4.12 API 认证 — `test_api_auth.py`

> 对应需求：5.3 API 认证与限流

```python
# tests/unit/test_api_auth.py
import pytest

pytestmark = pytest.mark.unit


class TestApiAuth:
    """API 认证模块测试"""

    def test_generate_token(self):
        """生成 Token 应为非空字符串"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        token = manager.generate_token()

        assert isinstance(token, str)
        assert len(token) >= 32

    def test_verify_valid_token(self):
        """有效 Token 应验证通过"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        token = manager.generate_token()
        api_id = 1

        # 注册 Token
        manager.register_token(api_id=api_id, token=token)
        # 验证
        result = manager.verify_token(token=token, api_id=api_id)
        assert result is True

    def test_verify_invalid_token(self):
        """无效 Token 应验证失败"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        result = manager.verify_token(token="invalid_token", api_id=1)
        assert result is False

    def test_verify_token_wrong_api(self):
        """Token 和 API 不匹配应验证失败"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        token = manager.generate_token()
        manager.register_token(api_id=1, token=token)

        # 用 api_id=2 验证 api_id=1 的 Token
        result = manager.verify_token(token=token, api_id=2)
        assert result is False

    def test_no_auth_mode_allows_access(self):
        """无认证模式下应直接允许访问"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        result = manager.verify_token(token=None, api_id=1, auth_type="none")
        assert result is True
```

---

### 4.13 限流 — `test_rate_limiter.py`

> 对应需求：5.3 限流

```python
# tests/unit/test_rate_limiter.py
import pytest
import time

pytestmark = pytest.mark.unit


class TestRateLimiter:
    """API 限流测试"""

    def test_within_limit_allows_request(self):
        """限流范围内的请求应被允许"""
        from app.api_gateway.rate_limiter import RateLimiter

        limiter = RateLimiter(rate=10, period=60)  # 10 次/分钟
        for i in range(10):
            assert limiter.is_allowed(key="api_1") is True

    def test_exceed_limit_blocks_request(self):
        """超过限流的请求应被阻止"""
        from app.api_gateway.rate_limiter import RateLimiter

        limiter = RateLimiter(rate=5, period=60)  # 5 次/分钟
        for i in range(5):
            limiter.is_allowed(key="api_1")

        assert limiter.is_allowed(key="api_1") is False

    def test_different_keys_independent(self):
        """不同 API 的限流应独立计算"""
        from app.api_gateway.rate_limiter import RateLimiter

        limiter = RateLimiter(rate=2, period=60)
        limiter.is_allowed(key="api_1")
        limiter.is_allowed(key="api_1")

        assert limiter.is_allowed(key="api_1") is False
        assert limiter.is_allowed(key="api_2") is True  # api_2 独立

    def test_limit_resets_after_period(self):
        """限流周期结束后应重置"""
        from app.api_gateway.rate_limiter import RateLimiter

        limiter = RateLimiter(rate=1, period=1)  # 1 次/秒
        limiter.is_allowed(key="api_1")
        assert limiter.is_allowed(key="api_1") is False

        time.sleep(1.1)  # 等待周期重置

        assert limiter.is_allowed(key="api_1") is True
```

---

## 五、集成测试

### 5.1 连接管理 API — `test_connections_api.py`

> 对应需求：一、连接管理模块（API 层）

```python
# tests/integration/test_connections_api.py
import pytest

pytestmark = pytest.mark.integration


class TestConnectionsAPI:
    """连接管理 API 集成测试"""

    @pytest.mark.asyncio
    async def test_create_connection(self, client, sample_connection_config):
        """POST /api/connections — 创建连接"""
        response = await client.post("/api/connections", json=sample_connection_config)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_connection_config["name"]
        assert data["db_type"] == "mysql"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_connection_missing_fields(self, client):
        """POST /api/connections — 缺少必填字段应返回 422"""
        response = await client.post("/api/connections", json={"name": "incomplete"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_connections(self, client, sample_connection_config):
        """GET /api/connections — 获取连接列表"""
        # 先创建一个
        await client.post("/api/connections", json=sample_connection_config)
        response = await client.get("/api/connections")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_list_connections_filter_by_group(self, client):
        """GET /api/connections?group_name=xxx — 按分组过滤"""
        config_dev = {"name": "dev", "db_type": "mysql", "host": "localhost",
                      "port": 3306, "username": "root", "password": "p",
                      "database_name": "dev", "group_name": "开发", "tags": []}
        config_prod = {"name": "prod", "db_type": "mysql", "host": "10.0.0.1",
                       "port": 3306, "username": "root", "password": "p",
                       "database_name": "prod", "group_name": "生产", "tags": []}
        await client.post("/api/connections", json=config_dev)
        await client.post("/api/connections", json=config_prod)

        response = await client.get("/api/connections", params={"group_name": "开发"})
        assert response.status_code == 200
        data = response.json()
        assert all(c["group_name"] == "开发" for c in data)

    @pytest.mark.asyncio
    async def test_get_connection_by_id(self, client, sample_connection_config):
        """GET /api/connections/{id} — 获取单个连接"""
        create_resp = await client.post("/api/connections", json=sample_connection_config)
        conn_id = create_resp.json()["id"]

        response = await client.get(f"/api/connections/{conn_id}")
        assert response.status_code == 200
        assert response.json()["name"] == sample_connection_config["name"]

    @pytest.mark.asyncio
    async def test_get_connection_not_found(self, client):
        """GET /api/connections/{id} — 不存在的连接应返回 404"""
        response = await client.get("/api/connections/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_connection(self, client, sample_connection_config):
        """PUT /api/connections/{id} — 更新连接"""
        create_resp = await client.post("/api/connections", json=sample_connection_config)
        conn_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/connections/{conn_id}",
            json={"name": "更新后的名称"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "更新后的名称"

    @pytest.mark.asyncio
    async def test_delete_connection(self, client, sample_connection_config):
        """DELETE /api/connections/{id} — 删除连接"""
        create_resp = await client.post("/api/connections", json=sample_connection_config)
        conn_id = create_resp.json()["id"]

        response = await client.delete(f"/api/connections/{conn_id}")
        assert response.status_code == 204

        # 确认已删除
        get_resp = await client.get(f"/api/connections/{conn_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_password_not_exposed_in_response(self, client, sample_connection_config):
        """API 响应中不应包含明文密码"""
        response = await client.post("/api/connections", json=sample_connection_config)
        data = response.json()

        # 密码字段不应出现或应为脱敏值
        assert "password" not in data or data.get("password") in (None, "", "******")
```

---

### 5.2 结构浏览 API — `test_explorer_api.py`

> 对应需求：二、数据库结构浏览模块（API 层）

```python
# tests/integration/test_explorer_api.py
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.integration


class TestExplorerAPI:
    """结构浏览 API 集成测试"""

    @pytest.mark.asyncio
    async def test_get_schemas(self, client):
        """GET /api/explorer/{connection_id}/schemas — 获取 Schema 列表"""
        with patch("app.explorer.service.ExplorerService.get_schema_list") as mock:
            mock.return_value = ["public", "test_schema"]
            response = await client.get("/api/explorer/1/schemas")

            assert response.status_code == 200
            assert "public" in response.json()

    @pytest.mark.asyncio
    async def test_get_tables(self, client):
        """GET /api/explorer/{connection_id}/tables — 获取表列表"""
        with patch("app.explorer.service.ExplorerService.get_table_list") as mock:
            mock.return_value = ["users", "orders", "products"]
            response = await client.get("/api/explorer/1/tables", params={"schema": "public"})

            assert response.status_code == 200
            tables = response.json()
            assert len(tables) == 3

    @pytest.mark.asyncio
    async def test_get_table_columns(self, client):
        """GET /api/explorer/{connection_id}/tables/{table}/columns"""
        with patch("app.explorer.service.ExplorerService.get_columns") as mock:
            mock.return_value = [
                {"name": "id", "type": "INTEGER", "nullable": False,
                 "primary_key": True, "comment": "主键"},
                {"name": "name", "type": "VARCHAR(50)", "nullable": False,
                 "primary_key": False, "comment": "名称"},
            ]
            response = await client.get("/api/explorer/1/tables/users/columns")

            assert response.status_code == 200
            columns = response.json()
            assert len(columns) == 2
            assert columns[0]["name"] == "id"
            assert columns[0]["primary_key"] is True

    @pytest.mark.asyncio
    async def test_get_table_indexes(self, client):
        """GET /api/explorer/{connection_id}/tables/{table}/indexes"""
        with patch("app.explorer.service.ExplorerService.get_indexes") as mock:
            mock.return_value = [
                {"name": "PRIMARY", "type": "PRIMARY", "columns": ["id"], "unique": True},
                {"name": "idx_name", "type": "INDEX", "columns": ["name"], "unique": False},
            ]
            response = await client.get("/api/explorer/1/tables/users/indexes")

            assert response.status_code == 200
            indexes = response.json()
            assert len(indexes) == 2

    @pytest.mark.asyncio
    async def test_get_table_foreign_keys(self, client):
        """GET /api/explorer/{connection_id}/tables/{table}/foreign-keys"""
        with patch("app.explorer.service.ExplorerService.get_foreign_keys") as mock:
            mock.return_value = [
                {"name": "fk_user", "source_column": "user_id",
                 "target_table": "users", "target_column": "id",
                 "on_update": "CASCADE", "on_delete": "RESTRICT"},
            ]
            response = await client.get("/api/explorer/1/tables/orders/foreign-keys")

            assert response.status_code == 200
            fks = response.json()
            assert len(fks) == 1
            assert fks[0]["target_table"] == "users"

    @pytest.mark.asyncio
    async def test_get_table_data_preview(self, client):
        """GET /api/explorer/{connection_id}/tables/{table}/data — 数据预览"""
        with patch("app.query.executor.QueryExecutor.execute") as mock:
            mock.return_value = {
                "columns": ["id", "name"],
                "rows": [[1, "Alice"], [2, "Bob"]],
                "row_count": 2,
                "total": 100,
                "duration_ms": 5,
            }
            response = await client.get(
                "/api/explorer/1/tables/users/data",
                params={"page": 1, "page_size": 100},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["rows"]) == 2

    @pytest.mark.asyncio
    async def test_get_database_stats(self, client):
        """GET /api/explorer/{connection_id}/stats — 数据库统计"""
        with patch("app.explorer.service.ExplorerService.get_database_stats") as mock:
            mock.return_value = {
                "table_count": 15,
                "total_rows": 50000,
                "data_size": 1048576,
                "index_size": 262144,
            }
            response = await client.get("/api/explorer/1/stats")

            assert response.status_code == 200
            stats = response.json()
            assert stats["table_count"] == 15
```

---

### 5.3 SQL 查询 API — `test_query_api.py`

> 对应需求：四、SQL 查询控制台模块（API 层）

```python
# tests/integration/test_query_api.py
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.integration


class TestQueryAPI:
    """SQL 查询 API 集成测试"""

    @pytest.mark.asyncio
    async def test_execute_select(self, client):
        """POST /api/query/execute — 执行 SELECT 查询"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id", "name", "email"],
                "rows": [[1, "Alice", "alice@example.com"]],
                "row_count": 1,
                "duration_ms": 15,
            }
            response = await client.post("/api/query/execute", json={
                "connection_id": 1,
                "sql": "SELECT id, name, email FROM users WHERE id = 1",
                "page": 1,
                "page_size": 50,
            })

            assert response.status_code == 200
            data = response.json()
            assert data["row_count"] == 1
            assert "duration_ms" in data

    @pytest.mark.asyncio
    async def test_execute_empty_sql_returns_error(self, client):
        """POST /api/query/execute — 空 SQL 应返回 400"""
        response = await client.post("/api/query/execute", json={
            "connection_id": 1,
            "sql": "",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_invalid_connection_returns_404(self, client):
        """POST /api/query/execute — 无效连接 ID 应返回 404"""
        response = await client.post("/api/query/execute", json={
            "connection_id": 99999,
            "sql": "SELECT 1",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_execute_read_only_blocks_insert(self, client):
        """POST /api/query/execute — 只读模式下 INSERT 应被阻止"""
        response = await client.post("/api/query/execute", json={
            "connection_id": 1,
            "sql": "INSERT INTO users (name) VALUES ('test')",
            "read_only": True,
        })
        assert response.status_code == 403
        assert "只读" in response.json().get("message", "")

    @pytest.mark.asyncio
    async def test_execute_with_pagination(self, client):
        """POST /api/query/execute — 分页参数"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id"],
                "rows": [[i] for i in range(51, 101)],
                "row_count": 50,
                "total": 200,
                "page": 2,
                "duration_ms": 25,
            }
            response = await client.post("/api/query/execute", json={
                "connection_id": 1,
                "sql": "SELECT id FROM users",
                "page": 2,
                "page_size": 50,
            })

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["total"] == 200

    # --- 导出测试 ---

    @pytest.mark.asyncio
    async def test_export_csv(self, client):
        """POST /api/query/export — 导出 CSV"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id", "name"],
                "rows": [[1, "Alice"], [2, "Bob"]],
                "row_count": 2,
                "duration_ms": 10,
            }
            response = await client.post("/api/query/export", json={
                "connection_id": 1,
                "sql": "SELECT id, name FROM users",
                "format": "csv",
            })

            assert response.status_code == 200
            assert "text/csv" in response.headers.get("content-type", "")
            content = response.text
            assert "id,name" in content
            assert "1,Alice" in content

    @pytest.mark.asyncio
    async def test_export_excel(self, client):
        """POST /api/query/export — 导出 Excel"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id", "name"],
                "rows": [[1, "Alice"], [2, "Bob"]],
                "row_count": 2,
                "duration_ms": 10,
            }
            response = await client.post("/api/query/export", json={
                "connection_id": 1,
                "sql": "SELECT id, name FROM users",
                "format": "xlsx",
            })

            assert response.status_code == 200
            assert "spreadsheet" in response.headers.get("content-type", "") or \
                   "octet-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_export_json(self, client):
        """POST /api/query/export — 导出 JSON"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id", "name"],
                "rows": [[1, "Alice"]],
                "row_count": 1,
                "duration_ms": 5,
            }
            response = await client.post("/api/query/export", json={
                "connection_id": 1,
                "sql": "SELECT id, name FROM users",
                "format": "json",
            })

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert data[0]["id"] == 1

    # --- 查询历史 ---

    @pytest.mark.asyncio
    async def test_query_history_auto_recorded(self, client):
        """执行查询后应自动记录历史"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["1"],
                "rows": [[1]],
                "row_count": 1,
                "duration_ms": 5,
            }
            await client.post("/api/query/execute", json={
                "connection_id": 1,
                "sql": "SELECT 1",
            })

            history_resp = await client.get("/api/query/history", params={"connection_id": 1})
            assert history_resp.status_code == 200
            history = history_resp.json()
            assert len(history) >= 1
            assert "SELECT 1" in history[0]["sql_text"]

    @pytest.mark.asyncio
    async def test_query_history_search(self, client):
        """GET /api/query/history?keyword=xxx — 搜索历史"""
        with patch("app.query.executor.QueryExecutor.execute", new_callable=AsyncMock) as mock:
            mock.return_value = {"columns": [], "rows": [], "row_count": 0, "duration_ms": 1}
            await client.post("/api/query/execute", json={"connection_id": 1, "sql": "SELECT * FROM users"})
            await client.post("/api/query/execute", json={"connection_id": 1, "sql": "SELECT * FROM orders"})

            response = await client.get("/api/query/history", params={"keyword": "users"})
            assert response.status_code == 200
            results = response.json()
            assert all("users" in r["sql_text"].lower() for r in results)
```

---

### 5.4 文档/代码生成 API — `test_generator_api.py`

> 对应需求：三、文档与代码生成模块（API 层）

```python
# tests/integration/test_generator_api.py
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.integration


class TestGeneratorAPI:
    """文档/代码生成 API 集成测试"""

    @pytest.mark.asyncio
    async def test_generate_markdown_doc(self, client):
        """POST /api/generator/doc — 生成 Markdown 文档"""
        with patch("app.generator.doc_generator.DocGenerator.generate_markdown") as mock:
            mock.return_value = "# test_db 数据库设计文档\n\n## users\n..."
            response = await client.post("/api/generator/doc", json={
                "connection_id": 1,
                "tables": ["users", "orders"],
                "format": "markdown",
            })

            assert response.status_code == 200
            assert "数据库设计文档" in response.text or response.headers.get("content-type") == "text/markdown"

    @pytest.mark.asyncio
    async def test_generate_docx_doc(self, client, tmp_path):
        """POST /api/generator/doc — 生成 Word 文档"""
        with patch("app.generator.doc_generator.DocGenerator.generate_docx") as mock:
            # 模拟生成 docx 文件
            mock.return_value = b"fake_docx_content"
            response = await client.post("/api/generator/doc", json={
                "connection_id": 1,
                "tables": ["users"],
                "format": "docx",
            })

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_code_sqlalchemy(self, client):
        """POST /api/generator/code — 生成 SQLAlchemy 代码"""
        with patch("app.generator.code_generator.CodeGenerator.generate") as mock:
            mock.return_value = "class Users(Base):\n    __tablename__ = 'users'\n..."
            response = await client.post("/api/generator/code", json={
                "connection_id": 1,
                "tables": ["users"],
                "target": "sqlalchemy",
                "naming_style": "snake_case",
                "include_comments": True,
            })

            assert response.status_code == 200
            assert "Users" in response.text

    @pytest.mark.asyncio
    async def test_generate_code_typescript(self, client):
        """POST /api/generator/code — 生成 TypeScript Interface"""
        with patch("app.generator.code_generator.CodeGenerator.generate") as mock:
            mock.return_value = "interface Users {\n  id: number;\n  name: string;\n}"
            response = await client.post("/api/generator/code", json={
                "connection_id": 1,
                "tables": ["users"],
                "target": "typescript",
                "naming_style": "camelCase",
            })

            assert response.status_code == 200
            assert "interface" in response.text

    @pytest.mark.asyncio
    async def test_generate_code_invalid_target(self, client):
        """POST /api/generator/code — 不支持的目标应返回 400"""
        response = await client.post("/api/generator/code", json={
            "connection_id": 1,
            "tables": ["users"],
            "target": "rust",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_ddl(self, client):
        """POST /api/generator/ddl — 生成 DDL"""
        with patch("app.generator.ddl_generator.DDLGenerator.generate_schema") as mock:
            mock.return_value = "CREATE TABLE users (\n  id INT PRIMARY KEY\n);"
            response = await client.post("/api/generator/ddl", json={
                "connection_id": 1,
                "tables": ["users"],
                "include_indexes": True,
                "include_foreign_keys": True,
            })

            assert response.status_code == 200
            assert "CREATE TABLE" in response.text
```

---

### 5.5 SQL-to-API 管理接口 — `test_api_gateway_api.py`

> 对应需求：五、SQL 发布为 Web API 模块（管理接口）

```python
# tests/integration/test_api_gateway_api.py
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.integration


class TestApiGatewayAPI:
    """SQL-to-API 管理接口集成测试"""

    @pytest.mark.asyncio
    async def test_create_api(self, client, sample_api_definition):
        """POST /api/gateway/apis — 创建 API"""
        response = await client.post("/api/gateway/apis", json=sample_api_definition)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "get-user-orders"
        assert data["url_path"] == "/api/v1/user-orders"
        assert data["is_enabled"] is True
        assert "auth_token" in data  # 应自动生成 Token

    @pytest.mark.asyncio
    async def test_create_api_duplicate_path(self, client, sample_api_definition):
        """POST /api/gateway/apis — 重复 URL 路径应返回 409"""
        await client.post("/api/gateway/apis", json=sample_api_definition)
        response = await client.post("/api/gateway/apis", json=sample_api_definition)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_api_non_select_sql(self, client, sample_api_definition):
        """POST /api/gateway/apis — 非 SELECT SQL 应返回 400"""
        bad_def = {**sample_api_definition, "sql_template": "DELETE FROM users WHERE id = :id"}
        response = await client.post("/api/gateway/apis", json=bad_def)

        assert response.status_code == 400
        assert "SELECT" in response.json().get("message", "").upper() or \
               "只允许" in response.json().get("message", "")

    @pytest.mark.asyncio
    async def test_list_apis(self, client, sample_api_definition):
        """GET /api/gateway/apis — 获取 API 列表"""
        await client.post("/api/gateway/apis", json=sample_api_definition)
        response = await client.get("/api/gateway/apis")

        assert response.status_code == 200
        apis = response.json()
        assert len(apis) >= 1

    @pytest.mark.asyncio
    async def test_toggle_api_enabled(self, client, sample_api_definition):
        """PATCH /api/gateway/apis/{id} — 启用/禁用 API"""
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        api_id = create_resp.json()["id"]

        # 禁用
        response = await client.patch(f"/api/gateway/apis/{api_id}", json={"is_enabled": False})
        assert response.status_code == 200
        assert response.json()["is_enabled"] is False

        # 重新启用
        response = await client.patch(f"/api/gateway/apis/{api_id}", json={"is_enabled": True})
        assert response.status_code == 200
        assert response.json()["is_enabled"] is True

    @pytest.mark.asyncio
    async def test_delete_api(self, client, sample_api_definition):
        """DELETE /api/gateway/apis/{id} — 删除 API"""
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        api_id = create_resp.json()["id"]

        response = await client.delete(f"/api/gateway/apis/{api_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_extract_params_endpoint(self, client):
        """POST /api/gateway/extract-params — 从 SQL 中提取参数"""
        response = await client.post("/api/gateway/extract-params", json={
            "sql": "SELECT * FROM orders WHERE user_id = :user_id AND status = :status AND date > :start_date",
        })

        assert response.status_code == 200
        params = response.json()["params"]
        assert "user_id" in params
        assert "status" in params
        assert "start_date" in params
```

---

### 5.6 发布后的 API 调用 — `test_api_gateway_call.py`

> 对应需求：5.2 参数绑定、5.3 认证与限流

```python
# tests/integration/test_api_gateway_call.py
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.integration


class TestApiGatewayCall:
    """发布后的 API 调用集成测试"""

    @pytest.mark.asyncio
    async def test_call_api_with_valid_token(self, client, sample_api_definition):
        """调用 API — 携带有效 Token 应返回数据"""
        # 先创建 API
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        api_data = create_resp.json()
        token = api_data["auth_token"]

        # 调用发布的 API
        with patch("app.api_gateway.gateway.ApiGateway.execute_api", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "columns": ["id", "user_id", "amount", "status"],
                "rows": [[1, 123, 99.99, "paid"]],
                "row_count": 1,
            }
            response = await client.get(
                "/gateway/api/v1/user-orders",
                params={"user_id": "123", "token": token},
            )

            assert response.status_code == 200
            data = response.json()
            assert "data" in data or "rows" in data

    @pytest.mark.asyncio
    async def test_call_api_without_token(self, client, sample_api_definition):
        """调用 API — 无 Token 应返回 401"""
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        api_data = create_resp.json()

        response = await client.get(
            "/gateway/api/v1/user-orders",
            params={"user_id": "123"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_call_api_with_wrong_token(self, client, sample_api_definition):
        """调用 API — 错误 Token 应返回 401"""
        await client.post("/api/gateway/apis", json=sample_api_definition)

        response = await client.get(
            "/gateway/api/v1/user-orders",
            params={"user_id": "123", "token": "wrong_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_call_api_wrong_param_type(self, client, sample_api_definition):
        """调用 API — 参数类型错误应返回 400"""
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        token = create_resp.json()["auth_token"]

        response = await client.get(
            "/gateway/api/v1/user-orders",
            params={"user_id": "not_a_number", "token": token},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_call_disabled_api(self, client, sample_api_definition):
        """调用已禁用的 API 应返回 503"""
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        api_id = create_resp.json()["id"]
        token = create_resp.json()["auth_token"]

        # 禁用
        await client.patch(f"/api/gateway/apis/{api_id}", json={"is_enabled": False})

        response = await client.get(
            "/gateway/api/v1/user-orders",
            params={"user_id": "123", "token": token},
        )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_call_api_respects_result_limit(self, client, sample_api_definition):
        """调用 API — 返回行数应不超过 result_limit"""
        create_resp = await client.post("/api/gateway/apis", json=sample_api_definition)
        token = create_resp.json()["auth_token"]

        with patch("app.api_gateway.gateway.ApiGateway.execute_api", new_callable=AsyncMock) as mock:
            # 模拟返回 2000 行（超出 limit 1000）
            mock.return_value = {
                "columns": ["id"],
                "rows": [[i] for i in range(2000)],
                "row_count": 2000,
            }
            response = await client.get(
                "/gateway/api/v1/user-orders",
                params={"user_id": "123", "token": token},
            )

            assert response.status_code == 200
            data = response.json()
            rows = data.get("data", data.get("rows", []))
            assert len(rows) <= 1000
```

---

## 六、安全测试

### 6.1 SQL 注入防护 — `test_sql_injection.py`

> 对应需求：5.2 参数绑定与安全、7.1 安全性

```python
# tests/security/test_sql_injection.py
import pytest

pytestmark = pytest.mark.security


class TestSQLInjectionPrevention:
    """SQL 注入防护测试 — 确保参数化查询有效"""

    def test_parameterized_query_not_vulnerable(self):
        """参数化查询 — 恶意输入不应被安全处理"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        sql = "SELECT * FROM users WHERE name = :name"
        malicious_input = "'; DROP TABLE users; --"

        # validate_params 应正常处理（作为字符串值传入）
        result = gateway.validate_params(
            [{"name": "name", "type": "str", "required": True, "default": None}],
            {"name": malicious_input},
        )

        # 恶意输入应作为纯字符串值传递，不会被解释为 SQL
        assert result["name"] == malicious_input

    def test_sql_template_cannot_be_modified(self):
        """用户无法修改 SQL 模板 — 只允许发布时定义的 SQL"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        # 白名单机制 — 不存在 "额外注入 SQL" 的入口
        assert gateway.is_safe_sql("SELECT * FROM users WHERE id = :id") is True
        assert gateway.is_safe_sql("SELECT * FROM users; DROP TABLE users; --") is False

    def test_multiple_statements_blocked(self):
        """多语句执行应被阻止"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        assert gateway.is_safe_sql("SELECT 1; SELECT 2") is False
        assert gateway.is_safe_sql("SELECT 1; DROP TABLE users") is False

    def test_union_based_injection_via_params(self):
        """通过参数的 UNION 注入 — 应作为字符串值处理"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        sql = "SELECT * FROM users WHERE id = :id"
        union_payload = "1 UNION SELECT password FROM admin_users"

        # id 类型定义为 int，UNION 字符串应被类型校验拒绝
        with pytest.raises(ValueError):
            gateway.validate_params(
                [{"name": "id", "type": "int", "required": True, "default": None}],
                {"id": union_payload},
            )

    def test_comment_based_injection(self):
        """注释注入 — 参数化查询中注释符号只是普通字符"""
        from app.api_gateway.gateway import ApiGateway

        gateway = ApiGateway()
        result = gateway.validate_params(
            [{"name": "name", "type": "str", "required": True, "default": None}],
            {"name": "admin' --"},
        )
        assert result["name"] == "admin' --"  # 作为纯字符串
```

---

### 6.2 认证安全 — `test_auth_security.py`

```python
# tests/security/test_auth_security.py
import pytest

pytestmark = pytest.mark.security


class TestAuthSecurity:
    """认证安全测试"""

    def test_token_not_predictable(self):
        """Token 应不可预测（随机生成）"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        tokens = {manager.generate_token() for _ in range(100)}

        # 100 个 Token 应全部不同
        assert len(tokens) == 100

    def test_brute_force_token_infeasible(self):
        """Token 长度应足够长，防止暴力破解"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        token = manager.generate_token()

        # Token 至少 32 字符（128 bit 熵）
        assert len(token) >= 32

    def test_revoked_token_rejected(self):
        """撤销后的 Token 应被拒绝"""
        from app.api_gateway.auth import TokenManager

        manager = TokenManager()
        token = manager.generate_token()
        manager.register_token(api_id=1, token=token)

        # 撤销
        manager.revoke_token(api_id=1, token=token)

        assert manager.verify_token(token=token, api_id=1) is False
```

---

## 七、测试执行与 CI 集成

### 7.1 本地执行命令

```bash
# 运行所有测试
pytest

# 仅运行单元测试
pytest -m unit

# 仅运行集成测试
pytest -m integration

# 仅运行安全测试
pytest -m security

# 跳过耗时测试
pytest -m "not slow"

# 带覆盖率报告
pytest --cov=app --cov-report=html

# 运行单个测试文件
pytest tests/unit/test_crypto.py -v

# 运行匹配的测试
pytest -k "test_encrypt"
```

### 7.2 GitHub Actions CI 配置

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_password
          MYSQL_DATABASE: test_db
        ports:
          - 3306:3306
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=3

      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: --health-cmd="pg_isready" --health-interval=10s --health-timeout=5s --health-retries=3

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        working-directory: backend
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Lint check
        working-directory: backend
        run: |
          pip install ruff
          ruff check app/

      - name: Run unit tests
        working-directory: backend
        run: pytest -m unit --cov=app --cov-report=xml

      - name: Run integration tests
        working-directory: backend
        env:
          MYSQL_HOST: 127.0.0.1
          MYSQL_PORT: 3306
          MYSQL_USER: root
          MYSQL_PASSWORD: test_password
          POSTGRES_HOST: 127.0.0.1
          POSTGRES_PORT: 5432
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: test_password
          ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
        run: pytest -m integration --cov=app --cov-append --cov-report=xml

      - name: Run security tests
        working-directory: backend
        run: pytest -m security -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml
```

---

## 八、测试用例汇总

### 8.1 单元测试用例总览

| 编号 | 模块 | 测试用例 | 对应需求 |
|------|------|----------|----------|
| UT-01 | 加密模块 | 加密解密往返正确 | 1.2 |
| UT-02 | 加密模块 | 同一明文不同密文（IV 随机） | 1.2 |
| UT-03 | 加密模块 | 错误密钥解密失败 | 1.2 |
| UT-04 | 加密模块 | 空字符串加密 | 1.2 |
| UT-05 | 加密模块 | Unicode 字符支持 | 1.2 |
| UT-06 | 加密模块 | 超长密码支持 | 1.2 |
| UT-07 | 加密模块 | 非法密钥长度报错 | 1.2 |
| UT-08 | 连接服务 | MySQL 连接测试成功 | 1.2 |
| UT-09 | 连接服务 | 认证失败返回明确错误 | 1.2 |
| UT-10 | 连接服务 | 超时返回明确错误 | 1.2 |
| UT-11 | 连接服务 | 数据库不存在返回明确错误 | 1.2 |
| UT-12 | 连接服务 | 创建连接密码加密存储 | 1.2 |
| UT-13 | 连接服务 | 缺少必填字段校验错误 | 1.1 |
| UT-14 | 连接服务 | 按 ID 获取连接 | 1.1 |
| UT-15 | 连接服务 | 按分组过滤连接列表 | 1.3 |
| UT-16 | 连接服务 | 删除连接 | 1.1 |
| UT-17 | 连接服务 | 更新连接名称 | 1.1 |
| UT-18 | 连接池 | 默认池大小为 5 | 1.2 |
| UT-19 | 连接池 | 相同 ID 复用连接池 | 1.2 |
| UT-20 | 连接池 | 不同 ID 独立连接池 | 1.2 |
| UT-21 | 连接池 | 销毁后重新创建 | 1.2 |
| UT-22 | 连接池 | 销毁所有连接池 | 1.2 |
| UT-23 | 连接池 | 健康检查检测失效连接 | 1.2 |
| UT-24 | 结构浏览 | 获取表列表 | 2.1 |
| UT-25 | 结构浏览 | 获取字段信息 | 2.2 |
| UT-26 | 结构浏览 | 获取索引信息 | 2.2 |
| UT-27 | 结构浏览 | 获取外键信息 | 2.2 |
| UT-28 | 结构浏览 | 获取视图列表 | 2.3 |
| UT-29 | 结构浏览 | 获取 Schema 列表 | 2.1 |
| UT-30 | SQL 执行 | SELECT 返回结果集 | 4.2 |
| UT-31 | SQL 执行 | 分页查询 | 4.2 |
| UT-32 | SQL 执行 | 返回耗时信息 | 4.2 |
| UT-33 | SQL 执行 | 超时查询抛出异常 | 4.2 |
| UT-34 | SQL 执行 | 返回列名元数据 | 4.2 |
| UT-35 | 只读保护 | SELECT 允许执行 | 4.2 |
| UT-36 | 只读保护 | INSERT 被阻止 | 4.2 |
| UT-37 | 只读保护 | UPDATE 被阻止 | 4.2 |
| UT-38 | 只读保护 | DELETE 被阻止 | 4.2 |
| UT-39 | 只读保护 | DROP 被阻止 | 4.2 |
| UT-40 | 只读保护 | ALTER 被阻止 | 4.2 |
| UT-41 | 只读保护 | TRUNCATE 被阻止 | 4.2 |
| UT-42 | 只读保护 | 大小写不敏感检测 | 4.2 |
| UT-43 | 只读保护 | 防注释绕过 | 4.2 |
| UT-44 | 只读保护 | 非只读模式允许写操作 | 4.2 |
| UT-45 | 查询历史 | 自动记录历史 | 4.3 |
| UT-46 | 查询历史 | 按关键词搜索 | 4.3 |
| UT-47 | 查询历史 | 收藏/取消收藏 | 4.3 |
| UT-48 | 查询历史 | 记录执行失败 | 4.3 |
| UT-49 | 文档生成 | Markdown 包含表信息 | 3.1 |
| UT-50 | 文档生成 | Markdown 包含索引 | 3.1 |
| UT-51 | 文档生成 | Markdown 包含外键 | 3.1 |
| UT-52 | 文档生成 | 多表独立章节 | 3.1 |
| UT-53 | 文档生成 | Word 文件创建 | 3.1 |
| UT-54 | 文档生成 | PDF 文件创建 | 3.1 |
| UT-55 | 文档生成 | 空表列表处理 | 3.1 |
| UT-56 | 代码生成 | SQLAlchemy Model | 3.3 |
| UT-57 | 代码生成 | Django Model | 3.3 |
| UT-58 | 代码生成 | Pydantic Schema | 3.3 |
| UT-59 | 代码生成 | TypeScript Interface | 3.3 |
| UT-60 | 代码生成 | Go Struct | 3.3 |
| UT-61 | 代码生成 | Java Entity | 3.3 |
| UT-62 | 代码生成 | camelCase 命名 | 3.3 |
| UT-63 | 代码生成 | PascalCase 命名 | 3.3 |
| UT-64 | 代码生成 | 包含注释映射 | 3.3 |
| UT-65 | 代码生成 | INTEGER 类型映射 | 3.3 |
| UT-66 | 代码生成 | VARCHAR 类型映射 | 3.3 |
| UT-67 | 代码生成 | DATETIME 类型映射 | 3.3 |
| UT-68 | 代码生成 | DECIMAL 类型映射 | 3.3 |
| UT-69 | 代码生成 | 不支持目标报错 | 3.3 |
| UT-70 | DDL 生成 | CREATE TABLE 语句 | 3.2 |
| UT-71 | DDL 生成 | 含索引 DDL | 3.2 |
| UT-72 | DDL 生成 | 不含索引 DDL | 3.2 |
| UT-73 | DDL 生成 | 含外键 DDL | 3.2 |
| UT-74 | DDL 生成 | Schema 导出 | 3.2 |
| UT-75 | DDL 转换 | MySQL→PG AUTO_INCREMENT | 3.2 |
| UT-76 | DDL 转换 | MySQL→PG TINYINT | 3.2 |
| UT-77 | DDL 转换 | MySQL→Oracle VARCHAR | 3.2 |
| UT-78 | DDL 转换 | MySQL→PG DATETIME | 3.2 |
| UT-79 | DDL 转换 | PG→MySQL SERIAL | 3.2 |
| UT-80 | DDL 转换 | 不支持方向报错 | 3.2 |
| UT-81 | API 网关 | 提取 SQL 参数 | 5.1 |
| UT-82 | API 网关 | 无参数 SQL | 5.1 |
| UT-83 | API 网关 | int 参数校验 | 5.2 |
| UT-84 | API 网关 | 类型不匹配报错 | 5.2 |
| UT-85 | API 网关 | 必填参数缺失报错 | 5.2 |
| UT-86 | API 网关 | 默认值应用 | 5.2 |
| UT-87 | API 网关 | 仅允许 SELECT | 5.2 |
| UT-88 | API 网关 | 执行返回结果 | 5.1 |
| UT-89 | API 认证 | 生成 Token | 5.3 |
| UT-90 | API 认证 | 有效 Token 验证 | 5.3 |
| UT-91 | API 认证 | 无效 Token 验证 | 5.3 |
| UT-92 | API 认证 | Token 与 API 不匹配 | 5.3 |
| UT-93 | API 认证 | 无认证模式放行 | 5.3 |
| UT-94 | 限流 | 范围内允许 | 5.3 |
| UT-95 | 限流 | 超限阻止 | 5.3 |
| UT-96 | 限流 | 独立计数 | 5.3 |
| UT-97 | 限流 | 周期重置 | 5.3 |

### 8.2 集成测试用例总览

| 编号 | 模块 | 测试用例 | 对应需求 |
|------|------|----------|----------|
| IT-01 | 连接 API | 创建连接 | 1.1 |
| IT-02 | 连接 API | 缺少必填字段 422 | 1.1 |
| IT-03 | 连接 API | 获取连接列表 | 1.1 |
| IT-04 | 连接 API | 按分组过滤 | 1.3 |
| IT-05 | 连接 API | 按 ID 获取 | 1.1 |
| IT-06 | 连接 API | 不存在的连接 404 | 1.1 |
| IT-07 | 连接 API | 更新连接 | 1.1 |
| IT-08 | 连接 API | 删除连接 | 1.1 |
| IT-09 | 连接 API | 密码不暴露 | 7.1 |
| IT-10 | 浏览 API | 获取 Schema 列表 | 2.1 |
| IT-11 | 浏览 API | 获取表列表 | 2.1 |
| IT-12 | 浏览 API | 获取字段信息 | 2.2 |
| IT-13 | 浏览 API | 获取索引信息 | 2.2 |
| IT-14 | 浏览 API | 获取外键信息 | 2.2 |
| IT-15 | 浏览 API | 数据预览 | 2.2 |
| IT-16 | 浏览 API | 数据库统计 | 2.1 |
| IT-17 | 查询 API | 执行 SELECT | 4.2 |
| IT-18 | 查询 API | 空 SQL 返回 400 | 4.2 |
| IT-19 | 查询 API | 无效连接返回 404 | 4.2 |
| IT-20 | 查询 API | 只读模式阻止写操作 | 4.2 |
| IT-21 | 查询 API | 分页查询 | 4.2 |
| IT-22 | 查询 API | 导出 CSV | 4.4 |
| IT-23 | 查询 API | 导出 Excel | 4.4 |
| IT-24 | 查询 API | 导出 JSON | 4.4 |
| IT-25 | 查询 API | 自动记录历史 | 4.3 |
| IT-26 | 查询 API | 搜索历史 | 4.3 |
| IT-27 | 生成 API | 生成 Markdown 文档 | 3.1 |
| IT-28 | 生成 API | 生成 Word 文档 | 3.1 |
| IT-29 | 生成 API | 生成 SQLAlchemy | 3.3 |
| IT-30 | 生成 API | 生成 TypeScript | 3.3 |
| IT-31 | 生成 API | 不支持目标 400 | 3.3 |
| IT-32 | 生成 API | 生成 DDL | 3.2 |
| IT-33 | 网关 API | 创建 API | 5.1 |
| IT-34 | 网关 API | 重复路径 409 | 5.1 |
| IT-35 | 网关 API | 非 SELECT 400 | 5.2 |
| IT-36 | 网关 API | 获取 API 列表 | 5.1 |
| IT-37 | 网关 API | 启用/禁用切换 | 5.5 |
| IT-38 | 网关 API | 删除 API | 5.5 |
| IT-39 | 网关 API | 提取 SQL 参数 | 5.1 |
| IT-40 | 网关调用 | 有效 Token 调用 | 5.3 |
| IT-41 | 网关调用 | 无 Token 返回 401 | 5.3 |
| IT-42 | 网关调用 | 错误 Token 返回 401 | 5.3 |
| IT-43 | 网关调用 | 参数类型错误 400 | 5.2 |
| IT-44 | 网关调用 | 已禁用返回 503 | 5.5 |
| IT-45 | 网关调用 | 结果行数限制 | 5.1 |

### 8.3 安全测试用例总览

| 编号 | 模块 | 测试用例 | 对应需求 |
|------|------|----------|----------|
| ST-01 | SQL 注入 | 参数化查询防注入 | 5.2 / 7.1 |
| ST-02 | SQL 注入 | SQL 模板不可修改 | 5.2 |
| ST-03 | SQL 注入 | 多语句阻止 | 5.2 |
| ST-04 | SQL 注入 | UNION 注入通过类型校验阻止 | 5.2 |
| ST-05 | SQL 注入 | 注释注入作为纯字符串 | 5.2 |
| ST-06 | 认证安全 | Token 不可预测 | 5.3 |
| ST-07 | 认证安全 | Token 长度足够 | 5.3 |
| ST-08 | 认证安全 | 撤销 Token 被拒绝 | 5.3 |

---

## 九、测试执行结果

### 9.1 执行概要

| 项目 | 结果 |
|------|------|
| 执行日期 | 2026-07-15 |
| 测试框架 | pytest 8.x + pytest-asyncio |
| 总测试数 | 82 |
| 通过 | 82 |
| 失败 | 0 |
| 跳过 | 0 |
| 代码覆盖率 | 46%（行覆盖） |
| 执行耗时 | ~6.3 秒 |

### 9.2 测试分层统计

| 层级 | 测试数 | 通过 | 失败 |
|------|--------|------|------|
| 单元测试（unit） | 63 | 63 | 0 |
| 集成测试（integration） | 13 | 13 | 0 |
| 安全测试（security） | 6 | 6 | 0 |
| **合计** | **82** | **82** | **0** |

### 9.3 各模块覆盖明细

| 测试文件 | 测试类/函数 | 用例数 | 状态 |
|----------|------------|--------|------|
| `test_crypto.py` | TestCrypto | 7 | 全部通过 |
| `test_query_guard.py` | TestQueryGuard | 10 | 全部通过 |
| `test_code_generator.py` | TestCodeGenerator | 16 | 全部通过 |
| `test_ddl_generator.py` | TestDDLGenerator | 5 | 全部通过 |
| `test_type_mapping.py` | TestTypeMapping | 20 | 全部通过 |
| `test_api_gateway.py` | TestApiGateway | 5 | 全部通过 |
| `test_rate_limiter.py` | TestRateLimiter | 3 | 全部通过 |
| `test_connections_api.py`（集成） | TestConnectionsAPI | 8 | 全部通过 |
| `test_query_api.py`（集成） | TestQueryAPI | 5 | 全部通过 |
| `test_sql_injection.py`（安全） | TestSQLInjection | 6 | 全部通过 |

### 9.4 开发过程中的问题与修复记录

在测试过程中发现并修复了以下问题：

| # | 问题描述 | 影响范围 | 修复方案 |
|---|----------|----------|----------|
| 1 | 加密函数调用缺少 key 参数 | 连接管理 Service | 在 Service 中添加 `_key()` 辅助函数读取配置中的 `ENCRYPTION_KEY` |
| 2 | ORM 模型字段名不一致（`password` vs `password_encrypted`） | 连接管理 Service | 统一使用 `password_encrypted` 列名 |
| 3 | 测试文件中的导入路径与实际模块不匹配 | 7 个测试文件 | 重写测试文件，使用正确的类方法 API |
| 4 | `ErrorResponse` 模型 `code` 字段为必填但路由未传入 | API 响应格式 | 将 `code` 字段设为默认值 500 |
| 5 | FastAPI 路由尾斜杠导致 307 重定向 | 集成测试 | 测试客户端添加 `follow_redirects=True` |
| 6 | Service 方法仅 `flush()` 未 `commit()`，数据不可见 | 连接 CRUD 操作 | 在写操作后添加 `session.commit()` |
| 7 | 测试环境变量 `DBSTUDIO_ENCRYPTION_KEY` 未设置 | 加密相关测试 | 在 `conftest.py` 顶部设置环境变量 |

### 9.5 测试环境信息

| 项目 | 值 |
|------|-----|
| 操作系统 | Windows 10 (10.0.19045) |
| Python 版本 | 3.12.7 |
| 数据库 | SQLite (内存模式, aiosqlite) |
| 加密密钥 | 64 个 'a' 字符（测试专用） |
