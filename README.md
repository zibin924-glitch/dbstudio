# DBStudio

**DBStudio** 是一款基于 Web 的数据库开发与管理工具，提供统一界面来操作多种数据库。内置强大的 SQL 查询编辑器、数据库结构浏览器、代码生成能力，以及将 SQL 查询发布为 RESTful 接口的 API 网关。

---

## 功能特性

- **多数据库支持** — 在同一界面连接 MySQL、PostgreSQL、Oracle 11g 等多种数据库。
- **SQL 查询编辑器** — 基于 Monaco Editor，支持语法高亮、自动补全、结果分页展示。
- **结构浏览** — 查看表、字段、索引、外键等元数据信息，支持数据库方言适配。
- **代码生成** — 根据表结构自动生成 SQLAlchemy、Django、Pydantic、TypeScript、Go、Java 的 ORM 模型与接口定义。
- **DDL 生成** — 从表元数据生成 CREATE TABLE 语句及迁移脚本，支持跨库类型转换（MySQL ↔ PostgreSQL ↔ Oracle）。
- **API 网关** — 将参数化 SQL 查询一键发布为带认证和限流的 REST 接口。
- **只读模式** — 强制只读访问，防止对生产数据库的误写操作。
- **数据导出** — 查询结果支持导出为 CSV、Excel、JSON 格式。
- **安全存储** — 数据库密码使用 AES-256-CBC 加密后持久化存储。

---

## 开发状态

截至 2026-07-15，DBStudio 后端已开发完成，**82 个测试用例全部通过**。测试覆盖三个层级：

| 测试层级 | 文件数 | 说明 |
|----------|--------|------|
| 单元测试 | 8 | 核心逻辑：加密、SQL 守卫、连接池、代码生成、DDL 生成、类型映射、限流、API 网关 |
| 集成测试 | 2 | 完整请求周期的 API 端到端测试 |
| 安全测试 | 1 | SQL 注入防护、加密验证 |

当前 `app/` 包代码行覆盖率为 **46%**。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11、FastAPI、SQLAlchemy 2.0（async） |
| 前端 | Vue 3、Pinia、Element Plus、Monaco Editor |
| 加密 | AES-256（`cryptography` 库） |
| 测试 | pytest、pytest-asyncio、httpx |
| 部署 | Docker、Docker Compose、Nginx |

---

## Docker 快速启动

最快方式运行 DBStudio：

```bash
# 克隆仓库
git clone https://github.com/zibin924-glitch/dbstudio.git
cd dbstudio

# 构建并启动前后端服务
docker-compose up --build
```

容器启动后：

