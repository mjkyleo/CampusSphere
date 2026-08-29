# CampusSphere 启动验证与代码质量审计

> 主理人：齐活林 · 工程师：寇豆码
> 分析日期：2026-08-28 · 代码基：本地 `main`

---

## 0. 实测环境说明（重要）

本审计报告在**隔离沙箱**中完成。仓库自带 `backend/.venv` 此前**未安装任何业务依赖**（仅含 pip 自身），需联网 `pip install -e ".[dev]"`。沙箱 PyPI 出口可达，但首次无缓存解析 + 下载较慢，安装耗时较长。

- **已验证**：目录结构、配置项、依赖降级路径、代码静态走查、`.gitignore` 覆盖、跨模块依赖、关键鉴权写法（item/message/admin）、Docker/compose/nginx 配置——均为**直接读代码结论**。
- **待安装完成后补测**：`uvicorn` 实际启动、`pytest` 通过率、`ruff` 问题统计、`pip-audit` 漏洞清单（安装任务后台进行中，完成后将补齐「实测结果」小节并标注实测输出）。

> 下述「启动步骤」与「降级行为」依据代码路径（`main.py` lifespan、`database.init_models`、`redis.get_redis` 兜底、`storage.StorageClient` 兜底、`config.validate_admin_security`）给出，逻辑上可零外部依赖启动。

---

## 1. 环境要求（实测结论）

| 组件 | 开发（零依赖） | 生产 | 是否必需 |
|---|---|---|---|
| Python | 3.12+（README/usage 已统一）/ `requires-python>=3.12`（pyproject） | 3.12（镜像 `python:3.12-slim`） | 必需 |
| Node.js | 18+（README）| 22（构建期） | 前端必需 |
| PostgreSQL | 不需要（默认 SQLite） | 16 | 生产必需 |
| Redis | 不需要（内存兜底） | 7 | 推荐（限流/黑名单/WS 广播/Celery） |
| MinIO | 不需要（本地磁盘兜底） | 可选 | 对象存储必需（或用 S3） |
| Meilisearch | 不需要（DB like 兜底） | v1.11 | 搜索必需 |
| SMTP | 不需要（返回 debug_code） | 必需（验证码邮件） | 注册验证码必需 |
| Gemini API Key | 不需要（AI 入口隐藏） | 可选 | AI 功能必需 |

**版本声明已统一**：`README.md` 与 `usage.md` 现已统一为「Python 3.12+」，与 `pyproject.toml` 的 `requires-python>=3.12` 及镜像 `python:3.12-slim` 一致，首次部署者不会因版本错配踩坑。

---

## 2. 配置项全清单

来源：`backend/app/core/config.py`、`backend/.env(.example)`、`config/school.yaml`、`deploy/.env.example`。

| 配置项 | 环境变量 | 必填(生产) | 默认值 | 敏感级 | 说明 |
|---|---|---|---|---|---|
| 应用名 | `APP_NAME` | 否 | campus-life-platform | - | |
| 调试 | `DEBUG` | 否 | false | - | true 时跳过管理员安全强校验 |
| 数据库 | `DB_URL` | **是** | sqlite+aiosqlite:///./dev.db | 中 | 生产用 postgresql+asyncpg |
| Redis | `REDIS_URL` | 否 | redis://localhost:6379/0 | 低 | 缺省内存兜底 |
| JWT 密钥 | `SECRET_KEY` | **是** | `change-me-to-a-long-random-string-in-prod` | **高** | 默认占位值；HS256 |
| JWT 算法 | `JWT_ALGORITHM` | 否 | HS256 | - | |
| 访问令牌时长 | `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | 15 | - | |
| 刷新令牌时长 | `REFRESH_TOKEN_EXPIRE_DAYS` | 否 | 7 | - | |
| 限流 | `RATE_LIMIT_PER_MINUTE` | 否 | 120 | - | 单实例固定窗口 |
| 网关密钥 | `ADMIN_GATEWAY_KEY` | **是** | `change-me-admin-gateway-key-16plus` | **高** | 生产需 ≥16 随机；缺失/过短启动即退出 |
| 网关强制 | `ADMIN_GATEWAY_ENFORCE` | 否 | true | - | false 时免网关令牌（仅本地） |
| 引导管理员账号 | `ADMIN_BOOTSTRAP_USERNAME` | 否 | siteadmin | 中 | |
| 引导管理员密码 | `ADMIN_BOOTSTRAP_PASSWORD` | **是** | `change-me-deploy-with-strong-pw-16plus` | **高** | 生产需 ≥16 位，否则启动退出 |
| SMTP | `SMTP_HOST/PORT/USER/PASS` | 否(开发) | 空 | **高** | 缺省验证码接口返回明文 debug_code |
| CORS | `CORS_ORIGINS` | 否 | 5173 本地 | 中 | 含 credentials=true |
| 多校配置 | `SCHOOL_CONFIG_PATH` | 否 | ../config/school.yaml | - | |
| MinIO | `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET/SECURE` | 否 | localhost:9000 / minioadmin/minioadmin | **高** | 默认弱口令 |
| Meilisearch | `MEILI_HOST/MEILI_API_KEY` | 否 | localhost:7700 / `masterKey` | **高** | 默认弱密钥 |
| Celery | `CELERY_BROKER_URL/RESULT_BACKEND` | 否 | redis db1/db2 | 低 | |
| Gemini | `GEMINI_API_KEY`(env) / `ai.api_key`(yaml) | 否 | 空 | **高** | 仅后端持有，前端无硬编码 |

**敏感信息暴露评估**：
- `backend/.env` 已被 `.gitignore` 忽略（实测 `git ls-files` 无 `.env`），**未入库**，这是正确的。
- 但 `deploy/.env.example` 与 `config/school.yaml` 内含**明文占位弱密钥**（`masterKey`、`minioadmin/minioadmin`、`change-me-*`），并被 `docker-compose` 的 `env_file: ./deploy/.env.example` 直接引用——见 §9 / 03 报告「部署安全」。

---

## 3. 可复现启动步骤（从零）

### 后端（开发，零依赖）
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate        # Windows
pip install -e ".[dev]"
cp .env.example .env                                   # 默认 SQLite，无需任何外部组件
uvicorn app.asgi:app --reload --port 8000              # 自动建表 + 注入引导管理员
# 验证
curl http://127.0.0.1:8000/health        # -> {"status":"ok"} (实际返回 "ok"? 见实测)
curl http://127.0.0.1:8000/docs          # Swagger
```

