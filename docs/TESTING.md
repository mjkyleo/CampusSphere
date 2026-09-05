# CampusSphere 测试计划

> 目标：用**单元测试 / 集成测试 / 端到端测试**三层体系覆盖核心用户旅程，
> 让"改动是否破坏了既有行为"这件事在合并之前就被机器回答。

---

## 1. 分层策略

| 层 | 范围 | 工具 | 是否依赖外部服务 | 运行耗时 |
|---|---|---|---|---|
| **单元测试** `backend/tests/unit/`、`frontend/__tests__/` | 单个函数/模块/组件，无数据库、无网络 | 后端 pytest + pytest-asyncio；**前端 Vitest + React Testing Library**（见 §2 选型说明） | 否 | ~2s / ~10s |
| **集成测试** `backend/tests/integration/` | API 端点 + 真实数据库（临时 SQLite）+ Redis/MinIO/Search 走**内存降级或 mock** | pytest + factory_boy + monkeypatch | 否（全部可降级/mock） | ~7 分钟 |
| **端到端测试** `e2e/` | 浏览器 → 前端代理层 → 后端 → 数据库全链路 | Playwright（页面对象模式） | 需要拉起前后端（Playwright 自动启动） | ~5 分钟 |

**分层原则**：越靠上越贴近用户、越慢越脆，因此"能下沉的断言尽量下沉"——
业务规则在集成层验证，只有真正需要真实浏览器/真实路由跳转的场景才放 E2E。

---

## 2. 工具选型说明（含两处对需求的偏离）

1. **前端用 Vitest 而非 Jest**
   本项目是 **Vite 6 + ESM + TSX**。Jest 需要额外接 `ts-jest`/Babel 处理 ESM 与 JSX，
   且要把 `@/` 别名、插件链配两遍，长期维护成本高。
   **Vitest** 与 Jest API 高度兼容（`describe/it/expect/vi.fn/beforeEach` 完全一致），
   但直接复用 Vite 的解析与插件，零额外转译配置。
   > 若团队坚持 Jest，替换成本约等于重写 `vitest.config.ts` 为一个 `jest.config.cjs`。

2. **前端测试目录为 `frontend/__tests__/` 而非 `frontend/src/__tests__/`**
   本项目**没有 `src/` 目录**，源码根就是 `frontend/`（`components/`、`pages/`、`services/`）。
   测试目录镜像真实源码布局，避免为了放测试而凭空造一个空的 `src/`。

---

## 3. 目录结构

```
backend/
├── pyproject.toml            # pytest 配置：分层标记、覆盖率源与排除项
└── tests/
    ├── conftest.py           # 公共夹具：临时 SQLite、get_db 覆盖、限流放宽
    ├── helpers.py            # 注册登录、认证头、lifespan 驱动
    ├── factories.py          # ★ factory_boy 数据工厂（用户/物品/课程/食堂/举报）
    ├── unit/                 # ── 单元测试层 ──
    │   ├── conftest.py       # 清空 Redis 内存兜底（保证用例间零残留）
    │   ├── test_captcha_unit.py
    │   ├── test_security_unit.py
    │   └── test_utils_unit.py
    ├── integration/          # ── 集成测试层 ──
    │   ├── conftest.py       # fx 工厂入口 + 自动打 integration 标记
    │   ├── test_auth/        # 注册流程、登录鉴权
    │   ├── test_items/       # 发布、议价会话
    │   ├── test_course/      # 课程搜索与评价
    │   ├── test_canteen/     # 食堂档口菜品评价
    │   ├── test_messaging/   # WebSocket 消息
    │   ├── test_admin/       # 管理后台治理
    │   └── test_external/    # 邮件 / AI / 存储 / 搜索索引（mock 或降级）
    └── test_*.py             # 既有回归用例（`pytest --collect-only` 实测 116 个用例 / 117 个 `test_` 函数；2026-09-05 修正：旧版文档"113 个"已过时）

frontend/
├── vitest.config.ts          # jsdom + 覆盖率配置
├── __tests__/
│   ├── setup.ts              # jest-dom 匹配器 + 自动 cleanup
│   └── components/
│       ├── SliderCaptcha.test.tsx
│       └── RouteGuards.test.tsx

e2e/
├── playwright.config.ts      # 自动拉起前后端 + E2E 专用库
├── pages/                    # 页面对象（BasePage / LoginPage / MarketPage ...）
├── utils/                    # 测试数据与登录态预置
└── tests/                    # 8 个端到端场景
```

