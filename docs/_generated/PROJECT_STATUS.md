<!-- 本文件由 scripts/doc_sync.py 自动生成，请勿手工编辑 -->
# 项目状态快照（自动生成）

> 生成时间：2026-08-29 06:51 UTC  ｜  来源：`scripts/doc_sync.py`
> 本文件由代码实时抽取，反映当前仓库真实状态；如需修改内容，请改代码后重跑工具。

## 目录结构（节选）

```text
CampusSphere/
  backend/
    alembic/
      env.py
      script.py.mako
      versions/
        0001_initial.py
    alembic.ini
    app/
      __init__.py
      asgi.py
      common/
        __init__.py
        enums.py
        models.py
        schemas.py
        utils.py
      core/
        __init__.py
        cache.py
        config.py
        database.py
        exceptions.py
        logging.py
        middleware.py
        redis.py
        response.py
        security.py
        storage.py
        sync_db.py
      main.py
      modules/
        admin/
        ai/
        auth/
        canteen/
        course/
        item/
        job/
        launcher/
        message/
        report/
        share/
        storage/
        teammate/
        user/
      search/
        __init__.py
        client.py
      tasks/
        __init__.py
        celery_app.py
        email.py
        notify.py
        search_sync.py
        summary.py
    campus_life_platform.egg-info/
      dependency_links.txt
      PKG-INFO
      requires.txt
      SOURCES.txt
      top_level.txt
    check_imports.py
    check_imports.txt
    Dockerfile
    pip_install.txt
    pip_install2.txt
    pyproject.toml
    pytest_collect.txt
    pytest_ver.txt
    README.md
    ruff_out.txt
    scripts/
      fake_redis_server.py
      gen_api_docs.py
      kill_celery.ps1
      list_python.ps1
    tests/
      conftest.py
      helpers.py
      test_admin_gateway.py
      test_arch_imports.py
      test_auth.py
      test_auth_email.py
      test_auth_login.py
      test_captcha.py
      test_celery_summary.py
      test_course_canteen.py
      test_e2e_flow.py
      test_idor.py
      test_item.py
      test_item_review.py
      test_lifecycle.py
      test_message.py
      test_p1.py
      test_shutdown_resources.py
      test_smoke.py
      test_user.py
      test_websocket.py
  config/
    logging.yaml
    school.yaml
  deploy/
    docker-compose.yml
    Dockerfile.worker
    grafana/
      dashboards/
        api-overview.json
    nginx/
      nginx.conf
      ssl/
        README.md
    prometheus/
      alerts.yml
      prometheus.yml
    start_dev.bat
  docs/
    _generated/
      DOC_DRIFT_REPORT.md
      PROJECT_STATUS.md
      state.json
    API_Reference.md
    audit/
      01-architecture.md
      02-startup-and-code-quality.md
      03-qa-and-production-readiness.md
      04-optimization-roadmap.md
      05-optimization-progress.md
    DEPLOYMENT.md
    development.md
    openapi.json
    usage.md
    后续开发计划.md
    部署手册.md
    项目现状分析.md
  examples/
    email_verification_flask/
      email_verification_flask_example.py
  frontend/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\App.tsx/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\bun.lock/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\components/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\context/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\dev_err.txt/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\dev_log.txt/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\hooks/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\index.css/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\index.html/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\index.tsx/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\metadata.json/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\package-lock.json/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\package.json/
    C:\Users\86132\Desktop\Phase3\Projects\CampusSphere\frontend\pages/
    … (+9 项)
  README.md
  scripts/
    check_css_classes.js
    devctl.py
    doc_sync.py
    start.bat
    stop.bat
    verify_render.py
```

## 核心后端模块

