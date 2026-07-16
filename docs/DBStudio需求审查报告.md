# DBStudio 需求审查报告

审查日期：2026-07-16

---

## 一、审查概要

本报告对照《数据库开发工具需求规格说明书》逐项检查实际代码实现，覆盖连接管理、结构浏览、SQL 查询、文档/代码生成、API 网关五大模块以及安全性、性能、可用性、部署四类非功能性需求。

| 类别 | 已实现 | 部分实现 | 未实现 | 合计 |
|------|--------|----------|--------|------|
| 连接管理 | 6 | 2 | 0 | 8 |
| 结构浏览 | 0 | 3 | 2 | 5 |
| SQL 查询 | 8 | 4 | 5 | 17 |
| 文档/代码生成 | 17 | 3 | 2 | 22 |
| API 网关 | 5 | 8 | 5 | 18 |
| 非功能性需求 | 5 | 6 | 4 | 15 |
| **合计** | **41** | **26** | **18** | **85** |

总体实现率约 48%（完全实现），加上部分实现约 79%。

---

## 二、运行时缺陷（需立即修复）

以下问题会导致功能在运行时直接报错，属于阻断级 Bug。

### 缺陷 1：API 网关动态路由未挂载

**位置**：`backend/app/main.py` 第 75 行

**现象**：`main.py` 只挂载了管理路由 `api_gateway.router`（前缀 `/gateway/apis`），但处理外部 API 调用的 `dynamic_router`（前缀 `/gateway/{path}`）从未被 `include_router()` 注册。所有已发布的 API 端点均无法被外部调用。

**影响**：SQL 发布为 API 的核心功能完全不可用。

**修复建议**：在 `main.py` 中添加 `app.include_router(dynamic_router, prefix=settings.API_PREFIX)`。

---

### 缺陷 2：ApiDefinition ORM 字段名与路由引用不一致

**位置**：`backend/app/database/models.py` 第 185 行 vs `backend/app/api_gateway/router.py` 多处

**现象**：ORM 模型定义列为 `auth_token`，但路由代码中引用 `api.token`（第 64、106、116、181、184、227 行）。运行时将抛出 `AttributeError`。

**修复建议**：统一字段名为 `auth_token`，或路由代码改为 `api.auth_token`。

---

### 缺陷 3：ApiCallLog ORM 字段名与路由写入不一致

**位置**：`backend/app/database/models.py` 第 224-259 行 vs `backend/app/api_gateway/router.py` 第 345-365 行

**现象**：ORM 模型定义了 `request_params`、`response_status`、`called_at` 列，但路由代码使用了 `params`、`status`、`error_message`、`response_data` 等不存在的字段名。API 调用日志将无法正确记录。

**修复建议**：将路由代码中的字段名改为与 ORM 模型一致。

---

### 缺陷 4：QueryHistory 缺少 created_at 列

**位置**：`backend/app/database/models.py` 第 97-135 行 vs `backend/app/query/history.py` 第 68、191 行

**现象**：ORM 模型中 `QueryHistory` 没有定义 `created_at` 字段，但 `list_history()` 按 `created_at` 排序，`_to_dict()` 也访问 `entry.created_at`。运行时将抛出 `AttributeError`。

**修复建议**：在 `QueryHistory` 模型中添加 `created_at: Mapped[datetime] = mapped_column(default=func.now())`。

---

## 三、需求缺陷（未实现功能）

### 3.1 结构浏览模块

| 编号 | 缺失需求 | 需求来源 | 严重程度 |
|------|----------|----------|----------|
| E-1 | 存储过程、函数、触发器、序列未出现在导航树中 | 需求 2.1 | 中 |
| E-2 | 视图/存储过程/函数的详情展示（定义 SQL、创建时间、参数列表）未实现 | 需求 2.3 | 中 |
| E-3 | ER 关系图完全未实现（前端无可视化组件） | 需求 2.4 | 低（Phase 3） |

**改善建议**：后端 `dialects/mysql.py` 已实现 `get_stored_procedures()` 和 `get_triggers()` 方法，需补充对应的 API 端点和前端展示组件。ER 图可使用 D3.js 力导向图或 Mermaid.js 实现。

---

### 3.2 SQL 查询模块

| 编号 | 缺失需求 | 需求来源 | 严重程度 |
|------|----------|----------|----------|
| Q-1 | 基于数据库结构的智能补全（表名、字段名）未实现 | 需求 4.1 | 高 |
| Q-2 | 查询结果的数据类型特殊渲染（JSON 可折叠、日期格式化）未实现 | 需求 4.2 | 中 |
| Q-3 | 导出选中行功能未实现 | 需求 4.4 | 中 |
| Q-4 | 大数据量流式导出未实现 | 需求 4.4 | 中 |
| Q-5 | EXPLAIN 执行计划可视化未实现 | 需求 4.5 | 低（Phase 3） |

