# CampusSphere 生产落地优化建议清单（按优先级）

> 主理人：齐活林 · 汇总自架构/工程/QA 三方审计（01/02/03）
> 日期：2026-08-28 · 适用范围：单校起步 → 公网多校
> 说明：每项含「现状 / 风险 / 改进方向」。优先级 P0（上线前必做）> P1（1-2 迭代）> P2（建议）> P3（长期）。

---

## P0 · 上线前必须解决（安全/稳定硬阻塞）

### P0-1 默认与占位密钥可直接起生产服务
- **现状**：`SECRET_KEY=change-me-...`、`ADMIN_GATEWAY_KEY=change-me-admin-gateway-key-16plus`、`MEILI_API_KEY=masterKey`、`MINIO_ACCESS/SECRET_KEY=minioadmin`、`postgres campus/campus` 为默认值；`docker-compose.yml` 用 `env_file: ./deploy/.env.example` 直接引用，`validate_admin_security` 仅校验长度 ≥16（占位值能通过）。
- **风险**：攻击者可用已知密钥伪造 JWT / 网关令牌、读取对象存储与搜索索引；一键部署即「带病上线」。
- **改进**：密钥经 Secret Manager / K8s Secret / Vault 注入；compose `env_file` 指向真实 `.env`；CI 增加「密钥强度 + 非占位值」校验；启动 fail-fast 扩展到 MinIO/Meili/PG。

### P0-2 全链路无 HTTPS（nginx 跳转被注释）
- **现状**：`deploy/nginx/nginx.conf` 的 `return 301 https://...` 被注释，默认 `listen 80` 明文。
- **风险**：凭证、JWT、验证码在公网被窃听/中间人。
- **改进**：启用 TLS（挂载证书），HTTP 301→HTTPS；HSTS；仅在内网/隧道场景才允许明文。

### P0-3 零 CI/CD，测试/构建/部署全手动
- **现状**：仓库无 `.github/`、`.gitlab-ci.yml`、Jenkinsfile、`.circleci`（已核实）。
- **风险**：回归靠人肉；依赖漂移、密钥误提交无卡点；发布不可复现。
- **改进**：最小 GitHub Actions：`lint → tsc --noEmit → pytest --cov(门禁) → build → 镜像推送 → 部署`；PR 必过；`secrets` 扫描（gitleaks）。

### P0-4 OpenTelemetry 仅 Console 导出，追踪形同虚设
- **现状**：`launcher/otel.py` 用 `ConsoleSpanExporter`，无 OTLP exporter；README 称 OTLP 与实现不符。
- **风险**：生产无分布式追踪，跨服务/跨实例问题无法定位。
- **改进**：`OTLPSpanExporter` + `OTEL_EXPORTER_OTLP_ENDPOINT`；接入 Jaeger/Tempo；保留 FastAPI instrumentation。

### P0-5 性能/稳定性两处硬伤（N+1 + MinIO 同步阻塞）
- **现状**：全模块 `selectinload` 使用数 = **0**；`core/storage.py` 的 `upload_bytes`(async) 内调用同步 `put_object`，阻塞事件循环。
- **风险**：列表/详情接口 N+1 放大 DB 压力；文件上传拖垮整实例吞吐。
- **改进**：列表接口补 `selectinload`/`joinedload`；MinIO 换 `aiominio` 或 `anyio.to_thread.run_sync`；上线前压测。

---

## P1 · 1-2 个迭代内完成（重要加固）

### P1-1 配置硬化：`extra="allow"` 与无 staging
- **现状**：`config.py:32` `Settings(extra="allow")`；dev/prod 仅靠 `DEBUG`+`.env` 区分。
- **风险**：任意环境变量污染配置、扩大攻击面；误配无隔离。
- **改进**：`extra="ignore"`；引入 `ENV=dev|staging|prod` 维度与对应 `.env.staging`；敏感字段集中。

### P1-2 数据库迁移缺乏增量脚本
- **现状**：`alembic/versions/0001_initial.py` 直接 `Base.metadata.create_all`，`down_revision=None`，后续模型演进无迁移。
- **风险**：团队协作 schema 漂移；生产无法安全演进/回滚。
- **改进**：每次模型变更生成增量迁移；`pre-commit` 校验模型与迁移一致；发布流程 `alembic upgrade head` + 备份。

### P1-3 `auth ↔ admin` 循环依赖
- **现状**：`auth/router.py` 顶层 import `admin`，`admin/router.py` 顶层 import `auth`（各 3/1 处），靠惰性 import 暂未崩。
- **风险**：改为顶层 import 即 `ImportError`；模块边界模糊。
- **改进**：抽公共 `admin_auth` 子域或统一经 `auth/deps`；固化为惰性 import 并加架构测试守护。

### P1-4 镜像质量（多阶段/非 root/锁版本/HEALTHCHECK）
- **现状**：`Dockerfile` 单阶段、`python:3.12-slim`、依赖 `pip install` 无锁版本、无 `HEALTHCHECK`；`Dockerfile.worker` 同。
- **风险**：镜像大、构建不可复现、供应链风险、K8s 无就绪探针。
- **改进**：多阶段构建 + 非 root + `HEALTHCHECK`；生成 `uv.lock`/`pip-tools` 约束并 `pip install -r requirements.lock`；`minio:latest` 固定版本。

