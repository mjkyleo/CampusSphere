# CampusSphere 测试覆盖与生产落地评估

> 主理人：齐活林 · QA：严过关
> 分析日期：2026-08-28 · 代码基：本地 `main`

---

## 0. TL;DR 评分卡

| 维度 | 评分(0-5) | 结论 |
|---|---|---|
| 配置管理与环境变量隔离 | 2 | 多源配置清晰，但占位弱密钥被 compose 直接引用、无 staging、debug_code 泄露风险 |
| 日志与监控体系 | 2 | structlog JSON 良好；`/metrics` 可用；**OTel 仅 Console 导出，追踪形同虚设**；无告警规则 |
| 错误处理与异常恢复 | 3 | 统一 BizError + 黑名单 + Celery 重试完善；但多处静默吞异常、外部依赖降级无统一可观测 |
| 安全性加固 | 2 | 鉴权/IDOR/密码哈希扎实；**默认 SECRET_KEY、占位网关/MinIO/Meili 密钥、无 HTTPS、无 WAF/限流纵深** |
| 性能瓶颈与可扩展性 | 2 | **0 处 selectinload（N+1 风险）、MinIO 同步阻塞事件循环**；无连接池调优、无缓存层 |
| 自动化测试覆盖率 | 2 | 51 个测试函数覆盖 ~9/14 模块；**7 模块零测试**、无行覆盖率门禁、无 E2E |
| 部署方案 | 2 | compose 完整但**用 .env.example 占位密钥起、无 HTTPS、无健康检查、无 CI/CD**、镜像未锁版本 |

> 总评：高质量**教学/原型级**单体，工程化与生产加固明显不足。可上线（单校低风险场景），但**不应直接暴露公网**。

---

## 1. 测试覆盖率分析

### 1.1 测试文件与覆盖模块映射
`backend/tests/` 共 **14 个文件、51 个 `test_` 函数**（实测 `grep -rc`）。

| 测试文件 | 覆盖模块 | 类型 |
|---|---|---|
| test_smoke.py | 冒烟 | 集成 |
| test_p1.py | 核心链路(P1) | 集成 |
| test_auth.py / test_auth_email.py | auth | 集成 |
| test_user.py | user | 集成 |
| test_item.py / test_item_review.py | item | 集成 |
| test_course_canteen.py | course / canteen | 集成 |
| test_message.py / test_websocket.py | message(含 WS) | 集成 |
| test_admin_gateway.py | admin(网关隐藏) | 集成 |
| test_celery_summary.py | tasks/ai | 集成 |

### 1.2 缺口
- **零测试的模块（7/14）**：`job`、`share`、`teammate`、`report`、`storage`、`launcher`，`ai` 仅经 celery_summary 间接覆盖。
- **断言质量**：以集成测试为主，多断言 `code==0`/HTTP 200；业务语义断言（如「越权返回 403」「PENDING 对他人 404」）仅 item/admin 少量覆盖。
- **边界/异常用例**：限流触发、黑名单登出、WebSocket 断线补偿、Celery 失败重试缺乏专门用例。
- **前端测试**：**无任何测试框架**（无 jest/vitest/playwright），仅靠 `tsc --noEmit` 类型检查。
- **行覆盖率**：本环境无法安装依赖运行 `pytest-cov`，**暂无百分比**；建议上线前补测并设门禁（≥70%）。

> 复测命令（依赖装好后）：
> `cd backend && .venv/Scripts/python.exe -m pytest -q --cov=app --cov-report=term-missing`

---

## 2. 配置管理与环境变量隔离

**现状**：三层配置——`.env`（基础/密钥）、`config/school.yaml`（多校业务）、`deploy/.env.example`（部署样例）。`core/config.py` 加载顺序 `.env → school.yaml 覆盖`，`MINIO_*/MEILI_*` 以 `.env` 优先于 yaml。`get_settings()` 用 `lru_cache` 单例。

**证据/风险**：
- `Settings(extra="allow")`（`config.py:32`）：任意环境变量可注入，扩大攻击面，建议 `extra="ignore"`。
- `deploy/docker-compose.yml:52` `env_file: ./deploy/.env.example` 直接以**占位弱密钥**（`ADMIN_GATEWAY_KEY=change-me-admin-gateway-key-16plus`、`MEILI_API_KEY=masterKey`、`minioadmin/minioadmin`、PG `campus/campus`）起生产服务；`validate_admin_security` 仅校验长度 ≥16，占位值**能通过** → 一键部署即带已知弱密钥。**高风险**。
- `school.yaml` `ai.api_key: ""` 与 `GEMINI_API_KEY` 仅后端持有，前端无硬编码（已核实 `frontend/services` 无密钥）——✅。
- **无 staging 概念**：dev / prod 仅靠 `DEBUG` + `.env` 内容区分，易误配。

**改进方向**：密钥经 Vault/Secret Manager/K8s Secret 注入；compose `env_file` 指向真实 `.env` 并由 CI 校验密钥强度；`extra="ignore"`；增加 `ENV=dev|staging|prod` 维度。

