# 使用说明（Usage）

本文档面向项目使用者与运维人员，覆盖环境准备、安装、配置、启动、功能使用与生产部署全流程。文档内容与当前代码实现保持一致（v1.0.0）。

## 目录

- [1. 环境要求](#1-环境要求)
- [2. 安装步骤](#2-安装步骤)
- [3. 配置说明](#3-配置说明)
- [4. 启动服务](#4-启动服务)
- [5. 测试账号](#5-测试账号)
- [6. 功能模块使用](#6-功能模块使用)
- [7. API 与接口文档](#7-api-与接口文档)
- [8. 生产部署](#8-生产部署)
- [9. 常见问题](#9-常见问题)

## 1. 环境要求

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.12+ | 后端运行时 |
| Node.js | 18+ | 前端构建与代理层 |
| npm | 9+ | 前端依赖管理 |
| PostgreSQL | 16（可选） | 生产数据库；开发默认用 SQLite，零依赖 |
| Redis | 7（可选） | 消息广播 / Celery 队列；开发可用内置假 Redis 替代 |
| Docker + Compose | 最新（可选） | 生产一键部署 |

> 开发模式（SQLite）**不需要** PostgreSQL / Redis / MinIO / Meilisearch，开箱即跑。

## 2. 安装步骤

### 2.1 后端

```bash
cd backend

# 创建虚拟环境（Windows）
python -m venv .venv
.venv\Scripts\activate
# macOS / Linux：source .venv/bin/activate

# 安装依赖（含开发依赖）
pip install -e ".[dev]"

# 生成环境变量文件（默认 SQLite）
cp .env.example .env
```

### 2.2 前端

```bash
cd frontend
npm install
```

## 3. 配置说明

配置采用「三层叠加」：**环境变量 / `.env` → `config/school.yaml` → 后台动态配置**。

### 3.1 `backend/.env`（基础配置）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_URL` | `sqlite+aiosqlite:///./dev.db` | 生产切换 `postgresql+asyncpg://campus:campus@host:5432/campus` |
| `REDIS_URL` | `redis://localhost:6379/0` | 消息广播 / 验证码缓存 |
| `SECRET_KEY` | `change-me-...` | **生产必须修改**，建议 32+ 字节随机串 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | 访问 Token 有效期 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新 Token 有效期 |
| `RATE_LIMIT_PER_MINUTE` | `120` | 网关限流 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 允许的前端来源，用 JSON 数组 |
| `SCHOOL_CONFIG_PATH` | `../config/school.yaml` | 多校配置路径 |
| `MINIO_*` / `MEILI_*` | 见 `.env.example` | 对象存储 / 搜索引擎 |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1`、`/2` | Celery 队列 |

### 3.2 `config/school.yaml`（多校配置）

| 区块 | 说明 |
| --- | --- |
| `school_name` / `school_domain` | 学校名称 / 域名，影响界面与 JWT 校域校验 |
| `oauth` | 微信 / QQ 开放平台凭据（占位符需替换），`state_ttl` 防 CSRF |
| `auth.email_register` | 邮箱注册开关、域名白名单、正则校验；可在后台 `/api/admin/auth/email-config` 动态覆盖（DB 优先） |
| `minio` | 对象存储端点 / 密钥 / 桶 / 签名 URL 有效期 |
| `meilisearch` | 搜索服务地址 / 密钥 / 索引 |
| `report_policy` | 自动封禁阈值（默认 5 次）、工单升级时限（默认 48h） |
| `items.review` | 二手发布审核开关：`false` 发布即上架，`true` 进入待审核 |

> 部署新校时复制 `school.yaml` 修改字段即可（"改配置即上线"）。

### 3.3 `config/logging.yaml`

structlog 结构化日志配置，输出到 stdout 便于容器采集。调整 `loggers.campus.level` 可控制日志级别。

## 4. 启动服务

### 4.1 启动后端

```bash
cd backend
uvicorn app.asgi:app --reload --port 8000
```

启动时自动完成：

- 开发模式（SQLite）自动建表（`init_models`），无需手动迁移；
- 按 `config/school.yaml` 的 `admin.bootstrap` 段注入引导管理员账号（配置下发，非硬编码）；
- 启动 WebSocket Redis 广播监听。

### 4.2 启动前端

```bash
cd frontend
npm run dev
```

前端 Express 层（`server.ts`）监听 **5173**，职责：

- 本地处理 `/api/ai/*`（Gemini 智能助手）与 `/api/health`；
- 其余 `/api/*` 反代到后端 `http://127.0.0.1:8000`；
- `/ws` WebSocket 升级转发到后端（实时消息）。

打开 <http://localhost:5173> 即可访问。

### 4.3 可选：无 Redis 环境的本地开发

```bash
# 终端 A：启动内置假 Redis（监听 127.0.0.1:6379）
cd backend && python scripts/fake_redis_server.py

# 终端 B：启动 Celery worker（异步任务：邮件 / 通知 / 搜索同步 / 交易摘要）
celery -A app.tasks.celery_app.celery_app worker --loglevel=info -Q email,notify,search,default
```

## 5. 测试账号

| 角色 | 账号 | 密码 |
| --- | --- | --- |
| 管理员 | 由 `admin.bootstrap.username` 配置下发 | 由 `admin.bootstrap.password` 配置下发（另需网关密钥换取登录令牌） |

普通用户：注册页面走邮箱验证码流程（开发模式未配置 SMTP 时，`POST /api/auth/send-code` 会直接返回 `debug_code` 便于联调，前端自动填入；注册邮箱需符合 `config/school.yaml` 的 `auth.email_register` 白名单规则）。

## 6. 功能模块使用

前端为单页应用（HashRouter），共 16 个页面：

| 路由 | 功能 | 说明 |
| --- | --- | --- |
| `/` | 首页 | 校园动态、智能洞察卡片（AI） |
| `/market` | 二手市场列表 | 按分类浏览闲置 |
| `/market/:id` | 二手详情 | 物品信息、交易会话 |
| `/market/publish` | 发布闲置 | 支持 AI 一键生成文案 |
| `/courses` | 课程搜索 | 课程查询 |
| `/courses/:id` | 课程详情 | 教学信息 |
| `/courses/review` | 课程评价 | 学生评价 + AI 选课摘要 |
| `/canteens` | 食堂列表 | 食堂浏览 |
| `/canteens/:id` | 食堂档口 | 档口 / 菜品、评价 |
| `/teammates` | 队友招募 | 组队发帖、入队申请 |
| `/share` | 分享圈 | 动态发布与评论 |
| `/jobs` | 兼职 | 兼职发布 / 申请 |
| `/messages` | 消息中心 | WebSocket 实时私信 |
| `/profile` | 个人中心 | 资料编辑、账号绑定（邮箱 / 手机 / QQ / 微信） |
| `/admin` | 管理后台 | 数据看板、举报处理、审核与注册规则配置 |
| `/login` | 登录 / 注册 | 统一登录（邮箱 / 手机号 / 自定义账号） |

### 6.1 账号体系

- **邮箱注册**：`POST /api/auth/email-register`，需验证码（`purpose=register`），符合域名白名单自动生成唯一自定义账号；
- **统一登录**：`POST /api/auth/login` 的 `account` 字段同时接受 邮箱 / 手机号 / 自定义账号；
- **多方式绑定**（登录后）：绑定邮箱 / 手机 / QQ / 微信，冲突时返回 `40900` 拒绝绑定；
- **Token**：JWT 双 Token（access 15 分钟 + refresh 7 天），刷新走 `/api/auth/refresh`。

### 6.2 AI 助手（前端本地端点，无需登录）

| 端点 | 功能 |
| --- | --- |
| `POST /api/ai/insights` | 校园智能生活洞察（按主题生成一句话指南） |
| `POST /api/ai/item-description` | 二手物品转让文案生成 |
| `POST /api/ai/course-summary` | 课程评价深度摘要 |
| `POST /api/ai/categorize` | 校园帖子分类与安全校验 |

配置环境变量 `GEMINI_API_KEY`（或 `API_KEY`）启用真实模型调用；模型按 `gemini-2.5-flash → gemini-3.1-flash-lite → gemini-flash-latest` 自动降级；未配置 Key 或模型不可用时自动返回内置兜底文案（响应带 `fallback: true`）。

### 6.3 消息与举报

- 私信通过 `/ws` WebSocket 实时推送（Redis pub/sub 广播，支持多实例）；
- 各模块内容可发起举报，达到阈值自动封禁（`report_policy.auto_ban_threshold`），超时工单自动升级。

## 7. API 与接口文档

- **在线文档**：启动后端后访问 <http://localhost:8000/docs>（Swagger UI）；
- **离线参考**：[docs/API_Reference.md](API_Reference.md)（128 个接口端点字段级说明）；机器可读：`docs/openapi.json`；
- **健康检查**：`GET /api/health`（前端层）/ `GET /health`（后端）/ `GET /metrics`（指标）。

**接口约定**：业务错误统一返回 **HTTP 200**，错误码在响应体 `code` 字段：

| 错误码 | 含义 |
| --- | --- |
| `40100` | 未认证 / Token 失效 |
| `40300` | 无权限 |
| `40400` | 资源不存在 |
| `40900` | 冲突（如账号已被绑定） |
| `42200` | 参数校验失败 |

## 8. 生产部署

### 8.1 Docker Compose 一键部署

```bash
# 构建前端产物（dist/ 会被 nginx 挂载）
cd frontend && npm run build

# 一键拉起：postgres + redis + minio + meilisearch + app + worker + nginx
docker compose -f deploy/docker-compose.yml --env-file deploy/.env.example up -d
```

服务端口：

| 服务 | 端口 |
| --- | --- |
| nginx（前端 + 反代） | 80 / 443 |
| app（FastAPI） | 8000 |
| MinIO Console | 9001 |

生产容器内 `app` 启动时自动执行 `alembic upgrade head` 完成迁移，`worker` 通过同步驱动访问 PostgreSQL。

### 8.2 生产注意事项

1. 修改 `SECRET_KEY` 为强随机值；
2. 修改 `school.yaml` 中的 OAuth 凭据与 Meili `masterKey`；
3. `DB_URL` 切换为 PostgreSQL，并确认 `CORS_ORIGINS` 为实际域名；
4. 详见 [部署手册.md](部署手册.md)。

## 9. 常见问题

**Q：前端 5173 端口启动失败？**
Windows Hyper-V 会保留部分端口段（如 2948-3047，含 3000），绑定会报 `EACCES`。项目已固定使用 5173，无需处理；如仍冲突，修改 `frontend/server.ts` 与 `frontend/vite.config.ts` 的端口即可。

**Q：后端启动报 `redis` 连接错误？**
开发模式下部分功能（验证码、广播）依赖 Redis。无 Redis 时可先运行 `python scripts/fake_redis_server.py`；生产环境必须配置真实 Redis。

**Q：AI 功能返回固定兜底文案？**
未配置 `GEMINI_API_KEY` 或模型服务不可用时会降级。设置环境变量后重启前端即可。

**Q：邮箱注册被拒绝？**
检查 `config/school.yaml` 的 `auth.email_register.domains` 白名单；管理员可在后台动态覆盖该规则。
