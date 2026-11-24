# CampusSphere

一站式校园生活服务平台（Python 重写 · 模块化单体架构），覆盖二手交易、课程评价、食堂、兼职、资源共享、队友招募、即时消息、举报与管理后台等核心校园场景，并内置可开关、可降级的 AI 能力（OpenAI 兼容模型接入，未配置 Key 时前端自动隐藏入口、主流程零阻塞）。

一站式校园生活服务平台：二手交易、课程评价、食堂、兼职、组队、即时消息与管理后台，内置可开关的 AI 能力。

CampusSphere 是一套面向高校的模块化单体校园生活平台（Python 重写），以「一份代码 + 一份 `config/school.yaml`」支撑单校一键上线。覆盖二手交易、课程评价、食堂、兼职、资源共享、队友招募、即时消息、举报与管理后台等核心场景，并通过可开关、可降级的 AI 能力（OpenAI 兼容模型接入）增强体验——未配置模型 Key 时前端按 `/api/ai/status` 自动隐藏入口，主流程零阻塞。

## 目录

- [背景](#背景)
  - [动机](#动机)
  - [功能特性](#功能特性)
  - [技术栈](#技术栈)
  - [参见](#参见)
- [安装](#安装)
  - [前置要求](#前置要求)
  - [后端](#后端)
  - [前端](#前端)
  - [依赖](#依赖)
  - [目录结构](#目录结构)
- [使用](#使用)
  - [开发环境启动](#开发环境启动)
  - [示例](#示例)
  - [命令行（devctl）](#命令行devctl)
  - [测试](#测试)
  - [生产部署](#生产部署)
- [API](#api)
- [安全](#安全)
- [维护者](#维护者)
- [贡献](#贡献)
- [许可](#许可)

## 背景

### 动机

高校师生的校园生活需求高度分散：二手交易、课程评价、食堂探店、兼职信息、组队招募各自为政。CampusSphere 将这些场景统一到同一个产品内，并通过「多校可配置」设计（`config/school.yaml` 驱动校名、OAuth、邮箱注册规则、审核策略、分类体系等），让同一份代码可以快速适配不同学校。

### 功能特性

| 模块 | 说明 |
| --- | --- |
| 账号体系 | 邮箱注册（验证码 + 域名白名单）、统一登录（邮箱 / 手机号 / 自定义账号）、邮箱 / 手机 / QQ / 微信多方式绑定、JWT 双 Token |
| 二手市场 | 发布 / 浏览 / 详情 / 交易会话，**并发安全**（条件 UPDATE 原子抢占 + 部分唯一索引 + 状态机校验），支持发布审核策略（后台可切换）、物品描述 AI 代写、完整的交易生命周期（完成 / 取消 + 参与者校验） |
| 课程中心 | 课程搜索、课程详情、学生评价与 AI 选课摘要，**学部 → 院系两级筛选**（由 `school.yaml` 配置驱动） |
| 食堂 | 食堂列表、档口 / 菜品浏览、评价，**按学部 / 餐饮区 / 类型 / 学期多维度配置化筛选**（模型扩维 + 后台 configs 端点 + seed 脚本） |
| 兼职 | 兼职发布 / 申请、申请状态流转，**分类由后台配置驱动**（与二手/分享/组队同套四层配置模式） |
| 分享圈 | 动态发布、评论、互动，**分类由后台配置驱动** |
| 队友招募 | 组队发帖 / 入队申请、队伍状态管理（含结队关闭），**分类由后台配置驱动** |
| 即时消息 | WebSocket 实时私信，Redis 广播，跨实例支持；会话列表 **N+1 合并查询**（窗口函数），历史消息**分页上拉** |
| 举报系统 | 多目标举报（user / item / message / share / comment）、自动封禁策略、工单升级 |
| 管理后台 | 数据看板、举报处理、审核配置、邮箱注册规则动态覆盖、管理操作审计日志（audit 模块） |
| AI 助手 | 校园智能洞察、物品文案生成、课程评价摘要、帖子分类、首页趣味问候；OpenAI 兼容模型接入，三层降级（开关 → 能力级 → 模型链 + 熔断），未配置 Key 时主流程零阻塞、前端按 `/api/ai/status` 能力级状态自动隐藏入口；UGC 提示注入防护 |
| 基础设施 | Celery 异步任务、MinIO 对象存储（对象键信任链校验）、Meilisearch 全文搜索（写侧增量同步 + 全量重建脚本 `reindex_search.py`）、OpenTelemetry 可观测、structlog 结构化日志 |
| 演示数据 | `backend/scripts/seed_demo_users.py` 一键灌入 10 个演示账号（`user01`~`user10` / `123456`）及全功能使用记录 |

### 技术栈

- **后端**：Python 3.12+ / FastAPI / SQLAlchemy 2（async）/ pydantic-settings / alembic / Celery / Redis / structlog
- **前端**：React 19 / TypeScript / Vite 6 / Tailwind CSS / Express 5（代理层）/ http-proxy-middleware
- **基础设施**：PostgreSQL 16 / Redis 7 / MinIO / Meilisearch / Nginx
- **可观测**：OpenTelemetry（OTLP）、`/metrics` 指标端点

### 参见

- 详细架构与设计见 [docs/development.md](docs/development.md)
- 全链路拆解与技术亮点见 [docs/全链路深度拆解与技术亮点.md](docs/全链路深度拆解与技术亮点.md)
- 项目现状与结构分析见 [docs/项目现状分析.md](docs/项目现状分析.md)

## 安装

### 前置要求

- Python 3.12+
- Node.js 18+
- （完整依赖栈）PostgreSQL 16、Redis 7、MinIO、Meilisearch、Nginx —— 开发模式可全部省略，使用 SQLite + 内存降级

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                                      # 默认 SQLite，无需任何外部组件
uvicorn app.asgi:app --reload --port 8000                # 自动建表 + 按 config/school.yaml 注入引导管理员
```

启动后访问 <http://localhost:8000/health> 返回 `ok`，API 文档见 <http://localhost:8000/docs>。

### 前端

```bash
cd frontend
npm install
npm run dev                                               # http://localhost:5173
```

前端 Express 代理层将 `/api/*` 与 `/ws` 自动转发至 `http://127.0.0.1:8000`，无需额外配置。

### 依赖

开发模式下后端零外部依赖：运行与测试使用临时 SQLite，Redis / MinIO / Meilisearch 走代码内建的内存降级。生产模式需要下述服务，推荐使用 Docker Compose 一键拉起（见[生产部署](#生产部署)）：

- PostgreSQL 16
- Redis 7
- MinIO（对象存储）
- Meilisearch（全文搜索，可选；缺省时回退 SQL LIKE）

### 目录结构

```
campusLifePlatform-py/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── core/            # 配置 / 数据库 / Redis / 安全 / 响应 / 异常 / 日志 / 中间件
│   │   ├── common/          # Base / Mixins / 枚举 / 工具
│   │   ├── modules/         # 业务模块（auth / user / item / message / course / canteen / job / share / teammate / report / admin / storage / launcher）
│   │   ├── tasks/           # Celery 异步任务（email / notify / search / default）
│   │   ├── search/          # Meilisearch 客户端
│   │   └── main.py          # 应用工厂
│   ├── alembic/             # 数据库迁移
│   ├── scripts/             # 开发辅助脚本（seed、API 文档生成等）
│   ├── tests/               # pytest 三层测试
│   ├── pyproject.toml
│   └── .env.example
├── frontend/                # React 前端 + Express 代理层
│   ├── pages/               # 16 个业务页面
│   ├── services/            # api.ts / websocket.ts / aiService.ts（统一 AI 客户端，含能力级 gating）
│   ├── server.ts            # Express：仅作 /api 与 /ws 反代（AI 由后端统一处理，前端不直连大模型）
│   ├── vite.config.ts
│   └── package.json
├── config/
│   ├── school.yaml          # 多校配置
│   └── logging.yaml         # 结构化日志配置
├── deploy/                  # docker-compose.yml / Dockerfile / nginx
├── e2e/                     # Playwright 端到端测试
└── docs/                    # 项目文档
```

## 使用

### 开发环境启动

推荐使用跨平台的一键启停脚本 `scripts/devctl.py`（取代仅 Windows 的 `deploy/start_dev.bat`）：

```bash
python scripts/devctl.py up          # 启动后端 + 前端，等待健康检查通过
python scripts/devctl.py status      # 查看监听状态与 PID
python scripts/devctl.py down        # 停止并校验端口释放
python scripts/devctl.py restart     # 先关再启
```

常用参数：`--backend-only` / `--frontend-only` 只操作其一；`--wait-timeout N` 调整健康检查等待；`--force` 清理占用端口的残留进程；`--mode docker` 改用 `docker compose` 起停整依赖栈。Windows 也可直接双击 `scripts/start.bat` / `scripts/stop.bat`。脚本将 PID 与日志写入 `.run/`（已 gitignore），关闭采用「优雅终止 → 超时强杀 → 端口兜底清理 → 校验释放」四步。

### 示例

**1. 健康检查**

```bash
curl http://127.0.0.1:8000/health
# => {"status":"ok"}
```

**2. 灌入演示数据**（10 个账号 `user01`~`user10`，密码 `123456`，脚本幂等）

```bash
python backend/scripts/seed_demo_users.py
```

**3. 普通用户登录获取 Token**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"account":"user01","password":"123456"}'
# => {"code":0,"data":{"access_token":"<jwt>","refresh_token":"<jwt>","token_type":"bearer"}}
```

**4. 携带 Token 调用业务接口**

```bash
curl http://127.0.0.1:8000/api/items \
  -H 'Authorization: Bearer <access_token>'
```

**5. 管理员登录**（独立页 `/admin/login`，需网关密钥 + 账号 + 密码）

- 生产流程：`POST /api/admin/discover`（携带 `gateway_key`）换取 `X-Admin-Gateway` 短时令牌，再在 `/api/admin/*` 请求头携带该令牌与 `Authorization: Bearer <access>`。
- 未携带有效网关令牌时，`/api/admin/*` 一律返回 404，避免被探测。
- dev 环境下 `ADMIN_GATEWAY_ENFORCE=false`，网关校验直通，可直接用 `.env` 中的引导账号登录。

> **验证码说明**：默认未配置 SMTP 时，`POST /api/auth/send-code` 会直接返回 `debug_code` 便于联调；生产在 `.env` 配置 `SMTP_*` 后仅通过邮件送达。发送验证码前需完成滑块拼图验证（接口 `GET /api/auth/captcha/slider` → `POST /api/auth/captcha/verify` → `POST /api/auth/send-code`）。

### 命令行（devctl）

`scripts/devctl.py` 是项目统一启停入口，支持以下子命令：

| 命令 | 作用 |
| --- | --- |
| `up` | 启动后端 + 前端并等待健康检查 |
| `down` | 停止服务并校验端口释放 |
| `status` | 查看各服务监听状态与 PID |
| `restart` | 先关再启 |

参数：`-b/--backend-only`、`-f/--frontend-only`、`--wait-timeout N`、`--force`、`--mode docker`。

### 测试

项目采用单元测试 / 集成测试 / 端到端测试三层体系，共 **373 个后端用例 + 14 个前端组件用例 + 8 个端到端场景**（后端用例数来自 `pytest --collect-only`；源码含 342 个 `def test_`，差值来自 `parametrize` 展开）。完整测试计划见 [docs/TESTING.md](docs/TESTING.md)。

```bash
# 后端（零外部依赖：临时 SQLite + Redis/MinIO/Meili 内存降级）
cd backend
pytest tests/unit -q
pytest tests/integration -q
coverage run -m pytest tests/unit -q && coverage run --append -m pytest tests/integration -q && coverage report --fail-under=70

# 前端组件测试（Vitest + React Testing Library）
cd frontend && npm run test

# 端到端（Playwright，自动拉起前后端）
cd e2e && npm install && npx playwright install chromium && npm test
```

> 建议按层分进程执行后端用例，以避免 Windows 上偶发的 `aiosqlite` 后台连接线程原生 Abort。

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
| **集成** | `.../test_external/` | 邮件任务参数、AI（OpenAI 兼容）mock 与三层降级、对象存储上传回读、搜索索引同步与降级 |
| **端到端** | `e2e/tests/` | 首页浏览、注册、登录会话、未登录重定向、发布与议价、即时消息、管理后台、课程评价 |

测试数据由 `backend/tests/factories.py`（factory_boy）生成，
每个用例跑在 `drop_all + create_all` 重建的干净库上，无需手动回滚。

生命周期测试通过 `conftest.lifecycle_env` 把全局 engine / SessionLocal 重定向到临时库，因此可以安全地跑完整 lifespan——而常规 `client` fixture 为提速刻意跳过了 lifespan。

## 生产部署

一条命令拉起全部服务（app + worker + PostgreSQL + Redis + MinIO + Meilisearch + Nginx）：

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env.example up -d
```

详细步骤见 [docs/usage.md](docs/usage.md) 与 [docs/部署手册.md](docs/部署手册.md)。首次部署的配置清单（环境变量 / 配置文件 / 依赖服务 / 密钥 / 数据库初始化）见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## API

后端通过 FastAPI 自动生成 OpenAPI 文档，开发态访问 <http://localhost:8000/docs> 即可交互调试。

- **REST 接口**：共 **128 个**（见 [docs/API_Reference.md](docs/API_Reference.md) 的字段级参考）。
- **WebSocket**：`/ws` 实时私信通道（不计入 OpenAPI）。
- **AI 端点**（默认关闭，需配置 `ai.feature.enabled=true` 与模型 Key）：`/api/ai/{status,insights,item-description,course-summary,categorize}` 与 `/api/admin/ai/config`。前端入口受 `/api/ai/status` 能力级状态控制，未启用时自动隐藏。

## 安全

- **凭证与网关**：管理后台接口在未携带有效 `X-Admin-Gateway` 网关令牌时返回 404，不暴露接口存在性；管理员凭据与网关密钥均由 `config/school.yaml` 与 `.env` 下发，不硬编码。
- **防滥用**：发送验证码前需完成滑块拼图验证，缺口横坐标仅留存服务端（Redis），校验票据一次性作废。
- **漏洞反馈**：如发现安全问题，请**私下**联系维护者（见[维护者](#维护者)），请勿在公开 Issue 中披露细节。

## 维护者

本项目由 **穆萨江（Ky）** 独立开发与维护（GitHub：[@mjkyleo](https://github.com/mjkyleo)）。

- 问题反馈与功能讨论：请通过本仓库的 **Issue** 板块提出。
- 联系方式：以仓库 Issue 为统一入口；如需私下沟通安全事项，见[安全](#安全)。

## 贡献

欢迎参与贡献！

1. 阅读 [docs/development.md](docs/development.md) 了解架构、模块设计与代码规范；
2. 在 [docs/后续开发计划.md](docs/后续开发计划.md) 或 Issue 中认领任务；
3. Fork 仓库并创建功能分支：`git checkout -b feat/xxx`；
4. 遵循现有代码风格（Python：`ruff` + `black` 风格；TypeScript：Prettier），并补充 / 更新测试；
5. 本地跑通 `pytest -q` 与 `npm run lint` 后提交 Pull Request，描述变更与验证结果。

提交信息建议使用约定式提交（`feat:` / `fix:` / `docs:` / `refactor:` 等）。

## 许可

`UNLICENSED`

本项目为内部项目，目前**尚未指定开源许可证**。代码所有权归开发者本人（穆萨江）所有，未经授权不得对外复制、分发或修改。如需使用，请联系[维护者](#维护者)。