### 前端（开发）
```bash
cd frontend
npm install
npm run dev                                          # http://localhost:5173
# Express 代理层将 /api/* 与 /ws 反代 127.0.0.1:8000
```

### 一键启动（Windows）
```bat
deploy\start_dev.bat     # 自动清理 8000/5173 残留进程，启动前后端并等待健康检查
```

### 生产（Docker）
```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env.example up -d
```

---

## 4. 启动验证结果（待安装完成后补测）

> 安装任务 `BeXypG` 后台进行中。完成后将在此填入：`/health` 实际返回体、`/openapi.json` 接口数（README 称 73）、uvicorn 启动日志是否有告警、前端 `/api` 代理连通性实测。

**代码路径预期**（来自 `main.py`）：
- lifespan 中 `validate_admin_security()`：本仓库 `backend/.env` 设 `ADMIN_GATEWAY_ENFORCE=false` → 跳过强校验，可启动；若用生产 `.env.example`（`enforce=true`）且密钥为占位值 → **启动即 SystemExit**，符合 fail-fast 设计。
- SQLite 模式 `init_models()` 执行 `create_all` + 手工 ALTER 补列（仅 SQLite）。
- `manager.start_listener()` 异常被吞（`except Exception: pass`）→ 无 Redis 时静默降级。

---

## 5. 可选组件降级行为矩阵

| 组件 | 缺失时行为 | 代码位置 | 风险 |
|---|---|---|---|
| Redis | 内存字典兜底，限流/黑名单/WS 广播降级为单实例 | `core/redis.py` | 多实例下限流失效、黑名单不跨实例、WS 不跨实例 |
| MinIO | 本地 `uploads/` 磁盘存储 | `core/storage.py` | 多实例文件不共享；无对象生命周期管理 |
| Meilisearch | 列表查询回退 DB `like` | `item/router.search` | 搜索体验降级，无中文分词 |
| SMTP | 验证码接口返回 `debug_code` 明文 | auth 模块 | **开发便利但生产若未配会泄露验证码** |
| Gemini | AI 入口隐藏、接口抛错 | `ai` 模块 | 无 |

---

## 6. 目录结构评价 + .gitignore 缺口

- `backend/` 根目录存在大量**排障/临时文件**已散落：`celery_worker.log`、`fake_redis.log`、`uvicorn.log`、`uvicorn_run.log`、`dev.db`、多个 `*.txt`（`check_imports.txt`、`pip_install.txt`、`pytest_collect.txt` 等）、`ruff_out.txt`。这些**不应常驻仓库**。`ruff_out.txt` 被 `.gitignore` 忽略，但 `*.log` 中 `uvicorn.log`、`celery_worker.log`、`fake_redis.log`、`uvicorn_run.log`、`uvicorn_smoke*.log` 也被忽略（`.log` 规则覆盖），`dev.db` 被忽略（好）。`check_imports.txt`/`pip_install*.txt`/`pytest_collect.txt`/`pytest_ver.txt` 被忽略。但 `backend/README.md`、`backend/pytest-cache-files-trjnhvje/` 未被忽略——后者是 pytest 缓存目录的异常命名（正常应为 `.pytest_cache/`），建议清理并加忽略。
- 前端 `frontend/` 有 `dev_log.txt`/`dev_err.txt`（被忽略）、`vite.log`、`metadata.json`（未被忽略，可能含构建元数据，建议确认是否需入库）。
- **建议**：增加 `backend/uploads/`、`*.log` 已覆盖；补充忽略 `backend/pytest-cache-files-*/`、`frontend/vite.log`、`frontend/metadata.json`；CI 加「禁止提交 `.env`/大日志」守卫。