**改善建议**：
- 智能补全：调用 Explorer API 获取当前连接的表和字段，通过 `monaco.languages.registerCompletionItemProvider()` 注入 Monaco Editor。
- 数据渲染：在 `QueryResult.vue` 中根据列类型判断渲染方式，JSON 类型使用 `<pre>` + 折叠展开。
- 流式导出：使用 FastAPI 的 `StreamingResponse` + `openpyxl` 的写模式逐行写入。

---

### 3.3 文档/代码生成模块

| 编号 | 缺失需求 | 需求来源 | 严重程度 |
|------|----------|----------|----------|
| G-1 | PDF 文档生成仅输出 HTML，未集成 WeasyPrint/ReportLab | 需求 3.1 | 中 |
| G-2 | 文档模板缺少版本号字段 | 需求 3.1 | 低 |
| G-3 | 文档中未嵌入 ER 关系图 | 需求 3.1 | 低 |
| G-4 | 自定义 Jinja2 模板扩展未实现（代码生成使用硬编码字符串拼接） | 需求 3.3 | 中 |

**改善建议**：
- PDF 生成：引入 `weasyprint` 或 `pdfkit` 库，将现有 HTML 模板转换为真正的 PDF。
- Jinja2 模板：将 `_gen_sqlalchemy()` 等六个生成方法重构为 Jinja2 模板文件，放入 `templates/` 目录，支持用户自定义扩展。

---

### 3.4 API 网关模块

| 编号 | 缺失需求 | 需求来源 | 严重程度 |
|------|----------|----------|----------|
| A-1 | 全局 API Key 认证方式未实现 | 需求 5.3 | 中 |
| A-2 | IP 白名单功能未实现（ORM 字段存在但无执行逻辑） | 需求 5.3 | 中 |
| A-3 | 自动 OpenAPI/Swagger 文档生成未实现 | 需求 5.4 | 中 |
| A-4 | API 调用统计（次数、平均响应时间、错误率）未实现 | 需求 5.4 | 中 |
| A-5 | API 变更历史记录未实现 | 需求 5.5 | 低 |

**改善建议**：
- IP 白名单：在 `dynamic_gateway()` 中添加请求 IP 提取（`request.client.host`）与 `api.ip_whitelist` JSON 列表的匹配逻辑。
- 调用统计：新增 `/gateway/apis/{id}/stats` 端点，对 `ApiCallLog` 做 `GROUP BY` 聚合查询。
- OpenAPI 文档：使用 FastAPI 的 `APIRouter` 动态注册端点或手动构建 OpenAPI schema JSON。

---

### 3.5 非功能性需求

| 编号 | 缺失需求 | 需求来源 | 严重程度 |
|------|----------|----------|----------|
| N-1 | 响应式布局（适配平板/手机屏幕） | 需求 7.3 | 低 |
| N-2 | 暗色模式切换 | 需求 7.3 | 低 |
| N-3 | 国际化（中文/英文） | 需求 7.3 | 低 |
| N-4 | 异步任务执行（文档生成、大导出使用后台任务） | 需求 7.2 | 中 |

---

## 四、部分实现项清单

以下功能已搭建但存在关键缺失，需补全后方可标记为完成。

