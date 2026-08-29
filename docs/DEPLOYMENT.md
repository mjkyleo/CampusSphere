# CampusSphere 部署与启动配置清单

> 适用对象：部署方 / 校方平台管理员 / 运维
> 目标：一份清单说清「首次把项目跑起来之前，需要准备哪些环境变量、配置文件、依赖服务、密钥与数据库初始化」，并标注每项配置的**用途**与**默认值**。
> 本文件与代码现状保持一致，由 `scripts/doc_sync.py` 的漂移检查辅助维护。

---

## 0. 一句话流程

```bash
# 开发（零外部依赖，开箱即跑）
cp backend/.env.example backend/.env        # 默认 SQLite，无需任何中间件
python scripts/devctl.py up                 # 启动后端 + 前端，自动健康检查

# 生产（Docker 一键）
cp deploy/.env.example deploy/.env          # 改 SECRET_KEY / DB_URL / 管理员密钥 / MinIO / Meili
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
```

---

## 1. 前置条件：依赖服务

| 服务 | 版本 | 开发（默认） | 生产 | 必需性 | 用途 |
|------|------|--------------|------|--------|------|
| Python | **3.12+** | ✅ | ✅ | 必需 | 后端运行时（`requires-python>=3.12`，注意不是 3.11） |
| Node.js | 18+ | ✅ | 22（构建期） | 前端必需 | 前端构建与 Express 代理层 |
| PostgreSQL | 16 | 不需要（默认 SQLite） | 16 | 生产必需 | 主数据库 |
| Redis | 7 | 不需要（内存兜底） | 7 | 推荐 | 缓存 / 限流 / 验证码 / 黑名单 / WS 广播 / Celery Broker |
| MinIO | 最新 | 不需要（本地磁盘兜底） | 必需 | 对象存储（或用兼容 S3） | 图片 / 文件 |
| Meilisearch | v1.11+ | 不需要（DB LIKE 兜底） | 推荐 | 全文搜索 | 物品 / 用户搜索 |
| SMTP 服务 | — | 不需要（返回 debug_code） | 必需 | 注册验证码邮件 | 邮箱验证 |
| Gemini API Key | — | 不需要（AI 入口隐藏） | 可选 | AI 助手 | 物品文案 / 课程摘要等 |

> 开发模式（SQLite + 无 Redis/MinIO/Meili）**开箱即跑**；生产环境缺 Redis/Celery 会降级，但**验证码邮件、WS 广播、搜索**等依赖外部服务的特性将不可用。

---

## 2. 配置文件清单

| 文件 | 作用 | 是否入库 | 说明 |
|------|------|----------|------|
| `backend/.env` | 后端运行环境变量（事实来源之一） | **否（gitignore）** | 由 `backend/.env.example` 复制而来，**切勿提交真实密钥** |
| `backend/.env.example` | 后端环境变量模板 | 是 | 部署者复制为 `.env`；已由 `doc_sync.py` 补全全部部署相关键 |
| `config/school.yaml` | 多校配置（校名 / OAuth / 邮箱白名单 / MinIO / Meili / 审核策略） | 是 | 「一份代码 + 一份 school.yaml = 一所学校一键上线」 |
| `config/logging.yaml` | structlog 结构化日志配置 | 是 | 调 `loggers.campus.level` 控制日志级别 |
| `deploy/.env.example` | 生产 Docker 模板 | 是 | `cp` 为 `deploy/.env` 后改敏感值 |
| `deploy/.env` | 生产环境变量 | **否（gitignore）** | 仅本地 / CI 使用 |
| `frontend/.env.example` | 前端环境变量模板 | 是 | 当前仅 `GEMINI_API_KEY`（可选） |

**配置叠加顺序**（后者覆盖前者）：
`环境变量 / .env` → `config/school.yaml` → 管理后台动态配置（`app_config` 表，DB 优先于 yaml）。

---

## 3. 环境变量全集（按分组）

> 默认值取自 `backend/app/core/config.py`。标注 **🔴 生产必改** 的项若使用占位值，非 debug 启动会被 `validate_admin_security` 直接拒绝（fail-fast）。
> 注意：邮件发送统一使用 **SMTP_SSL（端口 465）**。