- **前端页面**：[http://localhost:80](http://localhost:80)
- **后端 API**：[http://localhost:8000](http://localhost:8000)
- **API 文档**：[http://localhost:8000/docs](http://localhost:8000/docs)

---

## 开发环境搭建

### 前置要求

- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-test.txt

# 设置环境变量
export DBSTUDIO_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export DBSTUDIO_DEBUG=true

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器运行在 [http://localhost:5173](http://localhost:5173)，并将 API 请求代理到后端。

### 运行测试

```bash
cd backend

# 运行全部测试
pytest

# 仅运行单元测试
pytest -m unit

# 仅运行集成测试
pytest -m integration

# 仅运行安全测试
pytest -m security

# 带覆盖率报告
pytest --cov=app --cov-report=term-missing
```

---

## 环境变量配置

所有环境变量使用 `DBSTUDIO_` 前缀：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DBSTUDIO_ENCRYPTION_KEY` | *(空)* | 64 位十六进制字符串，用于 AES-256 加密 |
| `DBSTUDIO_DEBUG` | `false` | 开启调试模式（详细日志） |
| `DBSTUDIO_DATABASE_URL` | `sqlite+aiosqlite:///./dbstudio.db` | 本地元数据存储的异步数据库连接串 |
| `DBSTUDIO_API_PREFIX` | `/api` | 所有 API 路由的 URL 前缀 |
| `DBSTUDIO_CORS_ORIGINS` | `["*"]` | 允许的 CORS 来源（JSON 数组） |
| `DBSTUDIO_QUERY_TIMEOUT` | `30` | 远程查询最大执行时间（秒） |
| `DBSTUDIO_DEFAULT_PAGE_SIZE` | `50` | 分页查询默认每页行数 |
| `DBSTUDIO_MAX_EXPORT_ROWS` | `100000` | CSV/Excel/JSON 导出最大行数 |
| `DBSTUDIO_LOG_LEVEL` | `INFO` | Python 日志级别（DEBUG、INFO、WARNING、ERROR） |

生成安全的加密密钥：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 项目结构

```
dbstudio/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py              # 应用配置（pydantic-settings）
│   │   ├── main.py                # FastAPI 应用入口
│   │   ├── connections/           # 数据库连接管理
│   │   │   ├── models.py          # Pydantic 数据模型
│   │   │   ├── router.py          # FastAPI 接口
│   │   │   ├── service.py         # 业务逻辑（CRUD + 加密）
│   │   │   └── pool.py            # 连接池管理器
│   │   ├── database/              # 本地元数据存储
│   │   │   ├── models.py          # SQLAlchemy ORM 模型（4 张表）
│   │   │   └── session.py         # 异步引擎与会话工厂
│   │   ├── explorer/              # 数据库结构浏览
│   │   │   ├── service.py         # 浏览服务（SQLAlchemy Inspector）
│   │   │   ├── router.py          # API 接口
│   │   │   └── dialects/          # 数据库方言适配器（MySQL、PostgreSQL、Oracle）
│   │   ├── generator/             # 代码与文档生成
│   │   │   ├── code_generator.py  # 代码生成器 + 类型映射（6 种目标）
│   │   │   ├── doc_generator.py   # Markdown/DOCX/PDF 文档生成
│   │   │   ├── ddl_generator.py   # CREATE TABLE DDL 生成
│   │   │   ├── ddl_converter.py   # 跨数据库 DDL 转换
│   │   │   ├── router.py          # API 接口
│   │   │   └── templates/         # Jinja2 模板
│   │   ├── query/                 # SQL 查询执行
│   │   │   ├── executor.py        # 查询执行器（含分页）
│   │   │   ├── guard.py           # 只读 SQL 守卫（sqlparse）
│   │   │   ├── history.py         # 查询历史服务
│   │   │   ├── export.py          # CSV/Excel/JSON 导出
│   │   │   └── router.py          # API 接口
│   │   ├── api_gateway/           # SQL 发布为 API
│   │   │   ├── gateway.py         # API 网关引擎
│   │   │   ├── auth.py            # Token 认证管理
│   │   │   ├── rate_limiter.py    # 滑动窗口限流器
│   │   │   ├── models.py          # Pydantic 数据模型
│   │   │   └── router.py          # 管理接口 + 动态网关接口
│   │   ├── routers/               # 路由转发
│   │   └── utils/                 # 公共工具
│   │       ├── crypto.py          # AES-256-CBC 加密/解密
│   │       └── responses.py       # 标准 API 响应信封
│   ├── tests/
│   │   ├── conftest.py            # 全局测试 Fixtures
│   │   ├── unit/                  # 单元测试（8 个文件）
│   │   ├── integration/           # 集成测试（2 个文件）
│   │   └── security/              # 安全测试（1 个文件）
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                   # Axios API 封装
│   │   ├── components/            # Vue 组件（7 个）
│   │   ├── router/                # Vue Router 路由配置（5 个路由）
│   │   ├── stores/                # Pinia 状态管理（connection、query）
│   │   ├── views/                 # 页面视图（5 个）
│   │   ├── main.js
│   │   └── App.vue
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── docs/
│   ├── 数据库开发工具需求规格说明书.md
│   ├── DBStudio项目整体计划.md
│   ├── DBStudio测试计划与用例文档.md
│   ├── DBStudio项目完成总结.md
│   └── DBStudio需求审查报告.md
└── README.md
```

---

## API 文档

后端启动后，可通过以下地址访问交互式 API 文档：

- **Swagger UI**：[http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**：[http://localhost:8000/redoc](http://localhost:8000/redoc)

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/connections/` | 获取所有连接列表 |
| POST | `/api/connections/` | 创建新连接 |
| GET | `/api/connections/{id}/` | 获取指定连接详情 |
| PUT | `/api/connections/{id}/` | 更新连接 |
| DELETE | `/api/connections/{id}/` | 删除连接 |
| POST | `/api/query/execute` | 执行 SQL 查询 |
| GET | `/api/explorer/{id}/tables` | 获取已连接数据库的表列表 |
| POST | `/api/generator/code` | 根据表元数据生成代码 |
| POST | `/api/generator/ddl` | 根据表元数据生成 DDL |
| GET | `/api/gateway/{id}` | 调用已发布的 API 接口 |
| GET | `/api/health` | 健康检查 |

---

## 项目文档

项目完整文档存放在 `docs/` 目录下：

| 文档 | 说明 |
|------|------|
| [数据库开发工具需求规格说明书](docs/数据库开发工具需求规格说明书.md) | 完整的功能需求定义，涵盖连接管理、结构浏览、SQL 查询、代码生成、API 网关五大模块 |
| [DBStudio 项目整体计划](docs/DBStudio项目整体计划.md) | 三阶段开发计划（MVP → 增强 → 高级），含 Sprint 分解、甘特图、风险管理、附录 C 开发完成状态 |
| [DBStudio 测试计划与用例文档](docs/DBStudio测试计划与用例文档.md) | 测试策略、环境搭建、150+ 测试用例定义，第九章包含实际执行结果（82 个测试全部通过） |
| [DBStudio 项目完成总结](docs/DBStudio项目完成总结.md) | 交付成果总览、测试结果、开发过程中的问题与修复记录、后续建议 |
| [DBStudio 需求审查报告](docs/DBStudio需求审查报告.md) | 对照需求规格逐项审查，85 项需求实现状态、4 个阻断级 Bug、15 条改善建议 |

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

```
MIT License

Copyright (c) 2024 DBStudio Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
