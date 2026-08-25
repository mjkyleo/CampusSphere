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

- **后端**：Python 3.11+ / FastAPI / SQLAlchemy 2（async）/ pydantic-settings / alembic / Celery / Redis / structlog
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
    ├── 项目现状分析.md
    ├── 后续开发计划.md
    ├── API_Reference.md     # 73 个接口文档
    └── openapi.json
```

## 快速开始（开发环境）

前置要求：Python 3.11+、Node.js 18+。

### 1. 启动后端（零外部依赖）

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                                # 默认 SQLite，无需任何外部组件
uvicorn app.asgi:app --reload --port 8000           # 自动建表 + 注入默认管理员 admin/admin123
```

验证：<http://localhost:8000/health> 返回 `ok`，API 文档 <http://localhost:8000/docs>。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

前端 Express 层将 `/api/*` 与 `/ws` 自动代理到 `http://127.0.0.1:8000`，无需额外配置。

> **端口说明**：后端监听 `127.0.0.1:8000`；前端监听 `5173`（Windows Hyper-V 排除范围会拒绝绑定 3000，且 Node 24 将 `localhost` 解析为 IPv6 `::1`，故代理目标统一使用 `127.0.0.1`）。

### 3. 登录

默认管理员账号：**admin / admin123**。注册账号走邮箱验证码流程（开发模式可配置为任意邮箱）。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [docs/usage.md](docs/usage.md) | 使用说明：安装步骤、配置项、功能模块使用、生产部署 |
| [docs/development.md](docs/development.md) | 开发指南：架构设计、模块说明、API 约定、测试与贡献 |
| [docs/API_Reference.md](docs/API_Reference.md) | 73 个接口的字段级参考 |
| [docs/部署手册.md](docs/部署手册.md) | 生产部署手册 |
| [docs/项目现状分析.md](docs/项目现状分析.md) | 项目现状与结构分析 |
| [docs/后续开发计划.md](docs/后续开发计划.md) | 开发路线图 |

## 测试

```bash
# 后端 pytest 冒烟测试
cd backend && pytest -q

# 前端类型检查
cd frontend && npm run lint        # tsc --noEmit
```

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
