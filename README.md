# CampusSphere · 校园生活平台

一站式校园生活服务平台（Python 重写 · 模块化单体架构），覆盖二手交易、课程评价、食堂、兼职、资源共享、队友招募、即时消息、举报与管理后台等核心校园场景，并内置基于 Gemini 的 AI 智能助手。

- **后端**：FastAPI 模块化单体（认证 / 用户 / 二手 / 消息 / 课程 / 食堂 / 兼职 / 分享 / 组队 / 举报 / 管理后台 / 对象存储 / 启动器）
- **前端**：React 19 + TypeScript + Vite，Express 代理层统一转发 `/api` 与 WebSocket
- **多校可配置**：一份代码 + 一份 `config/school.yaml` = 一所学校一键上线

## 功能特性

| 模块 | 说明 |
| --- | --- |
| 账号体系 | 邮箱注册（验证码 + 域名白名单）、统一登录（邮箱 / 手机号 / 自定义账号）、邮箱 / 手机 / QQ / 微信多方式绑定、JWT 双 Token |
| 二手市场 | 发布 / 浏览 / 详情 / 交易会话，**并发安全**（条件 UPDATE 原子抢占 + 活跃会话部分唯一索引 + 状态机校验），支持发布审核策略（后台可切换）、物品描述 AI 代写 |
| 课程中心 | 课程搜索、课程详情、学生评价与 AI 选课摘要，**学部 → 院系两级筛选**（由 `school.yaml` 配置驱动） |
| 食堂 | 食堂列表、档口 / 菜品浏览、评价，**按学部 / 餐饮区 / 类型 / 学期多维度配置化筛选**（模型扩维 + 后台 configs 端点 + seed 脚本） |
| 兼职 | 兼职发布 / 申请、申请状态流转，**分类由后台配置驱动**（与二手/分享/组队同套四层配置模式） |
| 分享圈 | 动态发布、评论、互动，**分类由后台配置驱动** |
| 队友招募 | 组队发帖 / 入队申请、队伍状态管理，**分类由后台配置驱动** |
| 即时消息 | WebSocket 实时私信，Redis 广播，跨实例支持；会话列表 **N+1 合并查询**（窗口函数），历史消息**分页上拉** |
| 举报系统 | 多目标举报（user / item / message / share / comment）、自动封禁策略、工单升级 |
| 管理后台 | 数据看板、举报处理、审核配置、邮箱注册规则动态覆盖 |
| AI 助手 | 校园智能洞察、物品文案生成、课程评价摘要、帖子分类（Gemini 多模型自动兜底，无 Key 时降级为内置文案） |
| 基础设施 | Celery 异步任务、MinIO 对象存储、Meilisearch 全文搜索、OpenTelemetry 可观测、structlog 结构化日志 |
| 演示数据 | `backend/scripts/seed_demo_users.py` 一键灌入 10 个演示账号（`user01`~`user10` / `123456`）及全功能使用记录 |

## 技术栈

- **后端**：Python 3.12+ / FastAPI / SQLAlchemy 2（async）/ pydantic-settings / alembic / Celery / Redis / structlog
- **前端**：React 19 / TypeScript / Vite 6 / Tailwind CSS / Express 5（代理层）/ http-proxy-middleware / @google/genai
- **基础设施**：PostgreSQL 16 / Redis 7 / MinIO / Meilisearch / Nginx
- **可观测**：OpenTelemetry（OTLP）、`/metrics` 指标端点

## 目录结构

```
campusLifePlatform-py/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── core/            # 配置 / 数据库 / Redis / 安全 / 响应 / 异常 / 日志 / 中间件
│   │   ├── common/          # Base / Mixins / 枚举 / 工具
│   │   ├── modules/         # 业务模块（auth / user / item / message / course / canteen / job / share / teammate / report / admin / storage / launcher）
│   │   ├── tasks/           # Celery 异步任务（email / notify / search / default）
│   │   ├── search/          # Meilisearch 客户端
│   │   └── main.py          # 应用工厂（装配路由 / 中间件 / WebSocket / 生命周期）
│   ├── alembic/             # 数据库迁移
│   ├── scripts/             # 开发辅助脚本（seed_demo_users、seed_canteens、fake_redis、API 文档生成等）
│   ├── tests/               # pytest 冒烟测试
│   ├── pyproject.toml
│   └── .env.example
├── frontend/                # React 前端 + Express 代理层
│   ├── pages/               # 16 个业务页面
│   ├── services/            # api.ts / websocket.ts / geminiService.ts
│   ├── server.ts            # Express：/api/ai/* 本地处理 + /api 与 /ws 反代后端
│   ├── vite.config.ts
│   └── package.json
├── config/
│   ├── school.yaml          # 多校配置（校名 / OAuth / 邮箱注册规则 / MinIO / Meili / 审核策略）
│   └── logging.yaml         # 结构化日志配置
├── deploy/
│   ├── docker-compose.yml   # 单校一键起（app + worker + pg + redis + minio + meili + nginx）
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── nginx/
└── docs/                    # 项目文档
    ├── usage.md             # 使用说明（安装 / 配置 / 启动 / 部署）
    ├── development.md       # 开发指南（架构 / 模块 / 规范 / 测试 / 贡献）
    ├── 部署手册.md
    ├── DEPLOYMENT.md        # 初次部署/启动配置清单（环境变量/配置文件/依赖服务/密钥/数据库初始化）
    ├── 项目现状分析.md
    ├── 后续开发计划.md
    ├── API_Reference.md     # 128 个接口端点文档
    └── openapi.json
```