---

## 4. 测试数据策略

### 4.1 factory_boy 数据工厂（`backend/tests/factories.py`）

覆盖 `User / Item / ItemImage / Course / CourseReview / Canteen / Stall / Dish / CanteenReview / Report`。

**为什么不用 `SQLAlchemyModelFactory`**：项目数据层是异步 `AsyncSession`，
而 factory_boy 的 `SQLAlchemyModelFactory` 依赖同步 session 做 `add/commit`，会直接报错。
因此采用**「先 build 内存实例 → 再由测试显式异步持久化」**：

```python
user  = await fx.create(UserFactory, username="alice")     # 落库并 commit
items = await fx.batch(ItemFactory, 3, owner_id=user.id)   # 批量
```

`fx` 夹具默认 **commit**（HTTP 请求走另一个会话，不提交则接口看不到播种数据）。

### 4.2 每个用例独立、自动清理

- `tests/conftest.py` 的 `test_engine` 是 **function 级**，每次 `drop_all + create_all`，
  用例天然跑在干净库上，无需手动回滚，也不会互相串扰。
- Redis 内存降级字典**不支持 TTL**，验证码/限流计数/黑名单会无限期残留。
  因此 unit 与 integration 的 conftest 都有 `clean_memory_redis` 自动夹具，每个用例前后清空。

### 4.3 E2E 数据隔离

E2E 通过环境变量把后端指向独立的 `e2e_test.db`，**绝不污染开发库**；
`e2e/npm run reset-db` 可一键重置。

---

## 5. 环境配置

### 5.1 零外部依赖即可运行（默认）

后端测试**不需要** PostgreSQL / Redis / MinIO / Meilisearch。原因：

| 外部依赖 | 测试期行为 |
|---|---|
| 数据库 | 临时 SQLite 文件（`sqlite+aiosqlite`），由 `test_engine` 夹具创建 |
| Redis | 根 conftest 主动禁用真实连接，强制走 `app/core/redis.py` 的内存降级 |
| MinIO | `StorageClient` 懒连接失败即降级为本地磁盘目录（测试中重定向到 `tmp_path`） |
| Meilisearch | `SearchClient.enabled=False`，索引操作静默跳过 |
| SMTP / Gemini | 分别用 monkeypatch 替换 `send_email` 与 `_call_gemini` |

### 5.2 需要真实外部服务时（可选）

若想验证真实 PostgreSQL / Meilisearch，可用 `deploy/docker-compose.yml` 起依赖服务，
再覆盖以下环境变量后跑同一套用例：

```bash
export DB_URL="postgresql+asyncpg://campus:campus@localhost:5432/campus_test"
export REDIS_URL="redis://localhost:6379/1"
export MINIO_ENDPOINT="localhost:9000"
export MEILI_HOST="http://localhost:7700"
```

### 5.3 关键环境变量（测试期）

| 变量 | 测试值 | 用途 |
|---|---|---|
| `CACHE_ENABLED` | `false` | 关闭热点缓存，避免内存降级字典让列表断言读到旧数据 |
| `CAPTCHA_ENABLED` | `false`（默认） | 关闭滑块；滑块用例内显式开启 |
| `DEBUG` | `true`（E2E） | 让 `send-code` 回传 `debug_code`，前端自动回填验证码 |
| `SECRET_KEY` | 测试专用 | 生产弱密钥校验会拒绝启动 |

---

## 6. 如何运行

### 6.1 后端

