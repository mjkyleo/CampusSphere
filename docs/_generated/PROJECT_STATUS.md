<!-- 本文件由 scripts/doc_sync.py 自动生成，请勿手工编辑 -->
# 项目状态快照（自动生成）

> 生成时间：2026-09-05 09:56 UTC  ｜  来源：`scripts/doc_sync.py`
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
        0002_campus_config.py
    alembic.ini
    app/
      __init__.py
      asgi.py
      common/
        __init__.py
        enums.py
        models.py
        schemas.py
        types.py
        utils.py
      core/
        __init__.py
        cache.py
        config.py
        config_reload.py
        database.py
        deps.py
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
        audit/
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
    Dockerfile
    pyproject.toml
    README.md
    scripts/
      fake_redis_server.py
      gen_api_docs.py
      kill_celery.ps1
      list_python.ps1
      seed_canteens.py
      seed_demo_users.py
    tests/
      conftest.py
      factories.py
      helpers.py
      integration/
        __init__.py
        conftest.py
        test_admin/
        test_auth/
        test_canteen/
        test_course/
        test_external/
        test_items/
        test_messaging/
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
      unit/
        __init__.py
        conftest.py
        test_captcha_thread_offload_unit.py
        test_captcha_unit.py
        test_config_hot_reload_unit.py
        test_item_schema_rules_unit.py
        test_redis_fallback_unit.py
        test_scope_deps_unit.py
        test_security_unit.py
        test_trace_id_unit.py
        test_utils_unit.py
        test_ws_seq_unit.py
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
      external-proxy.conf.example
      nginx.conf
      nginx.http-only.conf
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
    API_Reference.md
    audit/
      01-architecture.md
      02-startup-and-code-quality.md
      03-qa-and-production-readiness.md
      04-optimization-roadmap.md
      05-optimization-progress.md
    DEPLOYMENT.md
    development.md
    images/
      campusphere-architecture.svg
    openapi.json
    REFACTOR_DELIVERABLE.md
    TESTING.md
    usage.md
    后续开发计划.md
    架构与面试备战白皮书.md
    模块级技术白皮书与面试备战手册.md
    部署手册.md
    配置方案_2026-09-04.md
    配置方案总览.html
    项目现状分析.md
  e2e/
    package-lock.json
    package.json
    pages/
      AdminPage.ts
      BasePage.ts
      CoursePage.ts
      HomePage.ts
      LoginPage.ts
      MarketPage.ts
      MessagePage.ts
    playwright.config.ts
    README.md
    test-results/
    tests/
      01-home-browsing.spec.ts
      02-register.spec.ts
      03-login-session.spec.ts
      04-unauthorized-redirect.spec.ts
      05-publish-and-bargain.spec.ts
      06-messaging.spec.ts
      07-admin-moderation.spec.ts
      08-course-review.spec.ts
    tsconfig.json
    utils/
      auth-helpers.ts
      test-data.ts
  examples/
    email_verification_flask/
      email_verification_flask_example.py
  frontend/
    D:\Phase3\Projects\CampusSphere\frontend\App.tsx/
    D:\Phase3\Projects\CampusSphere\frontend\bun.lock/
    D:\Phase3\Projects\CampusSphere\frontend\components/
    D:\Phase3\Projects\CampusSphere\frontend\context/
    D:\Phase3\Projects\CampusSphere\frontend\dev_err.txt/
    D:\Phase3\Projects\CampusSphere\frontend\dev_log.txt/
    D:\Phase3\Projects\CampusSphere\frontend\hooks/
    D:\Phase3\Projects\CampusSphere\frontend\index.css/
    D:\Phase3\Projects\CampusSphere\frontend\index.html/
    D:\Phase3\Projects\CampusSphere\frontend\index.tsx/
    D:\Phase3\Projects\CampusSphere\frontend\metadata.json/
    D:\Phase3\Projects\CampusSphere\frontend\package-lock.json/
    D:\Phase3\Projects\CampusSphere\frontend\package.json/
    D:\Phase3\Projects\CampusSphere\frontend\pages/
    … (+11 项)
  rag-projects-analysis.html
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
| `admin` | 47 | ✅ | ✅ | ✅ | 管理后台 |
| `ai` | 5 | ✅ | ✅ | ✅ | AI |
| `audit` | 2 | ✅ | ✅ | ✅ | — |
| `auth` | 24 | ✅ | ✅ | ✅ | 认证 |
| `canteen` | 5 | ✅ | ✅ | ✅ | 食堂 |
| `course` | 5 | ✅ | ✅ | ✅ | 课程 |
| `item` | 8 | ✅ | ✅ | ✅ | 二手 |
| `job` | 5 | ✅ | ✅ | ✅ | 兼职 |
| `launcher` | 3 | ✅ | — | — | 启动器 |
| `message` | 4 | ✅ | ✅ | ✅ | 消息 |
| `report` | 3 | ✅ | ✅ | ✅ | 举报 |
| `share` | 4 | ✅ | ✅ | ✅ | 分享 |
| `storage` | 3 | ✅ | — | — | 对象存储 |
| `teammate` | 5 | ✅ | ✅ | ✅ | 组队 |
| `user` | 4 | ✅ | ✅ | ✅ | 用户 |