| 模块 | 路由数 | router | service | schemas | 文档别名 |
| --- | ---: | --- | --- | --- | --- |
| `admin` | 36 | ✅ | ✅ | ✅ | 管理后台 |
| `ai` | 5 | ✅ | ✅ | ✅ | AI |
| `auth` | 23 | ✅ | ✅ | ✅ | 认证 |
| `canteen` | 4 | ✅ | ✅ | ✅ | 食堂 |
| `course` | 5 | ✅ | ✅ | ✅ | 课程 |
| `item` | 8 | ✅ | ✅ | ✅ | 二手 |
| `job` | 4 | ✅ | ✅ | ✅ | 兼职 |
| `launcher` | 2 | ✅ | — | — | 启动器 |
| `message` | 4 | ✅ | ✅ | ✅ | 消息 |
| `report` | 3 | ✅ | ✅ | ✅ | 举报 |
| `share` | 3 | ✅ | ✅ | ✅ | 分享 |
| `storage` | 3 | ✅ | — | — | 对象存储 |
| `teammate` | 4 | ✅ | ✅ | ✅ | 组队 |
| `user` | 4 | ✅ | ✅ | ✅ | 用户 |

共 14 个业务模块。

## 前端页面

共 16 个页面：`AdminDashboard`、`CanteenList`、`CanteenStall`、`CourseDetail`、`CourseReview`、`CourseSearch`、`HomePage`、`JobList`、`LoginPage`、`MarketDetail`、`MarketList`、`MarketPublish`、`MessageCenter`、`ShareFeed`、`TeammatePost`、`UserProfile`

## 依赖

- Python 运行时要求：`>=3.12`
- 后端依赖（26 项）：`fastapi>=0.111`、`uvicorn[standard]>=0.30`、`python-multipart>=0.0.9`、`sqlalchemy>=2.0.30`、`asyncpg>=0.29`、`psycopg2-binary>=2.9`、`alembic>=1.13`、`aiosqlite>=0.20`、`pydantic>=2.7`、`pydantic-settings>=2.3`、`redis>=5.0`、`celery>=5.4` 等
- 前端依赖：8 项（React / Vite / Express 等，详见 frontend/package.json）

## 测试

后端测试文件 19 个：`test_admin_gateway.py`、`test_arch_imports.py`、`test_auth.py`、`test_auth_email.py`、`test_auth_login.py`、`test_captcha.py`、`test_celery_summary.py`、`test_course_canteen.py`、`test_e2e_flow.py`、`test_idor.py`、`test_item.py`、`test_item_review.py`、`test_lifecycle.py`、`test_message.py`、`test_p1.py`、`test_shutdown_resources.py`、`test_smoke.py`、`test_user.py`、`test_websocket.py`

## 配置项清单（来自 config.py）

> 完整「初次部署/启动配置」见 [docs/DEPLOYMENT.md](DEPLOYMENT.md)。