### 3.1 应用基础

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `APP_NAME` | `campus-life-platform` | 应用名（日志 / 标识） | 可选 |
| `DEBUG` | `false` | 开发调试开关。**true 会绕过管理员安全强校验**，仅本地用 | 必须 `false` |

### 3.2 数据库

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `DB_URL` | `sqlite+aiosqlite:///./dev.db` | 数据库连接串。开发零依赖；生产改 `postgresql+asyncpg://user:pass@host:5432/db` | **必改** |
| `DB_POOL_SIZE` | `10` | PostgreSQL 常驻连接数 | 按负载调 |
| `DB_MAX_OVERFLOW` | `20` | 超出 pool_size 后临时连接上限 | 按负载调 |
| `DB_POOL_RECYCLE` | `1800` | 空闲连接回收秒数（规避中间件静默断连） | 可选 |
| `DB_POOL_TIMEOUT` | `30` | 等待连接池可用的最大阻塞秒数 | 可选 |

> SQLite 忽略连接池参数；仅 PostgreSQL/MySQL 生效。

### 3.3 Redis 与缓存

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接（缓存 / 验证码 / 限流 / 黑名单 / WS 广播） | 必改 |
| `CACHE_ENABLED` | `true` | 热点缓存总开关；无 Redis 时自动降级内存字典，不阻断业务 | 可选 |
| `CACHE_TTL_SECONDS` | `60` | 热点列表缓存基础 TTL（写入叠加随机抖动防雪崩） | 可选 |

### 3.4 安全 / JWT

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `SECRET_KEY` | `change-me-to-a-long-random-string-in-prod` | JWT 签名密钥 | **🔴 必改**（建议 32+ 字节随机串） |
| `JWT_ALGORITHM` | `HS256` | JWT 算法 | 一般不动 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | 访问令牌有效期（分钟） | 可选 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新令牌有效期（天） | 可选 |

### 3.5 限流

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `RATE_LIMIT_PER_MINUTE` | `120` | 单 IP + 单路径每分钟请求上限（超限 429） | 可选 |

### 3.6 管理员后台安全 🔴

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `ADMIN_GATEWAY_ENFORCE` | `true` | 是否强制校验 `X-Admin-Gateway` 头（隐藏 `/api/admin/*` 可达性）；本地联调可临时 `false` | 必须 `true` |
| `ADMIN_GATEWAY_KEY` | `""` | 网关密钥，用于换短时网关令牌；**长度 ≥ 16，非占位值** | **🔴 必改** |
| `ADMIN_BOOTSTRAP_USERNAME` | `siteadmin` | 首次启动注入的管理员用户名 | 可选 |
| `ADMIN_BOOTSTRAP_PASSWORD` | `""` | 首次启动注入的管理员密码，**长度 ≥ `ADMIN_BOOTSTRAP_MIN_LENGTH`** | **🔴 必改** |
| `ADMIN_BOOTSTRAP_MIN_LENGTH` | `16` | 引导密码最小长度 | 可选 |
| `ADMIN_BOOTSTRAP_ENABLED` | `true` | 是否自动 seed 引导管理员 | 可选 |
| `ADMIN_GATEWAY_ROTATE_SECONDS` | `3600` | 网关派生令牌轮换秒数 | 可选 |

> **fail-fast 规则**：非 debug 且 `ADMIN_GATEWAY_ENFORCE=true` 时，若 `ADMIN_GATEWAY_KEY` 缺失/过短/占位，或 `ADMIN_BOOTSTRAP_PASSWORD` 过短，或基础设施密钥仍为已知默认值（`MEILI_API_KEY=masterKey`、`MINIO_ACCESS_KEY=minioadmin` 等），启动直接 `SystemExit` 拒绝带病上线。

### 3.7 邮件（SMTP_SSL，端口 465）

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `SMTP_HOST` | `""` | SMTP 服务器地址 | **必改**（注册验证码邮件） |
| `SMTP_PORT` | `465` | SMTP 端口（465 = SSL） | 一般不动 |
| `SMTP_USER` | `""` | SMTP 登录用户 | 必改 |
| `SMTP_PASS` | `""` | SMTP 登录密码 / 授权码 | 必改 |