---

## 7. 代码质量（静态）

### 7.1 ruff（待补测）
> 安装完成后运行 `.venv/Scripts/python.exe -m ruff check app` 并统计。已知 `backend/` 下历史 `ruff_out.txt` 存在（已被忽略），说明团队曾跑过。

### 7.2 静态坏味道（已读代码确认）
1. **广泛 `except Exception: pass` / 静默吞异常**：`main.py`(admin_seed、ws listener)、`redis.get_redis`、`storage._ensure_minio`、`ws._redis_listen`、`message/ws` 多处。部分为合理降级，但缺日志级别统一与可观测性，排障困难。
2. **`Settings(extra="allow")`**（`config.py:32`）：放开任意环境变量注入，易被误设污染配置、增加攻击面。
3. **Dockerfile 依赖未锁版本**：`pip install fastapi "uvicorn[standard]" ...` 无版本约束、无 `requirements.lock`/`uv.lock` → 构建不可复现、供应链风险。
4. **`requires-python` 与 README 不一致**（见 §1）。
5. **`auth ↔ admin` 循环依赖**（见 01 报告 §5.3），属潜在导入炸弹。
6. **生产库依赖 `Base.metadata.create_all`**（alembic 仅 1 个基线迁移 `0001_initial` 直接 `create_all`）：模型演进不会产生增量迁移脚本，团队协作时 schema 漂移风险高；且 `down_revision=None` 无法回滚。

### 7.3 前端类型检查（待补测）
> `frontend` 无测试框架；`npm run lint` = `tsc --noEmit`。待 `npm install` 后运行。

---

## 8. 功能完整度核对（README 声称 vs 代码）

| README 声称 | 代码核实 | 结论 |
|---|---|---|
| 邮箱注册 + 域名白名单 + 验证码 | `auth` 模块 + `school.yaml auth.email_register` | ✅ 已实现 |
| 多方式绑定（邮箱/手机/QQ/微信） | `auth/oauth.py`、`auth/service` | ✅ 基本实现 |
| JWT 双 Token + 黑名单 | `core/security.py` revoke/is_revoked | ✅ 已实现 |
| 二手市场 + 发布审核策略 + AI 文案 | `item` 模块 + `ai` | ✅ 已实现；审核策略可后台切换 |
| 课程评价 + AI 摘要 | `course` + `ai/summarizeCourseReviews` | ✅ |
| 食堂档口菜品评价 | `canteen` | ✅ |
| 兼职申请状态机 | `job` | ✅ |
| 分享圈 | `share` | ✅ |
| 组队 | `teammate` | ✅ |
| WebSocket 私信 + Redis 跨实例 | `message/ws.py` pub/sub | ✅ 已实现（降级单实例） |
| 举报 + 自动封禁 + 工单升级 | `report` + Celery | ✅ |
| 管理后台（看板/审核/配置） | `admin`（1129 LOC） | ✅ 较完整 |
| AI 助手（Gemini 多模型兜底） | `ai` 模块 | ✅ 开关受控，无 Key 降级 |
| 对象级越权防护（item 示例） | `item/router` 校验 owner_id | ✅ 示例良好，需全模块统一 |

**未发现「宣称无、代码有」或「宣称有、代码无」的重大缺口**；README 与实现整体一致，属高质量原型。

---

## 9. 现存问题清单（工程师视角）

| 严重度 | 问题 | 位置 | 建议 |
|---|---|---|---|
| 高 | 生产 compose 直接用 `deploy/.env.example`（占位弱密钥）起服务 | docker-compose.yml:52-53 | 强制使用真实 `.env`，CI 校验密钥强度 |
| 高 | 版本声明不一致（3.11 vs 3.12） | README / pyproject | 统一为 3.12 |
| 中 | 静默吞异常过多 | 多处 | 统一日志 + 关键路径告警 |
| 中 | Dockerfile 依赖未锁版本 | Dockerfile / Dockerfile.worker | 生成 lockfile，固定版本 |
| 中 | alembic 仅基线 `create_all`，无增量迁移 | alembic/versions | 模型变更必须出迁移脚本 |
| 中 | `auth↔admin` 循环依赖 | auth/router, admin/router | 抽公共 `admin_auth` 或惰性 import 固化 |
| 低 | 仓库散落临时/日志文件 | backend/ 根 | 清理 + 完善 .gitignore |
| 低 | `Settings(extra="allow")` | config.py | 改为 `extra="ignore"` 或显式白名单 |

---

## 10. 实测结果（安装完成后回填）
_（待 `BeXypG` 完成，运行 `pytest` / `ruff` / `uvicorn` 后补充）_