### P1-5 限流与防爆破不足
- **现状**：网关固定窗口 120/min/IP（`middleware.py`），Redis 缺失时不生效；登录/验证码接口无独立更严限流。
- **风险**：验证码接口可被暴力枚举/刷接口；无 Redis 时限流失效。
- **改进**：登录/发码接口独立限流（如 5 次/10 分）；滑动窗口 + Redis；验证码接口生产强制 SMTP 且**绝不返回明文**。

### P1-6 CORS 过宽
- **现状**：`allow_credentials=True` + `allow_methods/headers=["*"]`（`main.py:81-87`）。
- **风险**：配合凭据暴露，跨站调用面扩大。
- **改进**：生产显式白名单 origins/methods/headers。

### P1-7 全模块对象级越权（IDOR）审计与测试
- **现状**：`item` 模块已正确校验 `owner_id`；`job/share/teammate/report/storage` 等未见统一所有权校验测试。
- **风险**：用户可能改/删/读他人资源（订单、会话、举报、队伍）。
- **改进**：抽象 `require_owner` 依赖统一复用；对全部写/读接口补越权测试（尤其 report 处理、teammate 队伍管理、message 会话）。

### P1-8 测试覆盖补齐（7 模块零测试）
- **现状**：51 测试函数覆盖 ~9/14 模块；`job/share/teammate/report/storage/launcher/ai` 无直接测试；前端无测试。
- **风险**：核心治理/状态机逻辑回归无保障。
- **改进**：优先补 `report`(自动封禁/越权)、`teammate`/`job`(状态机)、`storage`(上传/清理)、`ai`(降级)；前端引入 Vitest；CI 加覆盖率门禁（≥70%）。

### P1-9 连接池与缓存缺位
- **现状**：PG 仅 `pool_pre_ping`，未设 `pool_size`/`max_overflow`；Redis 仅用于限流/黑名单/WS，无业务缓存。
- **风险**：高并发连接耗尽；重复查询压 DB。
- **改进**：按压测调 `pool_size`/`max_overflow`；热点列表/课程/食堂加 Redis 缓存 + 失效策略。

### P1-10 日志落盘与告警缺失
- **现状**：structlog JSON 但散落 `*.log` 无轮转；`deploy/prometheus`/`grafana` 无核实的告警规则。
- **风险**：磁盘打满、故障无告警。
- **改进**：日志轮转/由采集器统一；补齐 Prometheus `rules.yml` + Grafana 看板 + 告警通知（错误率/限流/WS 在线数）。

---

## P2 · 建议项（工程化与体验）

### P2-1 健康检查探针细分
- **现状**：仅 `/health` 单一端点。
- **改进**：liveness/readiness/startup 分离；compose/K8s 用 readiness 决定接流。

### P2-2 前端构建优化
- **现状**：`vite build` 单包，管理后台 recharts 体积大，无懒加载。
- **改进**：路由级 `React.lazy` + 代码分割；管理后台按需分包。

### P2-3 文档与版本声明一致性
- **现状**：README 称 Python 3.11+/Node 18+，pyproject `requires-python>=3.12`，镜像 3.12。
- **改进**：统一为 3.12；补充「支持矩阵」。

### P2-4 仓库卫生与 .gitignore
- **现状**：`backend/` 根散落 `*.log`/`*.txt`/`dev.db`/`pytest-cache-files-*/`；`frontend/metadata.json`、`vite.log` 未忽略。
- **改进**：清理临时文件；忽略 `backend/uploads/`、`pytest-cache-files-*/`、`frontend/vite.log`、`metadata.json`；CI 守卫禁止提交 `.env`/大日志。

### P2-5 依赖漏洞常态化扫描
- **现状**：依赖 `>=` 无上限、无 lockfile、未跑 `pip-audit`/`npm audit`。
- **改进**：锁版本 + 每周 `pip-audit`/`npm audit` 进 CI，高危阻断。

### P2-6 静默异常治理
- **现状**：多处 `except Exception: pass`（seed/ws listener/redis/storage/ws）。
- **改进**：关键降级路径补 `logger.warning` + Prometheus 计数，避免排障盲区。

---

## P3 · 长期演进（架构级）

- **模块化单体 → 按需微服务**：以 `auth`/`admin` 高频耦合点为界，优先抽「通知/搜索索引」异步边界；用现有 service 门面降低拆分量。
- **多校隔离模型**：当前「一份代码 + 一份 school.yaml」适合单实例多租户轻隔离；若多校强隔离需求，引入 tenant_id + schema/库隔离。
- **可观测全栈**：OTel traces + metrics + logs 三联；SLO/错误预算；混沌演练验证 WS 跨实例与 Celery 重试。
- **安全纵深**：WAF、API 网关限流、审计日志防篡改、定期渗透测试。

---

## 落地路线图（建议节奏）

| 阶段 | 周期 | 交付 |
|---|---|---|
| 阶段 0（止血） | 1 周 | P0-1~P0-5：密钥/HTTPS/CI/OTel/性能硬伤 |
| 阶段 1（加固） | 2-3 周 | P1-1~P1-10：配置/迁移/镜像/限流/IDOR/测试/池与缓存/日志告警 |
| 阶段 2（工程化） | 持续 | P2 全项 + P3 启动 |

> 注：本审计的「实测运行」部分（pytest 通过率、ruff 统计、`pip-audit`/`npm audit` 漏洞数、`/health` 实测返回）因沙箱 PyPI 出口网络不稳定、依赖安装未能完成而暂缺，已在 `02` 报告 §4/§10 与 `03` §1/§5.1 标注，并给出复测命令。环境就绪后运行即可补齐。