> 未配置时 `POST /api/auth/send-code` 返回 `debug_code` 便于联调；**生产必须配置，否则验证码无法送达**。

### 3.8 滑块验证（发送验证码前的防滥用闸门）

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `CAPTCHA_ENABLED` | `true` | 是否启用滑块；`false` 时 `send-code` 免票据（测试 / 内网） | 可选 |
| `CAPTCHA_TOLERANCE_PX` | `6` | 缺口对齐容差（像素） | 可选 |
| `CAPTCHA_TTL_SECONDS` | `300` | 滑块令牌有效期 | 可选 |
| `CAPTCHA_MAX_ATTEMPTS` | `3` | 同一滑块最大校验次数 | 可选 |
| `CAPTCHA_MIN_TRACK_POINTS` | `6` | 轨迹最少采样点（防脚本直传坐标） | 可选 |
| `CAPTCHA_TICKET_TTL_SECONDS` | `120` | 校验通过签发的票据有效期 | 可选 |

### 3.9 验证码

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `CODE_TTL_SECONDS` | `300` | 验证码有效期（秒） | 可选 |
| `CODE_MAX_ATTEMPTS` | `5` | 同一验证码最大校验次数（超出作废，防枚举） | 可选 |

### 3.10 CORS

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | 允许的前端来源（JSON 数组） | **必改**为真实域名 |

### 3.11 多校配置

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `SCHOOL_CONFIG_PATH` | `../config/school.yaml` | 多校配置文件路径 | 可选 |
| `SCHOOL_NAME` | `示例大学` | 校名（被 school.yaml 覆盖） | 由 yaml |
| `SCHOOL_DOMAIN` | `localhost` | 校域（JWT 校域校验） | 由 yaml |

### 3.12 对象存储（MinIO / S3 兼容）

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `MINIO_ENDPOINT` | （取 school.yaml） | 端点 `host:port` | 必改 |
| `MINIO_ACCESS_KEY` | （取 school.yaml） | 访问 Key | **🔴 必改**（勿用 `minioadmin`） |
| `MINIO_SECRET_KEY` | （取 school.yaml） | 密钥 | **🔴 必改**（勿用 `minioadmin`） |
| `MINIO_SECURE` | `false` | 是否 HTTPS | 按部署 |
| `MINIO_BUCKET` | `campus` | 存储桶 | 可选 |

### 3.13 搜索（Meilisearch）

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `MEILI_HOST` | `http://localhost:7700` | 搜索服务地址 | 必改 |
| `MEILI_API_KEY` | `masterKey` | 搜索密钥 | **🔴 必改**（勿用 `masterKey`） |

### 3.14 Celery 异步任务

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | 任务 Broker | 必改 |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | 结果后端 | 必改 |

### 3.15 可观测（OpenTelemetry，仅生产 compose）

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | （空） | OTLP 端点；空则回退控制台 | 可选 |
| `OTEL_EXPORTER_OTLP_INSECURE` | `true` | 内网明文 4317 设 true；公网 TLS 设 false | 可选 |
| `OTEL_SERVICE_NAME` | `campus-life-platform` | 服务名 | 可选 |

### 3.16 前端（可选）

| 变量 | 默认值 | 用途 | 生产 |
|------|--------|------|------|
| `GEMINI_API_KEY` | （空） | Gemini AI 助手密钥（前端 Express 层消费）；空则 AI 入口隐藏 | 可选 |

### 3.17 第三方 OAuth 凭证（school.yaml，非环境变量）

位于 `config/school.yaml` 的 `oauth.wechat` / `oauth.qq`（`appid` / `secret`）。**当前微信 / QQ 登录仅保留接口、未开放**；填入真实凭据并启用后即可生效。

---

## 4. 密钥与凭证安全清单

部署前逐项核对（任一未满足，生产启动将 fail-fast）：