```bash
cd backend

# 全量（推荐按层跑，见 §8 已知环境风险）
python -m pytest tests/unit -q                       # 单元层，~2s
python -m pytest tests/integration -q                # 集成层，~7min
python -m pytest tests --ignore=tests/unit --ignore=tests/integration -q   # 既有回归，~8min

# 按标记筛选
python -m pytest tests -m unit -q                    # 只看单元
python -m pytest tests/integration -m "not slow" -q  # 跳过慢用例
python -m pytest tests -m slow -q                    # 只跑慢用例
```

### 6.2 后端覆盖率

```bash
cd backend
coverage run    -m pytest tests/unit -q
coverage run --append -m pytest tests/integration -q
coverage run --append -m pytest tests --ignore=tests/unit --ignore=tests/integration -q
coverage report            # 终端表格（含缺失行号）
coverage html              # 生成 htmlcov/index.html
```

> **注意**：不要在同一命令里用 `pytest --cov` 跨进程累加——
> `coverage` 的并行数据文件在合并后会删除临时文件，在受限环境（如沙箱/只读回收站）
> 会触发 `INTERNALERROR`。用 `coverage run --append` 不产生并行临时文件，更稳。

### 6.3 前端组件测试

```bash
cd frontend
npm run test            # 单次运行
npm run test:watch      # 监听模式
npm run test:coverage   # 生成覆盖率（coverage/index.html）
```

### 6.4 端到端测试

```bash
cd e2e
npm install
npx playwright install chromium      # 首次需要下载浏览器

npm run reset-db     # 可选：重置 E2E 数据库
npm test             # 运行全部场景
npm run test:headed  # 有界面模式（调试选择器时很有用）
npm run report       # 查看 HTML 报告
```

Playwright 会通过 `webServer` **自动拉起**后端（uvicorn:8000）与前端代理层（:5173）；
本地若已启动，会因 `reuseExistingServer` 直接复用。

---

## 7. CI 中的自动化（`.github/workflows/ci.yml`）

| Job | 内容 |
|---|---|
| `backend` | ruff lint → 单元层 → 集成层（`-m "not slow"`）→ 既有回归 → slow 用例 → **覆盖率门禁 `≥70%`** → 构建镜像 |
| `frontend` | `tsc --noEmit` → **Vitest 组件测试 + 覆盖率** → `vite build` |
| `e2e` | 安装 Playwright 浏览器 → 拉起前后端 → 运行 8 个端到端场景 → 上传报告 |
| `migrations` | `alembic upgrade head` + `alembic check`（模型变更必须出迁移） |
| `dependency-audit` | `pip-audit` + `npm audit --audit-level=high` |
| `secret-scan` | gitleaks 密钥扫描 |

### 7.1 覆盖率现状与门槛（实测数据）

| 端 | 用例数 | 语句覆盖 | 说明 |
|---|---|---|---|
| 后端 | **373**（单元 + 集成 + 既有回归，2026-09-05 实测全绿） | **70%**（4148 语句 / 1235 未覆盖） | 硬门禁 `--fail-under=70` |
| 前端 | 14 | 整体 **2.37%**；其中 `components/` **44.5%** | 仅上报，暂无硬门禁 |

**为什么后端门槛是 70% 而不是 80%**
需求建议 80%，但当前实测只有 70%。若直接写 80%，流水线**第一次运行就是红的**——
长期红灯的门禁很快会被忽略或删掉，反而失去保护意义。
因此先以 **70% 作为"防下滑基线"**，再用棘轮策略逐步上调至 80%（每提升到位就改一次数字）。

**提升覆盖率的优先顺序**（按当前覆盖率倒序，投入产出比最高）：

| 模块 | 当前 | 建议 |
|---|---|---|
| `app/core/cache.py` | 40% | 缓存命中/穿透/雪崩保护分支，纯逻辑易补 |
| `app/core/storage.py` | 48% | MinIO 客户端可用 monkeypatch 假 client 覆盖 |
| `app/core/sync_db.py`、`database.py` | 52% / 58% | 同步会话工厂、连接生命周期 |
| `pages/`、`context/`、`hooks/`（前端） | 0% | 页面级组件测试，按业务优先级逐个补 |