---

## 3. 日志与监控体系

**现状**：`core/logging.py` 用 structlog → JSON stdout，注入 `request_id`；`config/logging.yaml` 分级。`/metrics` 由 `launcher/metrics.py`（prometheus_client）真实注册（`launcher/router.py:37`）。健康检查 `/health` 存在。OpenTelemetry 在 `launcher/otel.py` 初始化。

**证据/风险**：
- **OTel 仅 `ConsoleSpanExporter`**（`otel.py:24`）：span 打印到 stdout，**未配置 OTLP exporter**，无 Jaeger/Tempo 收集 → 分布式追踪在生产**实际不可用**。README 声称「OpenTelemetry（OTLP）」与实现不符。
- 健康检查**未区分 liveness/readiness/startup**，K8s 无法精细探针。
- `backend/` 散落 `uvicorn.log`/`celery_worker.log`/`fake_redis.log` 等——说明日志曾落盘但未轮转（靠 `.gitignore` 忽略）。
- `deploy/prometheus/`、`deploy/grafana/` 存在但**无告警规则文件核实**（目录需补 `rules.yml`）；`nginx` 的 `/metrics` 用 `allow 10.0.0.0/8` 限制，网段不符多数云环境，可能误伤监控抓取。

**改进方向**：OTel 改用 `OTLPSpanExporter` + 环境变量 `OTEL_EXPORTER_OTLP_ENDPOINT`；拆分三探针；日志落盘加 `logging.handlers.RotatingFileHandler` 或由采集器统一处理；补齐 Prometheus 告警规则与 Grafana 看板。

---

## 4. 错误处理与异常恢复机制

**现状**：`core/exceptions.py` 统一 `BizError` + `RequestValidationError`/`404`/`500` handler，包装为 `ApiResponse`。外部依赖（Redis/MinIO/Meili/SMTP/Gemini）均有降级。Celery 任务配 `max_retries=3` + `retry_backoff` + `acks_late=True`（`tasks/celery_app.py:56-70`，`email.py`/`notify.py` 显式 `self.retry`）。

**证据/风险**：
- **业务错误一律 HTTP 200 + body.code**（设计取舍）：API 网关、WAF、状态监控无法按 HTTP 状态码区分成败，告警/限流联动受限。
- 多处 `except Exception: pass` 静默吞异常：`main.py`(seed/ws listener)、`redis.get_redis`、`storage._ensure_minio`、`ws._redis_listen`——降级合理但**缺结构化告警**，排障盲区。
- WebSocket 断线补偿（`since` 增量）✅；但消息持久化在 WS 协程内同步 DB，断连期间消息不丢（靠 DB）。

**改进方向**：关键降级路径补 `_logger.warning` + 指标计数；考虑对框架级错误用真实 HTTP 状态码（或保留业务码但暴露 Prometheus 错误计数）；为 Celery 死信队列（DLQ）配置。

---

## 5. 安全性加固

### 5.1 依赖漏洞（待补测）
> 本环境未能完成 `pip-audit` / `npm audit`（依赖安装超时）。**已知结构性风险**：`pyproject.toml` 全部 `>=` 无上限（如 `meilisearch>=0.32`、`fastapi>=0.111`），无 `lockfile` → 构建可拉入未来带漏洞/破坏性版本。镜像 `minio/minio:latest` 漂移。**强烈建议**生成并锁定 `uv.lock`/`pip-tools` 约束，纳入 `pip-audit`/`npm audit` 到 CI。

### 5.2 敏感信息暴露
- `backend/.env` 已被 `.gitignore` 忽略（实测 `git ls-files` 无 `.env`）✅，未入库。
- `config/school.yaml` 与 `deploy/.env.example` 含**明文弱密钥**（masterKey / minioadmin / change-me-*），且被 compose 直接引用（见 §2）。
- 前端源码无硬编码密钥（已 grep 核实）✅。

### 5.3 认证授权
- JWT：`HS256`，`SECRET_KEY` 默认占位 `change-me-...`（生产必须覆盖，否则可被伪造）；access 15m / refresh 7d；登出将 jti 写入 Redis 黑名单（TTL=剩余时长）✅。
- 网关隐藏：`/api/admin/*`（除 discover）无 `X-Admin-Gateway` 一律 404 ✅；`admin/router` 经 `get_current_admin`/`require_admin` 校验 `is_admin` ✅（非仅网关密钥）。
- **IDOR**：`item/router.py` 校验 `owner_id==user.id` 才允许改/删、PENDING 对他人 404 ✅——样本良好。但 **job/share/teammate/report/storage** 等模块**未见统一所有权校验测试**，需逐接口核实（特别是 report 处理、teammate 队伍管理、message 会话越权）。