## 快速开始（开发环境）

前置要求：Python 3.12+、Node.js 18+。

### 1. 启动后端（零外部依赖）

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                                # 默认 SQLite，无需任何外部组件
uvicorn app.asgi:app --reload --port 8000           # 自动建表 + 按 config/school.yaml 的 admin 段注入引导管理员
```

验证：<http://localhost:8000/health> 返回 `ok`，API 文档 <http://localhost:8000/docs>。

**一键启停**（推荐）：项目提供跨平台的 `scripts/devctl.py`，取代原先仅 Windows 可用的 `deploy\start_dev.bat`：

```bash
python scripts/devctl.py up          # 启动后端 + 前端，并等待健康检查通过
python scripts/devctl.py status      # 查看各服务监听状态与 PID
python scripts/devctl.py down        # 停止服务并校验端口已释放
python scripts/devctl.py restart     # 先关再启
```

常用参数：`--backend-only` / `--frontend-only` 只操作其中一个；`--wait-timeout N` 调整健康检查等待秒数；`--force` 自动清理占用端口的残留进程；`--mode docker` 改用 `docker compose` 起停整依赖（Postgres / Redis / MinIO / Meili / Nginx）。Windows 下也可直接双击 `scripts\start.bat` / `scripts\stop.bat`。

脚本会把 PID 写入 `.run/`、日志写入 `.run/logs/`（均已加入 .gitignore）。关闭采用「优雅终止 → 超时强杀 → 按端口兜底清理 → 校验端口释放」四步，避免残留进程继续占用 8000 / 5173；启动后若健康检查未通过，会自动回滚本次拉起的服务。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

前端 Express 层将 `/api/*` 与 `/ws` 自动代理到 `http://127.0.0.1:8000`，无需额外配置。

> **端口说明**：后端监听 `127.0.0.1:8000`；前端监听 `5173`（Windows Hyper-V 排除范围会拒绝绑定 3000，且 Node 24 将 `localhost` 解析为 IPv6 `::1`，故代理目标统一使用 `127.0.0.1`）。

### 3. 登录与账号

**普通用户**：登录页提供四种入口——

| 入口 | 账号 | 说明 |
| --- | --- | --- |
| 账号密码登录 | 用户名 / 邮箱 / 手机号 + 密码 | 邮箱注册会自动生成用户名，**用户名与邮箱均可登录**；邮箱忽略大小写 |
| 邮箱验证码注册 | 校园邮箱 + 验证码 | 需先通过滑块验证才能获取验证码；注册成功即自动登录 |
| 手机号验证码登录 | 手机号 + 验证码 | 同上 |
| 用户名注册 | 用户名 + 密码（邮箱选填） | 若填写邮箱，须同样遵守校园邮箱域名规则，不能绕过白名单 |

**微信 / QQ 授权登录暂未开放**：后端已保留 `/api/auth/wechat/*`、`/api/auth/qq/*` 回调接口与绑定 / 解绑能力，待配置应用凭据（AppID / Secret）后即可启用；前端入口点击时仅给出提示，不发起请求。

**管理员**：登录页底部「系统管理后台入口 → 管理员登录」，需依次输入**网关密钥 + 管理员账号 + 密码**（三者均通过 `config/school.yaml` 的 `admin` 段与 `.env` 配置下发，不再硬编码、不再对外暴露）方可进入 `/admin` 管理后台；后端未携带有效网关令牌时 `/api/admin/*` 一律返回 404，避免被探测。

**页面权限分离**：前端按登录身份隔离路由——未登录只能浏览公开内容（首页 / 市场 / 课程 / 食堂 / 分享 / 兼职 / 组队列表，后端列表接口对 GET 开放）；发布、评价、消息、个人中心需普通用户登录（自动跳转 `/login`）；`/admin` 管理后台仅管理员账号可进入，普通用户 token 无法访问任何 `/api/admin/*` 接口。

**演示账号**：执行 `python backend/scripts/seed_demo_users.py` 可一键灌入 10 个演示用户（`user01`~`user10`，密码统一 `123456`，昵称 测试用户一 ~ 十）以及覆盖二手 / 课程 / 食堂 / 兼职 / 分享 / 组队 / 消息 / 举报全部功能的使用记录（脚本幂等，重复执行自动跳过）。食堂与课程数据另由 `backend/scripts/seed_canteens.py`（按 `school.yaml` 的 canteen 段）灌入。

> **验证码说明**：当前默认未配置 SMTP 发送服务，`POST /api/auth/send-code` 的响应会直接返回 `debug_code`，前端注册页自动填入便于联调；生产环境在 `.env` 配置 `SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS` 后，验证码仅通过邮件送达，接口不再返回明文验证码。

### 4. 滑块验证（发送验证码前的防滥用闸门）

为防止脚本恶意刷取验证码、轰炸校园邮箱，请求发送验证码前必须完成一次**滑块拼图验证**：

```
GET  /api/auth/captcha/config   → 是否开启（前端据此决定是否弹窗）
GET  /api/auth/captcha/slider   → 背景图 + 拼图块（base64）+ 令牌
POST /api/auth/captcha/verify   → 校验拖动结果，通过后签发一次性票据
POST /api/auth/send-code        → 携带票据才能真正发送
```

设计要点：

* **缺口横坐标不下发**：只保存在服务端（Redis），响应仅含纵坐标，避免被直接解析绕过；
* **令牌一次性**：校验无论成败立即作废，杜绝反复试探坐标；
* **多重判定**：位置容差（默认 6px）+ 拖动耗时 + 轨迹形态（拦截匀速脚本）；
* **票据一次性**：一次滑块只能换一次发码，防止「一次验证、反复刷码」；
* 图像处理基于 **Pillow**（业界标准库），不依赖第三方验证服务，离线部署同样可用。

可通过 `CAPTCHA_ENABLED=false` 关闭（测试与内网环境），关闭后 `send-code` 不再要求票据。

### 5. 验证码与注册规则

| 项 | 默认值 | 配置键 |
| --- | --- | --- |
| 验证码有效期 | 300 秒 | `CODE_TTL_SECONDS` |
| 验证码最大校验次数 | 5 次（超出即作废，防暴力枚举） | `CODE_MAX_ATTEMPTS` |
| 同一目标发码频率 | 60 秒 1 次 | — |
| 邮箱域名白名单 / 正则 | 见 `config/school.yaml` | 管理后台 `/admin` 可动态覆盖 |
| 滑块容差 / 有效期 / 尝试次数 | 6px / 300s / 3 次 | `CAPTCHA_TOLERANCE_PX`、`CAPTCHA_TTL_SECONDS`、`CAPTCHA_MAX_ATTEMPTS` |

邮箱**统一以小写存储与比对**，用户输入含大写字母也不会出现「收不到验证码」或「登录失败」。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [docs/usage.md](docs/usage.md) | 使用说明：安装步骤、配置项、功能模块使用、生产部署 |
| [docs/development.md](docs/development.md) | 开发指南：架构设计、模块说明、API 约定、测试与贡献 |
| [docs/API_Reference.md](docs/API_Reference.md) | 128 个接口端点的字段级参考 |
| [docs/部署手册.md](docs/部署手册.md) | 生产部署手册 |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 初次部署/启动配置清单：环境变量、配置文件、依赖服务、密钥凭证、数据库初始化与前置条件 |
| [docs/TESTING.md](docs/TESTING.md) | **测试计划**：三层测试范围与工具选型、数据工厂与环境配置、运行方式、CI 门禁、已知缺陷清单 |
| [e2e/README.md](e2e/README.md) | 端到端测试：8 个场景清单、页面对象模式、运行与调试方式 |
| [docs/项目现状分析.md](docs/项目现状分析.md) | 项目现状与结构分析 |
| [docs/后续开发计划.md](docs/后续开发计划.md) | 开发路线图 |
| [docs/配置方案_2026-09-04.md](docs/配置方案_2026-09-04.md) | 配置化改造方案（食堂 / 课程院系 / 分类四层 / 消息历史 / 并发加固），已全部落地 |
| [docs/REFACTOR_DELIVERABLE.md](docs/REFACTOR_DELIVERABLE.md) | 后端深改交付文档（权限作用域 / 规则引擎 / 任务隔离 / 配置热更新 / WS 补发 / 可观测 + P0-P4 迭代） |
| [docs/架构与面试备战白皮书.md](docs/架构与面试备战白皮书.md) | 项目架构设计与核心难点攻克（面试向） |
| [docs/模块级技术白皮书与面试备战手册.md](docs/模块级技术白皮书与面试备战手册.md) | 模块级技术拆解与面试备战手册 |

> 文档与代码的一致性由 `scripts/doc_sync.py` 自动比对：运行后生成 `docs/_generated/PROJECT_STATUS.md`（项目状态快照）与 `DOC_DRIFT_REPORT.md`（漂移清单），`--check` 可作 CI 卡点，`--sync-env-example` 可自动补全 `backend/.env.example` 缺失的部署配置键。

## 测试

采用**单元测试 / 集成测试 / 端到端测试**三层体系，共 **373 个后端用例 + 14 个前端组件用例 + 8 个端到端场景**。
完整测试计划见 **[docs/TESTING.md](docs/TESTING.md)**。

```bash
# ── 后端（零外部依赖：临时 SQLite + Redis/MinIO/Meili 内存降级）──
cd backend
pytest tests/unit -q                     # 单元层：纯函数与模块逻辑，~3s
pytest tests/integration -q              # 集成层：API + 数据库 + mock 外部服务，~3min
pytest tests --ignore=tests/unit --ignore=tests/integration -q   # 既有回归用例，~3min

# 覆盖率（用 coverage run --append 累加，避免并行数据文件的删除问题）
coverage run -m pytest tests/unit -q
coverage run --append -m pytest tests/integration -q
coverage report --fail-under=70          # 当前实测 70%

# ── 前端组件测试（Vitest + React Testing Library）──
cd frontend
npm run test                             # 单次运行
npm run test:coverage                    # 覆盖率报告

# ── 端到端测试（Playwright，自动拉起前后端）──
cd e2e
npm install && npx playwright install chromium
npm test                                 # 8 个核心用户旅程场景
```

> **建议按层分进程执行**：把全部后端用例放进同一个 pytest 进程时，
> Windows 上偶发 `aiosqlite` 后台连接线程的原生 Abort（进程直接退出）。
> 分层跑可彻底规避，详见 `docs/TESTING.md` §8.1。

### 分层与目录

| 层 | 位置 | 覆盖内容 |
| --- | --- | --- |
| **单元** | `backend/tests/unit/` | 滑块验证码（生成/反脚本/票据一次性）、安全工具（密码哈希、JWT 签发解析、jti 吊销）、通用工具（校验/脱敏/分页/类型转换） |
| **单元** | `frontend/__tests__/` | `SliderCaptcha` 拖动交互与失败重试、`ProtectedRoute`/`PublicOnlyRoute`/`AdminRoute` 三个路由守卫的重定向行为 |
| **集成** | `backend/tests/integration/test_auth/` | 邮箱注册全链路（滑块 → 验证码 → 注册即登录）、重复邮箱/域名白名单/错误码；登录双 Token、错误分支、刷新与注销吊销 |
| **集成** | `.../test_items/` | 发布 → 列表可见 → 详情 → 下架 → 删除；议价会话创建与越权隔离 |
| **集成** | `.../test_course/`、`test_canteen/` | 课程搜索与评价、食堂档口菜品评分，含跨课程/菜品的数据隔离 |
| **集成** | `.../test_messaging/` | WebSocket 消息落库与越权拒绝 |
| **集成** | `.../test_admin/` | 管理员登录、举报列表、封禁/解封 |
| **集成** | `.../test_external/` | 邮件任务参数、AI（Gemini）mock 与降级、对象存储上传回读、搜索索引同步与降级 |
| **端到端** | `e2e/tests/` | 首页浏览、注册、登录会话、未登录重定向、发布与议价、即时消息、管理后台、课程评价 |

测试数据由 `backend/tests/factories.py`（factory_boy）生成，
每个用例跑在 `drop_all + create_all` 重建的干净库上，无需手动回滚。

生命周期测试通过 `conftest.lifecycle_env` 把全局 engine / SessionLocal 重定向到临时库，因此可以安全地跑完整 lifespan——而常规 `client` fixture 为提速刻意跳过了 lifespan。

## 生产部署

一条命令拉起全部服务（app + worker + PostgreSQL + Redis + MinIO + Meilisearch + Nginx）：

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env.example up -d
```

详细步骤见 [docs/usage.md](docs/usage.md#生产部署) 与 [docs/部署手册.md](docs/部署手册.md)。

## 贡献方式

欢迎参与贡献，流程如下：

1. 阅读 [docs/development.md](docs/development.md) 了解架构与代码规范；
2. 在 [docs/后续开发计划.md](docs/后续开发计划.md) 中选择一个待办项，或在 Issue 中认领任务；
3. Fork 仓库并创建功能分支：`git checkout -b feat/xxx`；
4. 遵循现有代码风格（Python：ruff + `black` 风格；TypeScript：prettier），补充/更新测试；
5. 本地跑通 `pytest -q` 与 `npm run lint` 后提交 Pull Request，描述变更与验证结果。

代码提交信息建议使用约定式提交（`feat:` / `fix:` / `docs:` / `refactor:` 等）。

## License

内部项目，尚未指定开源许可证。