> 覆盖率是**手段不是目的**：优先补"改了会出事"的核心链路（鉴权、权限、交易），
> 而不是为了刷数字去覆盖 `asgi.py` 这类无逻辑的胶水文件。

---

## 8. 已知环境风险与既有缺陷

### 8.0 Ruff 规则集已显式固定（原为版本漂移风险，2026-08-29 已修复）

**根因**：`pyproject.toml` 原先**没有** `[tool.ruff]` 配置，ruff 会采用
"当前版本的默认规则集"。该默认集随版本扩大（0.16 相比 0.5 新增 `UP*` / `S` /
`ASYNC` / `BLE` / `RUF` 等），导致 CI 依赖解析到新版 ruff 时**突然变红**
（历史代码 363 处报错），且**连续 5 次流水线失败**。

**修复方式**（`backend/pyproject.toml`）：

1. **显式列出规则集** `select = ["E4","E7","E9","F","W","I","B","UP","ASYNC","RUF100"]`，
   让门禁结果与 ruff 版本解耦，不再随版本漂移。
2. **`B008` 误报白名单**：FastAPI 依赖注入**必须**写成参数默认值
   （`Depends` / `Query` / `Path` / ...），这不是"可变默认参数"陷阱。
   通过 `flake8-bugbear.extend-immutable-calls` 加白名单后，
   单此一项即消除 **176 处**误报（占原报错的近一半）。
3. **批量自动修复** `ruff check app --fix`：246 处机械性问题
   （`Optional[X]` → `X | None`、`List` → `list`、导入排序、失效 `noqa` 等）。
4. **人工修复 12 处**自动修复无法处理的项，其中含 2 个真实缺陷：
   - `admin/router.py`：`promote_user_to_admin` 被重复定义（F811）；
   - `message/service.py`：`page_obj` 死变量（F841）；
   - 另含 4 处补全异常链（B904）、3 处 async 阻塞 IO 改线程池（ASYNC230/240）。

**当前状态**：`ruff check app` → **All checks passed!**（363 → 0）。

**注意事项**：

- `UP046` / `UP047`（PEP 695 泛型语法）已显式 `ignore`：改动面大且非缺陷，单独排期。
- **自动修复会误删有意的再导出（re-export）**：`admin/schemas.py` 的
  `EmailRegisterConfig` 原本带 `# noqa: F401` 标记导出意图，仍被删除并导致
  测试 `ImportError`。已恢复该导入；**后续遇到"模块导入名消失"应优先怀疑此类误删**。

### 8.1 aiosqlite 原生崩溃（Windows，偶发）

把**全部 373 个用例放进同一个 pytest 进程**时，偶发
`Fatal Python error: Aborted`，崩溃点在 `aiosqlite` 的后台连接工作线程，
表现为进程直接退出、没有任何失败用例。

- **与测试逻辑无关**：分层单独跑三层全部通过；同一套用例重跑即可通过。
- **规避方式**：按层分进程执行（CI 与本文档推荐方式），避免超长单会话。
- **若需根治**：可把 `test_engine` 改为 session 级引擎 + function 级重建表结构，
  大幅减少 SQLite 连接 churn（改动涉及共享夹具，需完整回归后启用）。

### 8.2 已发现并固化的缺陷（`xfail`，修复后会转为 XPASS 提醒更新标记）

