# 开发指南（Development）

本文档面向参与开发的工程师，介绍项目架构、模块设计、API 约定、代码规范、测试与贡献流程。请保持文档与代码同步，任何结构性变更都需更新本文档。

## 目录

- [1. 架构概览](#1-架构概览)
- [2. 后端结构](#2-后端结构)
- [3. 前端结构](#3-前端结构)
- [4. API 约定](#4-api-约定)
- [5. 核心机制](#5-核心机制)
- [6. 数据库与迁移](#6-数据库与迁移)
- [7. 异步任务（Celery）](#7-异步任务celery)
- [8. 代码规范](#8-代码规范)
- [9. 测试](#9-测试)
- [10. 构建与发布](#10-构建与发布)
- [11. 贡献流程](#11-贡献流程)

## 1. 架构概览

模块化单体的三端协作架构：

```
┌──────────────┐   /api/*  /ws    ┌──────────────────┐
│  React SPA    │ ───────────────▶ │  Express 代理层   │
│  (HashRouter) │                  │  (server.ts:5173) │
└──────────────┘                   └────────┬─────────┘
                                            │ 反代 /api/*、/ws
                                   ┌────────▼─────────┐
                                   │  FastAPI 后端     │   SQLite(dev) / PostgreSQL(prod)
                                   │  (uvicorn:8000)  │──▶ Redis / MinIO / Meilisearch
                                   └──────────────────┘
```

- **前端代理层**（`frontend/server.ts`）是开发与生产共用的统一入口：
  - 本地处理 `/api/ai/*`（Gemini）与 `/api/health`；
  - `/api/*` 其余请求、`/ws` WebSocket 升级反代到后端 `http://127.0.0.1:8000`；
  - 开发模式挂载 Vite 中间件（HMR），生产模式托管 `dist/` 静态资源。
- **后端**（`backend/app/main.py` 应用工厂）装配：CORS → 统一异常处理 → 网关中间件（鉴权 / 限流 / 请求 ID）→ 13 个业务路由 → WebSocket → OpenTelemetry。

> 关键环境约定：后端监听 `127.0.0.1:8000`；前端固定 `5173`（3000 处于 Windows Hyper-V 排除范围）；代理目标用 `127.0.0.1` 而非 `localhost`（Node 24 会把 `localhost` 解析为 IPv6 `::1`）。

## 2. 后端结构

```
backend/
├── app/
│   ├── main.py              # 应用工厂：装配中间件 / 路由 / WS / 生命周期
│   ├── asgi.py              # ASGI 入口
│   ├── core/                # 横切关注点
│   │   ├── config.py        # pydantic-settings 配置（.env + school.yaml 叠加）
│   │   ├── database.py      # async SQLAlchemy engine / SessionLocal / init_models
│   │   ├── security.py      # JWT、密码哈希
│   │   ├── redis.py         # Redis 客户端封装
│   │   ├── middleware.py    # GatewayMiddleware（鉴权 / 限流 / 请求 ID）
│   │   ├── exceptions.py    # 统一异常处理器 + 业务错误码
│   │   ├── response.py      # 统一响应结构（code / message / data）
│   │   ├── logging.py       # structlog 配置
│   │   └── storage.py       # MinIO 客户端
│   ├── common/              # Base / Mixins / 枚举 / 工具
│   ├── modules/             # 业务模块（每模块 router + service + models + schemas）
│   │   ├── auth/            # 注册 / 登录 / 绑定 / Token
│   │   ├── user/            # 用户资料
│   │   ├── item/            # 二手交易（含审核策略）
│   │   ├── message/         # 私信 + WebSocket /ws
│   │   ├── course/          # 课程与评价
│   │   ├── canteen/         # 食堂与档口
│   │   ├── job/             # 兼职
│   │   ├── share/           # 分享圈
│   │   ├── teammate/        # 队友招募
│   │   ├── report/          # 举报与封禁
│   │   ├── admin/           # 管理后台（含 seed 默认管理员）
│   │   ├── storage/         # 文件上传
│   │   └── launcher/        # 启动器 + OpenTelemetry（otel.py）
│   ├── tasks/               # Celery 任务
│   └── search/              # Meilisearch 客户端
├── alembic/                 # 迁移脚本
├── scripts/                 # fake_redis_server.py / gen_api_docs.py 等
├── tests/                   # pytest 冒烟测试（13 个文件）
├── pyproject.toml
└── Dockerfile
```

### 模块开发规范

每个业务模块保持同构结构：

```
app/modules/<name>/
├── router.py     # APIRouter，定义端点
├── service.py    # 业务逻辑（依赖注入 Session）
├── models.py     # SQLAlchemy 模型
└── schemas.py    # pydantic 请求 / 响应模型
```

新增模块三步骤：在 `modules/` 下创建模块 → 在 `app/main.py` 注册 `include_router` → 在 `app/tasks`（如需要异步任务）。

## 3. 前端结构

```
frontend/
├── App.tsx                 # 根组件：HashRouter + AuthProvider + ToastProvider
├── main.tsx                # 入口
├── server.ts               # Express 代理层（AI 端点 + 反代 + WS）
├── vite.config.ts
├── pages/                  # 16 个页面（见下方路由表）
├── components/             # Navbar / ReportModal 等公共组件
├── context/                # AuthContext / ToastContext
├── services/
│   ├── api.ts              # 后端 API 封装（Token 存取、统一请求、价格换算）
│   ├── websocket.ts        # WebSocket 客户端（消息中心）
│   └── geminiService.ts    # AI 端点封装（带兜底文案）
└── types.ts                # 与后端 schemas 对齐的 TS 类型
```

页面路由（HashRouter）：

| 路由 | 页面组件 |
| --- | --- |
| `/` | `HomePage` |
| `/market`、`/market/:id`、`/market/publish` | `MarketList` / `MarketDetail` / `MarketPublish` |
| `/courses`、`/courses/:id`、`/courses/review` | `CourseSearch` / `CourseDetail` / `CourseReview` |
| `/canteens`、`/canteens/:id` | `CanteenList` / `CanteenStall` |
| `/teammates` | `TeammatePost` |
| `/share` | `ShareFeed` |
| `/jobs` | `JobList` |
| `/messages` | `MessageCenter` |
| `/profile` | `UserProfile` |
| `/admin` | `AdminDashboard` |
| `/login` | `LoginPage` |

> 前端 `services/api.ts` 内置了一份 Mock 数据（`INITIAL_MOCK_DATA`）作为后端不可用时的降级展示，业务代码应始终通过 `api.ts` 统一访问后端。

## 4. API 约定

### 统一响应结构

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

- 成功 `code = 0`；
- 业务错误返回 **HTTP 200** + 非零 `code`（便于前端统一处理）：

| code | 含义 |
| --- | --- |
| `40100` | 未认证 / Token 过期 |
| `40300` | 无权限 |
| `40400` | 资源不存在 |
| `40900` | 冲突（账号被绑定等） |
| `42200` | 参数校验失败 |

### 认证方式

- 请求头：`Authorization: Bearer <access_token>`；
- 网关中间件 `GatewayMiddleware` 负责鉴权与限流（默认 120 次 / 分钟 / IP）；
- 业务端点通过依赖注入获取当前用户（`app/modules/auth/deps.py` 或等价机制）。

### 主要端点分组（共 73 个）

| 分组 | 前缀 | 说明 |
| --- | --- | --- |
| auth | `/api/auth/*` | 注册 / 登录 / 绑定 / 刷新 |
| user | `/api/user/*` | 资料 |
| item | `/api/items/*` | 二手交易 |
| message | `/api/messages/*` | 私信（+ `/ws`） |
| course / canteen / job / share / teammate | `/api/...` | 各业务 CRUD 与评价 |
| report | `/api/reports/*` | 举报 |
| admin | `/api/admin/*` | 管理后台 |
| storage | `/api/files/*` | 上传 |

完整列表见 [docs/API_Reference.md](API_Reference.md)，机器可读版本为 `docs/openapi.json`（可用 `backend/scripts/gen_api_docs.py` 重新生成）。

## 5. 核心机制

### 5.1 配置加载链

1. `backend/.env`（`pydantic-settings` 读取 `DB_URL` / `REDIS_URL` / `SECRET_KEY` / `CORS_ORIGINS` 等）；
2. `config/school.yaml`（`Settings.load_school_config()` 合并多校字段：校名 / OAuth / 邮箱注册规则 / MinIO / Meili / 举报策略 / 物品审核）；
3. 后台动态配置（DB 优先，如邮箱注册规则、物品发布审核开关），实时生效。

> 原则：**一份代码 + 一份 school.yaml = 一所学校**。

### 5.2 WebSocket 消息

- 端点：`/ws`（`app/modules/message/ws.py`）；
- 生命周期：应用启动时 `manager.start_listener()` 订阅 Redis 广播；
- 前端 `services/websocket.ts` 负责连接与消息处理；生产经 nginx 配置 `/ws` 升级。

### 5.3 网关中间件（`app/core/middleware.py`）

请求处理顺序：请求 ID 注入 → 限流计数 → JWT 解析与用户注入 → 放行到业务路由 → 统一异常包装。

### 5.4 统一异常（`app/core/exceptions.py`）

业务异常抛出后由 `register_exception_handlers` 统一捕获，转换为 `{code, message, data}` 结构，避免端点内重复 try/except。

### 5.5 AI 服务（前端层）

`frontend/server.ts` 中的 `/api/ai/*` 端点调用 Gemini：

- 模型降级链：`gemini-2.5-flash → gemini-3.1-flash-lite → gemini-flash-latest`；
- 无 Key / 服务不可用时返回内置兜底文案（`fallback: true`）；
- 前端 `services/geminiService.ts` 对失败同样有本地兜底。

## 6. 数据库与迁移

- **开发（默认）**：SQLite（`sqlite+aiosqlite:///./dev.db`），应用启动时 `init_models` 自动建表，无需手动迁移；
- **生产**：PostgreSQL 16（`postgresql+asyncpg`），容器启动执行 `alembic upgrade head`；
- **迁移流程**：修改模型后

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## 7. 异步任务（Celery）

队列与任务：

| 队列 | 任务 | 说明 |
| --- | --- | --- |
| `email` | `app.tasks.email.send_welcome` / `send_email` | 注册欢迎邮件 / 通用邮件 |
| `notify` | `app.tasks.notify.send_notify` | 站内通知投递 |
| `search` | `app.tasks.search_sync.sync_item` / `sync_user` / `delete_doc` | Meilisearch 文档同步 |
| `default` | `app.tasks.summary.generate_trade_summary` | 交易会话摘要 |

启动 worker：

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info -Q email,notify,search,default
```

> 生产环境 worker 容器通过同步驱动访问 PostgreSQL（`sync_db`），无需额外配置。

## 8. 代码规范

- **Python**：遵循 `pyproject.toml` 中的 ruff 配置；使用 `black` 风格格式化；类型标注完整；日志使用 structlog 结构化字段（`_logger.info("event", key=value)`），禁用裸 `print`；
- **TypeScript / React**：函数组件 + Hooks；类型定义集中在 `types.ts`；组件样式使用 Tailwind；提交前通过 `tsc --noEmit`；
- **提交信息**：约定式提交（`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`）；
- **文档**：涉及结构 / 端口 / 端点变更时同步更新 `docs/` 与根目录 `README.md`。

## 9. 测试

后端 pytest（`backend/tests/`，13 个文件，覆盖认证 / 注册 / 物品 / 审核 / 课程食堂 / 消息 / WebSocket / Celery 摘要 / 冒烟）：

```bash
cd backend
pytest -q
```

前端类型检查：

```bash
cd frontend
npm run lint     # tsc --noEmit
```

冒烟测试基线（本地全链路）：页面 200 → 健康检查 → 管理员登录 → 用户注册登录 → 物品列表 → WebSocket 101 → CORS 校验。

## 10. 构建与发布

```bash
# 后端（容器）
docker build -f backend/Dockerfile -t campus-app .

# 前端：Vite 构建 + 代理层打包为 Node CJS
cd frontend
npm run build    # 产出 dist/（含 server.cjs）
npm start        # 生产模式运行代理层（node dist/server.cjs）
```

生产拓扑：nginx（80/443）→ 前端产物或代理层 → FastAPI（8000）→ PostgreSQL / Redis / MinIO / Meilisearch。一键编排见 `deploy/docker-compose.yml`。

## 11. 贡献流程

1. 阅读本文档与 [docs/项目现状分析.md](项目现状分析.md)，了解当前进度；
2. 从 [docs/后续开发计划.md](后续开发计划.md) 认领任务（建议先同步计划表）；
3. 分支命名：`feat/<功能>`、`fix/<问题>`、`docs/<主题>`；
4. 开发完成后本地验证：`pytest -q` + `npm run lint` + 冒烟测试；
5. 提交 PR：说明变更内容、影响面与验证结果，由维护者评审合并。

**特别约定**：新增或改动 API 端点后，在 `backend/` 下运行 `python scripts/gen_api_docs.py` 重新生成 `docs/API_Reference.md` 与 `docs/openapi.json`，并同步更新本文档与 README。