| 配置键（环境变量） | 类型 | 默认值 | 用途 |
| --- | --- | --- | --- |
| `APP_NAME` | str | `"campus-life-platform"` | — |
| `DEBUG` | bool | `False` | — |
| `DB_URL` | str | `"sqlite+aiosqlite:///./dev.db"` | — |
| `DB_POOL_SIZE` | int | `10` | 常驻连接数 |
| `DB_MAX_OVERFLOW` | int | `20` | 超出 pool_size 后允许临时创建的最大连接数 |
| `DB_POOL_RECYCLE` | int | `1800` | 秒：回收空闲连接，规避中间件静默断连（如 PG 的 idle_timeout） |
| `DB_POOL_TIMEOUT` | int | `30` | 秒：等待连接池可用的最大阻塞时间 |
| `REDIS_URL` | str | `"redis://localhost:6379/0"` | — |
| `CACHE_ENABLED` | bool | `True` | 默认开启；测试/本地无 Redis 时自动降级为内存字典，不会阻断业务。 关闭：设置 CACHE_ENABLED=false（如离线单测避免跨用例污染）。 |
| `CACHE_TTL_SECONDS` | int | `60` | 热点列表缓存基础 TTL（秒）；实际写入会叠加随机抖动以规避雪崩（见 app/core/cache.py）。 |
| `SECRET_KEY` | str | `"change-me-to-a-long-random-string-in-prod"` | — |
| `JWT_ALGORITHM` | str | `"HS256"` | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `15` | — |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | `7` | — |
| `RATE_LIMIT_PER_MINUTE` | int | `120` | — |
| `ADMIN_GATEWAY_KEY` | str | `""` | 这些字段专门保护 /api/admin/* 的可达性，与普通用户账号无关。 - admin_gateway_key  : 前端页面可见，调用 /api/admin/discover 时用它换取 X-Admin-Gateway 短期 token。 错误的 gateway key 一律 404 Not Found（对未授权 |
| `ADMIN_BOOTSTRAP_ENABLED` | bool | `True` | — |
| `ADMIN_BOOTSTRAP_USERNAME` | str | `"siteadmin"` | — |
| `ADMIN_BOOTSTRAP_PASSWORD` | str | `""` | — |
| `ADMIN_BOOTSTRAP_MIN_LENGTH` | int | `16` | — |
| `ADMIN_GATEWAY_ROTATE_SECONDS` | int | `3600` | 派生 token 1 小时轮换 |
| `ADMIN_GATEWAY_ENFORCE` | bool | `True` | 网关强制开关：True=生产（默认，强制校验 X-Admin-Gateway）；False=本地开发放宽（免网关密钥）。 仅用于本地联调，生产环境请勿置为 false（validate_admin_security 会告警）。 |
| `SMTP_HOST` | str | `""` | 未配置 SMTP 时，验证码接口会返回 debug_code 便于测试联调； 配置后验证码仅通过邮件送达，生产环境必须配置。 |
| `SMTP_PORT` | int | `465` | — |
| `SMTP_USER` | str | `""` | — |
| `SMTP_PASS` | str | `""` | — |
| `CAPTCHA_ENABLED` | bool | `True` | 关闭后 /api/auth/send-code 不再要求票据（供测试与内网环境使用）。 |
| `CAPTCHA_TOLERANCE_PX` | int | `6` | 缺口对齐容差（像素），过小会伤及真实用户体验 |
| `CAPTCHA_TTL_SECONDS` | int | `300` | 滑块令牌有效期 |
| `CAPTCHA_MAX_ATTEMPTS` | int | `3` | 同一滑块最多校验次数，超出即作废 |
| `CAPTCHA_MIN_TRACK_POINTS` | int | `6` | 轨迹最少采样点，防脚本直传坐标 |
| `CAPTCHA_TICKET_TTL_SECONDS` | int | `120` | 校验通过签发的票据有效期 |
| `CODE_TTL_SECONDS` | int | `300` | 验证码有效期 |
| `CODE_MAX_ATTEMPTS` | int | `5` | 同一验证码最多校验次数，超出即作废 |
| `CORS_ORIGINS` | List[str] | `["http://localhost:5173", "http://127.0.0.1:5173"]` | 默认放行前端（frontend :5173；3000 在 Windows Hyper-V 排除范围不可用）；生产环境用 .env 的 CORS_ORIGINS 覆盖 |
| `SCHOOL_CONFIG_PATH` | str | `"../config/school.yaml"` | — |
| `SCHOOL_NAME` | str | `"示例大学"` | — |
| `SCHOOL_DOMAIN` | str | `"localhost"` | — |
| `OAUTH` | Dict[str, Any] | `{}` | 由 school.yaml 注入的嵌套配置 |
| `MINIO` | Dict[str, Any] | `{}` | — |
| `MEILISEARCH` | Dict[str, Any] | `{}` | — |
| `REPORT_POLICY` | Dict[str, Any] | `{}` | — |
| `AUTH` | Dict[str, Any] | `{}` | — |
| `ITEMS` | Dict[str, Any] | `{}` | — |
| `COURSES` | Dict[str, Any] | `{}` | — |
| `AI` | Dict[str, Any] | `{}` | — |
| `ADMIN` | Dict[str, Any] | `{}` | — |
| `MINIO_ENDPOINT` | Optional[str] | `None` | — |
| `MINIO_ACCESS_KEY` | Optional[str] | `None` | — |
| `MINIO_SECRET_KEY` | Optional[str] | `None` | — |
| `MINIO_SECURE` | bool | `False` | — |
| `MINIO_BUCKET` | str | `"campus"` | — |
| `MEILI_HOST` | str | `"http://localhost:7700"` | — |
| `MEILI_API_KEY` | str | `"masterKey"` | — |
| `CELERY_BROKER_URL` | str | `"redis://localhost:6379/1"` | — |
| `CELERY_RESULT_BACKEND` | str | `"redis://localhost:6379/2"` | — |

## 多校配置（config/school.yaml 顶层区块）

``

## 接口文档

- API_Reference.md 抽取接口数：**88**