- [ ] `SECRET_KEY`：≥ 32 字节随机串，且**不是** `change-me-...`
- [ ] `ADMIN_GATEWAY_KEY`：≥ 16 位随机串，且**不是** `change-me-admin-gateway-key`
- [ ] `ADMIN_BOOTSTRAP_PASSWORD`：≥ `ADMIN_BOOTSTRAP_MIN_LENGTH`(16) 位
- [ ] `SMTP_*`：已填真实邮件服务（注册验证码依赖）
- [ ] `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`：**不是** `minioadmin`
- [ ] `MEILI_API_KEY`：**不是** `masterKey`
- [ ] `CORS_ORIGINS`：已改为真实前端域名
- [ ] `DB_URL`：生产指向 PostgreSQL
- [ ] `school.yaml` 的 `oauth.*.secret`：如启用第三方登录需真实值

> 网关密钥与管理员密码通过**安全渠道**告知管理员，**不写入前端源码**、不入库。后端未携带有效网关令牌时 `/api/admin/*` 一律返回 404，避免被探测。

---

## 5. 数据库初始化

- **开发（SQLite）**：启动即自动建表（`init_models`）+ 按 `config/school.yaml` 的 `admin.bootstrap` 注入引导管理员，**无需手动迁移**。
- **生产（PostgreSQL）**：Docker compose 启动时自动执行 `alembic upgrade head` 完成迁移；裸机部署需手动 `alembic upgrade head`。
- **首次启动 seed**：自动创建 `admin.bootstrap.username` 管理员账号（密码取 `admin.bootstrap.password` 或环境变量覆盖）。修改密码可在管理后台操作或更新 `admin_users` 表。
- **降级说明**：无 Redis / MinIO / Meili 时分别降级为内存字典 / 本地磁盘 / SQL LIKE 搜索，主流程不受影响。

---

## 6. 启动方式

### 6.1 一键启停（推荐，跨平台）

```bash
python scripts/devctl.py up            # 启动后端 + 前端，等待健康检查通过
python scripts/devctl.py status         # 查看监听状态与 PID
python scripts/devctl.py down           # 优雅停止并校验端口释放
python scripts/devctl.py restart        # 先关再启
# 常用参数：--backend-only / --frontend-only / --wait-timeout N / --force / --mode docker
```

### 6.2 Docker Compose（生产）

```bash
cp deploy/.env.example deploy/.env     # 改敏感值
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
```

### 6.3 裸机 / venv

```bash
cd backend && pip install -e ".[dev]" && cp .env.example .env
uvicorn app.asgi:app --host 0.0.0.0 --port 8000
celery -A app.tasks.celery_app.celery_app worker --loglevel=info   # 另开终端
```

---

## 7. 部署后验证

| 验证项 | 方法 | 期望 |
|--------|------|------|
| 健康检查 | `GET /health` | `{"status":"ok",...}` |
| API 文档 | `http://localhost:8000/docs` | Swagger UI 可访问 |
| 滑块验证 | `GET /api/auth/captcha/slider` → `POST /api/auth/captcha/verify` | 返回一次性票据 |
| 发送验证码 | `POST /api/auth/send-code`（带票据） | 生产经邮件送达；未配 SMTP 返回 `debug_code` |
| 管理员登录 | `POST /api/admin/discover`（网关密钥）→ `POST /api/admin/login` | 拿到管理员令牌 |
| 指标 | `GET /metrics` | Prometheus 格式 |

---

## 8. 常见问题

- **启动即退出（SystemExit）**：多为密钥仍为占位值，见 §4 安全清单。本地联调可设 `DEBUG=true` 绕过（仅限开发）。
- **验证码收不到**：检查 `SMTP_*` 是否配置；未配置时接口返回 `debug_code`。
- **搜索无结果**：确认 Meilisearch 在线，或已触发 Celery 索引同步任务（离线自动降级 SQL）。
- **WS 连接失败**：Nginx 需透传 `Upgrade`/`Connection`；多实例依赖 Redis 广播。
- **端口占用**：后端 8000 / 前端 5173；Windows 下 3000 被 Hyper-V 保留，已固定用 5173。

---

> 维护说明：本文件与 `docs/usage.md`、`docs/部署手册.md` 互补——本文聚焦「**配置项与前置条件清单**」，部署步骤详见 `docs/部署手册.md`，日常使用见 `docs/usage.md`。配置键若有增减，请同步更新 `backend/.env.example` 并重跑 `python scripts/doc_sync.py --check`。
