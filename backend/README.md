# 校园生活平台（Python 重写）后端

FastAPI 模块化单体：认证、用户、二手物品、消息(WebSocket)、课程、食堂、兼职、资源共享、队友招募、举报、管理后台，以及 Celery 异步任务与 Meilisearch 搜索。

## 快速开始（开发 / 零依赖）

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # 默认使用 SQLite，无需任何外部组件

# 启动（自动建表 + 注入默认管理员 admin/admin123）
uvicorn app.asgi:app --reload --port 8000

# 另开终端执行迁移（可选，等价的建表方式）
alembic upgrade head
```

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 指标：http://localhost:8000/metrics

## Celery 异步任务（可选）

默认使用 SQLite + 本地 Redis 即可本地开发；需要异步任务时另开终端启动 worker：

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=info -Q email,notify,search,default
```

| 任务 | 队列 | 说明 |
| --- | --- | --- |
| `app.tasks.email.send_welcome` | `email` | 注册后欢迎邮件 |
| `app.tasks.email.send_email` | `email` | 通用邮件发送 |
| `app.tasks.notify.send_notify` | `notify` | 站内通知投递 |
| `app.tasks.search_sync.sync_item` | `search` | 物品文档同步到 Meilisearch |
| `app.tasks.search_sync.sync_user` | `search` | 用户文档同步到 Meilisearch |
| `app.tasks.search_sync.delete_doc` | `search` | 删除 Meilisearch 文档 |
| `app.tasks.summary.generate_trade_summary` | `default` | 交易会话摘要生成（worker 内走同步 DB 访问） |

> 生产部署时 worker 容器通过 `sync_db` 使用同步驱动访问 PostgreSQL，无需额外配置。

## 账号体系（邮箱注册 / 统一登录 / 多方式绑定）

- **邮箱格式设置**：`config/school.yaml` 的 `auth.email_register` 定义默认规则（开关、域名白名单、正则），管理员可在后台 `GET/PUT /api/admin/auth/email-config` 动态覆盖（DB 优先，实时生效）。
- **邮箱注册**：`POST /api/auth/email-register`（需邮箱验证码，`purpose=register`），符合规则的邮箱注册后自动生成唯一自定义账号。
- **统一登录**：`POST /api/auth/login` 的 `account` 字段同时接受 邮箱 / 手机号 / 自定义账号 + 密码；QQ、微信快捷登录接口不变。
- **多方式绑定**（均需登录）：
  - `GET /api/auth/bindings` 查询当前账户绑定情况
  - `POST /api/auth/bind/email`（验证码 `purpose=bind_email`）、`POST /api/auth/bind/phone`（`purpose=bind_phone`）
  - `POST /api/auth/bind/oauth` 绑定 QQ/微信（需授权码，建议配合 `state` 防 CSRF）
  - `DELETE /api/auth/unbind/{email,phone,oauth}` 解绑
- **账户关联冲突**：绑定的邮箱 / 手机号 / 第三方 openid 已被其他账户占用时，默认**拒绝绑定**并返回明确提示（`40900`）；解绑后该方式可被其他账户重新绑定。

## 目录结构

- `app/core` 配置/数据库/Redis/安全/响应/异常/日志/中间件/存储
- `app/common` Base/Mixins、枚举、工具
- `app/modules/*` 业务模块（auth/user/item/message/course/canteen/job/share/teammate/report/admin）
- `app/tasks` Celery 任务
- `app/search` Meilisearch 客户端
- `tests` pytest 冒烟测试

## 测试

```bash
pytest -q
```

## 生产部署

见 `deploy/docker-compose.yml`，一条命令拉起 app + worker + PostgreSQL + Redis + MinIO + Meilisearch + Nginx：
`docker compose -f deploy/docker-compose.yml --env-file deploy/.env.example up -d`