### 5.4 其他
- CORS：`allow_credentials=True` + `allow_methods/headers=["*"]`（`main.py:81-87`）——生产应显式白名单 origins/methods。
- 密码：`bcrypt` ✅（强）。
- 限流：网关固定窗口 120/min/IP（`middleware.py`），Redis 缺失时**不生效**；nginx 另有限流（纵深 ✅）。登录/验证码接口**无独立更严格限流/防爆破**（仅靠全局 120/min）。
- XSS：项目源码**未发现 `dangerouslySetInnerHTML`**（仅 node_modules 类型定义）✅，React 默认转义缓解。
- CSRF：JWT Bearer 模式，SPA 场景风险低；管理后台表单需注意。
- SQL 注入：ORM 参数化，风险低；`database._run_sqlite_column_migrations` 用 f-string 拼表名/列名（仅 SQLite 迁移、值来自代码常量，非外部输入）风险可控。

---

## 6. 性能瓶颈与可扩展性

**现状/证据**：
- **N+1 查询风险高**：全模块 `selectinload` 使用数 = **0**（`grep -rc selectinload` 合计 0）。列表/详情接口大量关系字段（用户、物品、评论）未预加载 → 每行一次额外查询，并发下放大。
- **MinIO 同步阻塞事件循环**：`core/storage.py` 的 `upload_bytes`(async) 内调用同步 `self._client.put_object`（`storage.py:86`），`presigned_*`/`remove_object` 同理 → 文件上传/签名**阻塞 asyncio 单线程**，高并发上传拖垮整实例。应改用 `aiominio` 或 `run_in_threadpool`。
- 连接池：PostgreSQL 仅 `pool_pre_ping=True`，未设 `pool_size`/`max_overflow` → 默认 5 连接，高并发易耗尽。
- 缓存：Redis 仅用于限流/黑名单/WS 广播，**无业务缓存**（热点列表、课程、食堂可缓存）。
- WebSocket：Redis Pub/Sub 跨实例广播 ✅，水平扩展可行；`upstream campus_app` 可加实例。
- 前端：无代码分割/懒加载（`vite build` 单包），管理后台 recharts 体积大。

**改进方向**：列表接口补 `selectinload`/`joinedload`；MinIO 换 `aiominio` 或 `anyio.to_thread`；连接池调优；热点数据加 Redis 缓存 + 失效策略；前端路由级懒加载。

---

## 7. 自动化测试覆盖率
见 §1。补测建议：优先补 `report`（自动封禁/越权）、`teammate`/`job`（状态机）、`storage`（上传/清理）、`ai`（降级）的单元+集成测试；前端引入 Vitest + 关键页面组件测试；CI 加 `pytest --cov` 门禁与 Playwright E2E 冒烟。

---

## 8. 部署方案

**现状**：
- `docker-compose.yml`：app+worker+pg+redis+minio+meili+nginx 一站式，`depends_on` 用 `service_healthy/service_started`，配置卷持久化 ✅。
- `Dockerfile`：单阶段 `python:3.12-slim`，**未多阶段、未非 root、依赖未锁版本、无 HEALTHCHECK 指令**；`CMD` 直接 `uvicorn`（compose 内覆盖为 `alembic upgrade head && uvicorn`）。
- `Dockerfile.worker`：子集依赖，无锁版本。
- **nginx**：`/api`、`/ws` 反代 app；`client_max_body_size 20m`；`/metrics` 限制网段。**但 `listen 80` 的 HTTPS 跳转被注释** → 默认**明文 HTTP**；`limit_req` 120r/m 纵深限流 ✅。
- `app`/`worker` **无 healthcheck**；nginx `depends_on app` 仅 `service_started` → 可能流量早于就绪。
- `meilisearch` `MEILI_ENV: development` + `masterKey`；`minio:latest`；PG `campus/campus` —— 均为不安全默认值。
- **零 CI/CD**：仓库无 `.github/`/`.gitlab-ci.yml`/`Jenkinsfile`/`.circleci`（已核实）→ 测试、构建、镜像、部署**全手动**。

**改进方向**：镜像多阶段 + 非 root + `HEALTHCHECK` + 锁版本；compose 加 `restart: unless-stopped`、资源 `deploy.resources`、app/worker healthcheck；nginx 启用 HTTPS（挂载证书）；密钥经 secret；Meili 生产模式 + 强 master key；引入 GitHub Actions：lint → typecheck → pytest --cov → build → 镜像推送 → 部署；数据库迁移纳入发布流程（alembic 自动化 + 备份）。

---

## 9. 生产落地 P0 阻塞项

| # | 阻塞项 | 必须解决 |
|---|---|---|
| P0-1 | 默认/占位密钥（SECRET_KEY、网关、MinIO、Meili、PG）可直接起服务 | 强制真实密钥 + CI 密钥强度校验 |
| P0-2 | 无 HTTPS（nginx 跳转注释） | 启用 TLS，全链路加密 |
| P0-3 | 零 CI/CD，测试/构建/部署全手动 | 建最小 GitHub Actions |
| P0-4 | OTel 仅 Console 导出，追踪不可用 | 接 OTLP collector |
| P0-5 | N+1 + MinIO 同步阻塞 | 上线前修复（性能/稳定性） |
