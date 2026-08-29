# CampusSphere · 校园生活平台

一站式校园生活服务平台（Python 重写 · 模块化单体架构），覆盖二手交易、课程评价、食堂、兼职、资源共享、队友招募、即时消息、举报与管理后台等核心校园场景，并内置基于 Gemini 的 AI 智能助手。

- **后端**：FastAPI 模块化单体（认证 / 用户 / 二手 / 消息 / 课程 / 食堂 / 兼职 / 分享 / 组队 / 举报 / 管理后台 / 对象存储 / 启动器）
- **前端**：React 19 + TypeScript + Vite，Express 代理层统一转发 `/api` 与 WebSocket
- **多校可配置**：一份代码 + 一份 `config/school.yaml` = 一所学校一键上线

## 功能特性

| 模块 | 说明 |
| --- | --- |
| 账号体系 | 邮箱注册（验证码 + 域名白名单）、统一登录（邮箱 / 手机号 / 自定义账号）、邮箱 / 手机 / QQ / 微信多方式绑定、JWT 双 Token |
| 二手市场 | 发布 / 浏览 / 详情 / 交易会话，支持发布审核策略（后台可切换）、物品描述 AI 代写 |
| 课程中心 | 课程搜索、课程详情、学生评价与 AI 选课摘要 |
| 食堂 | 食堂列表、档口 / 菜品浏览、评价 |
| 兼职 | 兼职发布 / 申请、申请状态流转 |
| 分享圈 | 动态发布、评论、互动 |
| 队友招募 | 组队发帖 / 入队申请、队伍状态管理 |
| 即时消息 | WebSocket 实时私信，Redis 广播，跨实例支持 |
| 举报系统 | 多目标举报、自动封禁策略、工单升级 |
| 管理后台 | 数据看板、举报处理、审核配置、邮箱注册规则动态覆盖 |
| AI 助手 | 校园智能洞察、物品文案生成、课程评价摘要、帖子分类（Gemini 多模型自动兜底，无 Key 时降级为内置文案） |
| 基础设施 | Celery 异步任务、MinIO 对象存储、Meilisearch 全文搜索、OpenTelemetry 可观测、structlog 结构化日志 |

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
│   ├── scripts/             # 开发辅助脚本（fake_redis、API 文档生成等）
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
    ├── API_Reference.md     # 88 个接口文档
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
| [docs/API_Reference.md](docs/API_Reference.md) | 88 个接口的字段级参考 |
| [docs/部署手册.md](docs/部署手册.md) | 生产部署手册 |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 初次部署/启动配置清单：环境变量、配置文件、依赖服务、密钥凭证、数据库初始化与前置条件 |
| [docs/项目现状分析.md](docs/项目现状分析.md) | 项目现状与结构分析 |
| [docs/后续开发计划.md](docs/后续开发计划.md) | 开发路线图 |

> 文档与代码的一致性由 `scripts/doc_sync.py` 自动比对：运行后生成 `docs/_generated/PROJECT_STATUS.md`（项目状态快照）与 `DOC_DRIFT_REPORT.md`（漂移清单），`--check` 可作 CI 卡点，`--sync-env-example` 可自动补全 `backend/.env.example` 缺失的部署配置键。

## 测试

```bash
# 后端完整测试套件（零外部依赖：测试库为临时 SQLite，Redis/MinIO/Meili 走内存降级）
cd backend && pytest -q

# 只看生命周期与资源释放相关用例
pytest tests/test_lifecycle.py tests/test_shutdown_resources.py -v

# 前端类型检查
cd frontend && npm run lint        # tsc --noEmit
```

测试套件分层：

| 文件 | 覆盖内容 |
| --- | --- |
| `tests/test_lifecycle.py` | 应用启动 / 关闭全生命周期：健康检查、seed 幂等、DB 引擎释放、Redis 客户端关闭、WS 监听任务取消；边界含弱密钥拒绝启动、Redis 不可用降级启动、启动中途失败仍释放资源 |
| `tests/test_shutdown_resources.py` | 关闭期资源释放专项：三类资源释放完整性、释放顺序（后台任务 → 外部连接 → 连接池）、单环节失败不阻断后续释放、幂等性与旧版 Redis 客户端兼容 |
| `tests/test_e2e_flow.py` | 端到端主流程：注册登录 → 发布 → 浏览 → 议价会话 → 下架 → 删除，覆盖跨模块协作（item → message、课程 / 食堂）与越权拦截 |
| 其余 `tests/test_*.py` | 按模块划分的用例：认证、用户、物品、发布审核、消息、WebSocket、管理端网关、架构约束等 |

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