| 严重度 | 问题 | 位置 | 固化用例 |
|---|---|---|---|
| **P0** ✅ **已修复 (2026-08-29)** | `/api/reports/{id}/handle` 与 `GET /api/reports` 原**不校验管理员身份**：任意登录用户可查看全部举报工单，并用 `action=ban` 封禁任意用户（越权提权）。已改用 `Depends(require_admin)`（与 `/api/admin/*` 一致）。 | `app/modules/report/router.py` | `test_admin/test_moderation.py::test_ordinary_user_cannot_handle_report` 等（已转正向断言） |
| **P0** ✅ **已修复 (2026-08-29)** | 同一批端点原依赖 `get_current_user`（查 `users` 表），管理员令牌属 `AdminUser` 表导致**管理员无法处置工单**（报"用户不存在"）。改 `require_admin` 后管理员可正常处置/驳回。 | 同上 | `test_admin_resolves_report`、`test_admin_rejects_report`（xfail 已移除） |
| **P1** ✅ **已修复 (2026-08-30)** | **验证码邮件从未真实派发**：`send_code` 只生成并入库，`smtp_*` 配置仅用于决定是否回传 `debug_code`。生产配置 SMTP 后，用户既收不到邮件也拿不到 `debug_code`，注册流程会断 | `app/modules/auth/service.py::send_code`、`app/tasks/email.py` | `test_external/test_email_task.py`（9 条，含真实 SMTP 投递与 465/587 加密分支） |
| **P2** | `create_trade_session` 未校验 `buyer.id == item.owner_id`，**卖家可与自己议价**并生成自会话 | `app/modules/item/service.py` | `test_items/test_item_bargain.py::test_seller_cannot_trade_own_item` |
| **P2** | `verify_password(pwd, None)` 抛 `AttributeError`（未捕获）。因 `password_hash` 为 NOT NULL 故当前不可达 | `app/core/security.py` | `test_unit/test_security_unit.py::test_verify_password_with_none_raises_attribute_error` |

> 以上均以 `xfail(strict=False)` 固化：**不阻塞 CI，但在测试报告里始终可见**；
> 一旦有人修复，用例会转为 XPASS 提醒同步更新标记。

### 8.1.1 回传验证码：务必用 `EXPOSE_VERIFICATION_CODE`，不要用 `DEBUG`

`send-code` 响应里的 `debug_code` 由**独立开关** `EXPOSE_VERIFICATION_CODE` 控制，
**刻意没有**复用 `DEBUG`。原因：`DEBUG` 还连带控制管理员网关校验——
`gateway_enforced() = admin_gateway_enforce and not settings.debug`。
若为了让测试拿到验证码而全局开启 `DEBUG=true`，会**顺带把网关校验整个关掉**，
`test_admin_gateway.py` 里"未带网关令牌应被拒"的断言将全部失效（实测教训）。

因此各环境的正确配置：

| 环境 | `EXPOSE_VERIFICATION_CODE` | `SMTP_HOST` | 行为 |
|---|---|---|---|
| 生产 | `false` | 必填 | 验证码仅经邮件送达，响应恒为 `null` |
| 生产（邮件未配好） | `false` | 空 | `send-code` **直接报错**，不谎称"已发送" |
| 本地联调 | `true` | 可选 | 回传验证码，无需邮件即可走通注册 |
| 测试（conftest） | `true` | 强制置空 | 只回传、**绝不真实发信** |

**测试环境的两条硬约束**（见 `backend/tests/conftest.py`）：

1. `os.environ["SMTP_HOST"] = ""` —— 测试绝不能发真实邮件。
   用赋值而非 `setdefault`：`os.environ` 优先级高于 `.env` 文件，
   只 `setdefault` 挡不住 CI 环境变量带入真实 SMTP。
2. `os.environ["EXPOSE_VERIFICATION_CODE"] = "true"` —— 让注册类用例能取到验证码。

### 8.1.2 SMTP 配置缺失：告警而非拒绝启动

启动校验（`validate_admin_security`）在 SMTP 未配置时**只记 CRITICAL 日志**，
不抛 `SystemExit`。

取舍理由：邮件配错只影响注册/找回密码，登录、浏览、交易、消息都还能用。
用 `SystemExit` 拒绝启动会把"邮件没配好"放大成"全站不可用"，老用户一并被牵连
（实测会让 `test_lifecycle.py`、`test_shutdown_resources.py` 共 16 条启动/关停用例全挂）。
改为在**受影响的位置**暴露问题：`send-code` 显式报错 + 启动 CRITICAL 日志可接告警。