| 模块 | 功能项 | 已做 | 待补全 |
|------|--------|------|--------|
| 连接管理 | 连接池大小可调 | ORM 字段存在 | 在 Create/Update Schema 中暴露 `pool_size`，前端添加输入框 |
| 连接管理 | 定时健康检查 | `health_check()` 方法存在 | 添加后台定时任务调用健康检查并自动回收失效连接 |
| 结构浏览 | 数据库统计面板 | 表数量、总行数 | 后端聚合 `data_size` 和 `index_size` 并返回前端 |
| 结构浏览 | 表详情 | 5 个 Tab 全部存在 | 补充字段级别的字符集信息 |
| SQL 查询 | SQL 格式化 | 前端正则格式化 | 集成 `sqlparse` 做服务端格式化或使用 `sql-formatter` 前端库 |
| SQL 查询 | 结果表格可筛选 | 可排序、可分页 | 添加列级过滤器（Element Plus `filter-method`） |
| SQL 查询 | 执行统计 | 耗时、影响行数 | 补充扫描行数统计 |
| SQL 查询 | 只读模式 | 请求级开关 | 将 `read_only` 持久化为连接级属性，服务端强制校验 |
| 文档生成 | PDF 导出 | 生成 HTML | 集成 WeasyPrint 输出真正的 PDF |
| API 网关 | Token 认证 | 生成/校验逻辑存在 | 修复 ORM 字段名不一致（`auth_token` vs `token`） |
| API 网关 | 限流 | 全局限流器 | 读取每个 API 的 `rate_limit` 配置做差异化限流 |
| API 网关 | 结果缓存 | `cache_seconds` 字段存在 | 实现响应缓存逻辑（内存或 Redis） |
| API 网关 | 启用/禁用 | 开关机制存在 | 禁用后应返回 503 而非 403 |
| API 网关 | 版本管理 | `version` 字段存在 | 添加版本路由逻辑和 UI |
| 安全 | 审计日志 | 查询历史 + API 调用日志 | 补充连接 CRUD、API 发布/修改、DDL 导出的审计记录 |
| 安全 | 只读账号 | 查询守卫可用 | 改为连接级持久配置，防止客户端绕过 |
| 性能 | 查询超时 | 配置项 + 参数签名存在 | 实现超时取消逻辑（`asyncio.wait_for` 或 `execution_options`） |
| 部署 | 环境变量 | 后端支持完整 | docker-compose.yml 应通过 `.env` 文件传入敏感配置 |
| 部署 | 数据持久化 | 卷已声明 | 修正默认 `DATABASE_URL` 路径与卷挂载点对齐 |

---

## 五、改善建议

### 5.1 高优先级（影响核心功能）

1. **修复 API 网关动态路由挂载** — 这是 SQL 发布为 API 功能能否工作的决定性因素，应在 `main.py` 中立即补上 `dynamic_router` 的注册。

2. **修复 ORM 字段名不一致** — `auth_token` vs `token`、`request_params` vs `params` 等问题会导致 API 网关的认证和日志功能在运行时崩溃。

3. **实现 SQL 智能补全** — 这是数据库开发工具的核心用户体验要素。通过 Explorer API 获取表和字段列表，注入 Monaco Editor 的 CompletionProvider。

4. **实现查询超时机制** — 当前配置项形同虚设，长时间运行的查询可能耗尽服务器资源。应使用 `asyncio.wait_for()` 或 SQLAlchemy 的 `execution_options(statement_timeout=...)` 实现真正的超时取消。

### 5.2 中优先级（完善功能体验）

5. **连接池大小可调** — 在连接创建/编辑表单中添加 `pool_size` 输入框，当前硬编码为 5 不够灵活。

6. **补充存储过程/触发器展示** — 后端方言适配器已有查询方法，只需补充 API 端点和前端展示面板。

7. **PDF 文档生成** — 引入 `weasyprint` 或 `pdfkit`，将现有 HTML 模板转为真正的 PDF 输出。

8. **API 网关调用统计面板** — 对 `ApiCallLog` 做聚合查询，前端用 ECharts 展示调用趋势和错误率。

9. **结果导出增强** — 支持选中行导出和大数据量流式导出（使用 `StreamingResponse`）。

10. **docker-compose 配置优化** — 通过 `.env` 文件管理加密密钥等敏感配置，修正数据库文件路径与卷挂载点对齐。

### 5.3 低优先级（Phase 3 高级功能）

11. **ER 关系图** — 基于外键数据使用 D3.js 或 Mermaid.js 实现可视化。

12. **EXPLAIN 执行计划** — 在查询控制台添加 EXPLAIN 按钮，用树形图展示执行计划节点。

13. **暗色模式与响应式** — 使用 CSS 变量定义主题色，添加 `@media` 断点和主题切换按钮。

14. **国际化** — 引入 `vue-i18n`，将所有 UI 字符串提取为中英文 locale 文件。

15. **Jinja2 模板扩展** — 将代码生成从硬编码字符串重构为 Jinja2 模板文件，支持用户自定义模板。

---

## 六、总结

DBStudio 项目的后端骨架完整、模块划分清晰、核心业务逻辑（加密、SQL 守卫、代码生成、类型映射、DDL 转换）实现质量较高，82 个测试用例全部通过。但对照需求规格说明书，仍有约 18 项功能完全缺失、26 项部分实现，同时存在 4 个会导致运行时崩溃的阻断级 Bug。

最紧迫的修复项是：API 网关动态路由挂载、ORM 字段名不一致、查询超时机制。这三项修复后，SQL 发布为 API 的完整链路才能打通。

建议按高→中→低优先级分批迭代，优先确保核心功能链路（连接→浏览→查询→发布 API）完整可用，再逐步补全增强功能和高级特性。