共 15 个业务模块。

## 前端页面

共 17 个页面：`AdminDashboard`、`AdminLoginPage`、`CanteenList`、`CanteenStall`、`CourseDetail`、`CourseReview`、`CourseSearch`、`HomePage`、`JobList`、`LoginPage`、`MarketDetail`、`MarketList`、`MarketPublish`、`MessageCenter`、`ShareFeed`、`TeammatePost`、`UserProfile`

## 依赖

- Python 运行时要求：`>=3.12`
- 后端依赖（27 项）：`fastapi>=0.111`、`uvicorn[standard]>=0.30`、`python-multipart>=0.0.9`、`sqlalchemy>=2.0.30`、`asyncpg>=0.29`、`psycopg2-binary>=2.9`、`alembic>=1.13`、`aiosqlite>=0.20`、`pydantic>=2.7`、`pydantic-settings>=2.3`、`email-validator>=2.0`、`redis>=5.0` 等
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
| `AUTH_RATE_LIMIT_PER_MINUTE` | int | `10` | 登录 / 注册 / 验证码等认证端点单独限流（防爆破与刷接口）。 生产保持 10；测试环境需放宽，否则批量创建用户的用例会在同一分钟内互相 挤爆限额（中间件已把它做成构造参数，这里补上配置入口供 .env 覆盖）。 |
| `ADMIN_GATEWAY_KEY` | str | `""` | 这些字段专门保护 /api/admin/* 的可达性，与普通用户账号无关。 - admin_gateway_key  : 前端页面可见，调用 /api/admin/discover 时用它换取 X-Admin-Gateway 短期 token。 错误的 gateway key 一律 404 Not Found（对未授权 |
| `ADMIN_BOOTSTRAP_ENABLED` | bool | `True` | — |
| `ADMIN_BOOTSTRAP_USERNAME` | str | `"siteadmin"` | — |
| `ADMIN_BOOTSTRAP_PASSWORD` | str | `""` | — |
| `ADMIN_BOOTSTRAP_MIN_LENGTH` | int | `16` | — |
| `ADMIN_GATEWAY_ROTATE_SECONDS` | int | `3600` | 派生 token 1 小时轮换 |
| `ADMIN_GATEWAY_ENFORCE` | bool | `True` | 网关强制开关：True=生产（默认，强制校验 X-Admin-Gateway）；False=本地开发放宽（免网关密钥）。 仅用于本地联调，生产环境请勿置为 false（validate_admin_security 会告警）。 |
| `SMTP_HOST` | str | `""` | 生产环境**必须**配置 smtp_host，否则验证码无法送达（启动校验会拒绝启动）。 |
| `EXPOSE_VERIFICATION_CODE` | bool | `False` | 是否在 ``send-code`` 响应里回传验证码（供本地联调与自动化测试读取）。  这是一个**独立开关**而非复用 DEBUG：DEBUG 还控制管理员网关校验开关 （``gateway_enforced() = admin_gateway_enforce and not debug``）与启动期 安全强校验的严 |
| `SMTP_PORT` | int | `465` | — |
| `SMTP_USER` | str | `""` | — |
| `SMTP_PASS` | str | `""` | — |
| `SMTP_FROM` | str | `""` | 发件人地址。留空时回退为 smtp_user（多数 SMTP 服务商要求两者一致）。 |
| `SMTP_TIMEOUT` | int | `10` | 连接/读超时（秒）。SMTP 为同步阻塞调用，必须设上限，避免 worker 被拖死。 |
| `EMAIL_DISPATCH_TIMEOUT` | int | `20` | 邮件任务**入队+兜底直发**的等待上限（秒）。 结果后端已禁用，broker 不可达时 delay() 约 2 秒内快速失败并降级为内联直发； 内联直发走 smtp_timeout（默认 10s）。本值需覆盖「broker 快速失败 + 内联 SMTP 发送」， 留出余量，避免正常内联发送被误判超时。 |
| `SMTP_STARTTLS` | bool | None | `None` | True=强制 STARTTLS（587 等端口）；留为 None 时按端口推断：465 走 SSL，其余走 STARTTLS。 |
| `CAPTCHA_ENABLED` | bool | `True` | 关闭后 /api/auth/send-code 不再要求票据（供测试与内网环境使用）。 |
| `CAPTCHA_TOLERANCE_PX` | int | `6` | 缺口对齐容差（像素），过小会伤及真实用户体验 |
| `CAPTCHA_TTL_SECONDS` | int | `300` | 滑块令牌有效期 |
| `CAPTCHA_MAX_ATTEMPTS` | int | `3` | 同一滑块最多校验次数，超出即作废 |
| `CAPTCHA_MIN_TRACK_POINTS` | int | `6` | 轨迹最少采样点，防脚本直传坐标 |
| `CAPTCHA_TICKET_TTL_SECONDS` | int | `120` | 校验通过签发的票据有效期 |
| `GEETEST_CAPTCHA_ID` | str | `""` | 留空则使用上面那套自建拼图滑块；填入 captcha_id / captcha_key 后， /api/auth/captcha/config 会下发 provider=geetest，前端自动切到极验。 这样"是否接入第三方"变成纯配置决策，不需要改代码重新发版。 |
| `GEETEST_CAPTCHA_KEY` | str | `""` | — |
| `GEETEST_TIMEOUT` | int | `5` | 二次校验接口超时（秒）。必须设上限：极验服务不可达时若无限等待， 会把 uvicorn 的工作线程拖死，进而影响整站。 |
| `GEETEST_FAIL_OPEN` | bool | `True` | 容灾开关：极验服务异常/超时时是否放行。 True  → 校验接口不可达时"放行"，保证用户仍能注册（牺牲部分防刷能力） False → 校验接口不可达时"拒绝"，宁可暂时无法注册也不放机器人进来 |
| `CODE_TTL_SECONDS` | int | `300` | 验证码有效期 |
| `CODE_MAX_ATTEMPTS` | int | `5` | 同一验证码最多校验次数，超出即作废 |
| `CODE_SEND_LIMIT_PER_MINUTE` | int | `1` | 同一 target 每分钟最多发送次数（防轰炸邮箱/手机）；0 表示不限制。 |
| `CORS_ORIGINS` | list[str] | `["http://localhost:5173", "http://127.0.0.1:5173"]` | 默认放行前端（frontend :5173；3000 在 Windows Hyper-V 排除范围不可用）；生产环境用 .env 的 CORS_ORIGINS 覆盖 |
| `SCHOOL_CONFIG_PATH` | str | `"../config/school.yaml"` | — |
| `SCHOOL_NAME` | str | `"示例大学"` | — |
| `SCHOOL_DOMAIN` | str | `"localhost"` | — |
| `OAUTH` | dict[str, Any] | `{}` | 由 school.yaml 注入的嵌套配置 |
| `MINIO` | dict[str, Any] | `{}` | — |
| `MEILISEARCH` | dict[str, Any] | `{}` | — |
| `REPORT_POLICY` | dict[str, Any] | `{}` | — |
| `AUTH` | dict[str, Any] | `{}` | — |
| `ITEMS` | dict[str, Any] | `{}` | — |
| `COURSES` | dict[str, Any] | `{}` | — |
| `AI` | dict[str, Any] | `{}` | — |
| `ADMIN` | dict[str, Any] | `{}` | — |
| `JOB` | dict[str, Any] | `{}` | 分类配置化（P1）：与 items.categories 同一套「yaml 默认 → DB 覆盖 → 公开端点下发 → 前端兜底」四层模式，消除前端写死分类。 |
| `SHARE` | dict[str, Any] | `{}` | — |
| `TEAMMATE` | dict[str, Any] | `{}` | — |
| `CANTEEN` | dict[str, Any] | `{}` | 食堂维度枚举（P3）：学部 / 餐饮区 / 类型 / 学期。 |
| `MINIO_ENDPOINT` | str | None | `None` | — |
| `MINIO_ACCESS_KEY` | str | None | `None` | — |
| `MINIO_SECRET_KEY` | str | None | `None` | — |
| `MINIO_SECURE` | bool | `False` | — |
| `MINIO_BUCKET` | str | `"campus"` | — |
| `MEILI_HOST` | str | `"http://localhost:7700"` | — |
| `MEILI_API_KEY` | str | `"masterKey"` | — |
| `CELERY_BROKER_URL` | str | `"redis://localhost:6379/1"` | — |
| `CELERY_RESULT_BACKEND` | str | `"redis://localhost:6379/2"` | — |

## 多校配置（config/school.yaml 顶层区块）

``

## 接口文档

- API_Reference.md 抽取接口数：**128**
