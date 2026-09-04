# CampusSphere 后端深改交付文档（6 项任务）

> 目标：用 FastAPI 的 DI（`Depends`）、Pydantic v2 校验器、ASGI Lifespan、asyncio
> 把权限、业务规则、CPU 隔离、配置热更、WS 精准补发、全链路染色下沉到框架层。
> 约束：API 响应保持 `{"code":0,"message":"ok","data":{}}`；Redis 缺失时优雅降级；
> 每个任务配套 pytest 单测。

---

## Task 1 — 声明式权限作用域（替换 Service 层 `if user.role=="admin"`）

**改动点**
- 新增 `backend/app/core/deps.py`：`Scope(str,Enum)`（read/write/admin/audit）、
  `_SCOPE_IMPLIES` 隐含关系（admin⊃write⊃read，audit⊃read）、
  `Principal` 数据类、`get_principal(request, db)`（**同时**解析平台 `User` 与
  后台 `AdminUser` 两套身份，用 `selectinload(AdminUser.role)` 避免异步下的
  `MissingGreenlet`）、`require_scope(scope)` 参数化依赖工厂、
  `require_owner_or_scope(owner_id, principal, scope)`。
- `app/modules/item/router.py`：`update/delete` 从 `get_current_user`+`require_owner`
  改为 `principal: Principal = Depends(require_scope(Scope.WRITE))` +
  `require_owner_or_scope(item.owner_id, principal, Scope.ADMIN)`。
- `app/modules/audit/router.py`：`require_admin` → `Depends(require_scope("audit"))`。
- `app/modules/admin/service.py`：修复 `ensure_seed` 早退导致新权限永不同步的缺陷；
  新增 `_sync_roles(db)`（幂等、仅追加）与 `_SUPER_ADMIN_PERMS`/`_AUDITOR_PERMS`。

**对应 FastAPI 特性**：`Depends` + **参数化依赖工厂**（闭包返回 `_dependency`，
每次调用生成带名字的协程依赖）；请求级依赖缓存。`require_scope` 把"需要什么权限"
声明在**路由层**，Service 层因此对权限零耦合。

**验证**：`tests/unit/test_scope_deps_unit.py` 12 passed；`test_audit_logs` 经
`register_exception_handlers` 后 BizError 被正确包装。

---

## Task 2 — Pydantic 业务规则引擎（金额/跨字段校验左移进类型系统）

**改动点**
- `config/school.yaml` 增加 `items.rules`：`electronics_min_images: 0`（默认关闭，
  因前端 `MarketPublish.tsx` 只要求 ≥1 图，开启 3 会破坏真实用户/测试）、
  `forbid_zero_price_on_sale: true`。
- `app/modules/item/schemas.py`：`price` 保持**整数分**（前端已 `toCents()` 转换，
  后端不再 ×100，已与用户确认——原"元→分"前提不成立，改为只加防御校验）；
  `_validate_cents` 用 `field_validator(mode="before")` 拒绝 bool/float/str 的
  lax 模式隐式转换（实测 `{"price":true}`→1 会被静默接受，故显式拦截），上限
  `MAX_PRICE_CENTS=99_999_900`；`ItemCreate/_check_cross_field_rules`（`mode="after"`）
  强制电子产品图片数、`price==0` 且 `ON_SALE` 禁止。

**对应 FastAPI 特性**：**Pydantic v2 校验器**（`field_validator(mode="before")`
拿到原始输入做类型守卫；`model_validator(mode="after")` 做跨字段业务规则）。
校验错误由 `BizError` 统一抛出，经异常处理器归一成 `code/msg`。

**验证**：`tests/unit/test_item_schema_rules_unit.py` 15 passed。

> 两个**前提被证伪**（已与用户确认）：① 元→分转换前端已完成，后端无需再做；
> ② 邮件白名单本就是实时读 DB，"`email_register` 属性热更"前提不成立 → 改为
> school.yaml 静态配置热更（见 Task 4）。

---

## Task 3 — CPU 密集任务隔离（`asyncio.to_thread` 保护事件循环）

**改动点**
- `app/modules/auth/captcha.py`：抽出纯 CPU 同步函数
  `_render_slider_images(target_x, target_y) -> tuple[str,str]`（返回 data URI）；
  `generate_slider()` 改为 `await asyncio.to_thread(_render_slider_images, target_x, target_y)`
  （Pillow 出图原本阻塞事件循环）。

**对应 FastAPI 特性**：`asyncio.to_thread` 把阻塞型 CPU 工作 offload 到线程池，
保持异步端点高并发。控制实验（在同一协程里同步跑 Pillow）证明事件循环被拖死，
`to_thread` 后 tick 数恢复正常。

**验证**：`tests/unit/test_captcha_thread_offload_unit.py` 4 passed（含控制实验）。

---

## Task 4 — 配置热更新（Redis Pub/Sub + Lifespan 后台任务）

**改动点**
- 新增 `app/core/config_reload.py`：`CONFIG_RELOAD_CHANNEL="config:reload"`、
  `publish_config_reload(reason)`（失败返回 0 不抛）、`reload_settings`
  （`asyncio.to_thread(settings.load_school_config)` 就地刷新单例）、
  `_listen()` 长驻订阅循环（Redis 不可用时优雅降级 + 30s 慢重试 + 坏消息自愈）、
  `start/stop_config_reloader()` 幂等。
- `app/main.py`：lifespan 里 `await start_config_reloader()`，finally 里
  `await stop_config_reloader()`。
- `app/modules/admin/router.py`：新增 `POST /api/admin/config/reload` →
  `publish_config_reload` + 本地 `reload_settings` 兜底（receivers==0 时标记降级）。

**对应 FastAPI 特性**：**ASGI Lifespan** 承载后台常驻协程（配置订阅监听），
与应用生命周期同生共死；配合 `asyncio.to_thread` 刷新配置单例，模块导入期绑定的
`settings` 引用无需重启即生效。

**验证**：`tests/unit/test_config_hot_reload_unit.py` 6 passed（含全局单例污染还原）。

---

## Task 5 — WebSocket 精准补发（LocalSeq + Redis ZSet，应用层 Ack）

**改动点**
- 新增 `app/modules/message/seq.py`：`LocalSeqStore`（前缀 `ws:seq:`，上限 500），
  `append` 用 Redis `INCR` 作 score + `ZADD`，`since(conversation_id, last_seq)`
  用开区间 `(last_seq` 取缺量，内存降级）；模块单例 `seq_store`。
- `app/modules/message/ws.py`：新增 `_compensate_by_seq(ws, conv, last_seq)`；
  `websocket_endpoint` 增加 `conv`/`last_seq` 参数，连接建立后按游标补发
  （旧的 `_compensate` 时间戳口径保留为 deprecated，且**修复了它从未被调用**的真实缺陷）；
  `message:send` 路径先 `seq = await seq_store.append(...)` 再写 payload，
  在线推送与离线补发共用同一 seq。

**对应 FastAPI 特性**：WebSocket 端点即普通 `Depends`-无依赖的 ASGI 处理器；
补发游标 (=应用层 Ack) 由客户端随重连上报 `last_seq`，服务端 ZSet 区间取缺量——
精确不重不漏，替代易丢/易重的 `since=时间戳`。

**验证**：`tests/unit/test_ws_seq_unit.py` 12 passed；
`tests/test_websocket.py` 新增 3 个集成测试全过（含"修前 `_compensate` 死代码"守护）。
⚠️ **测试客户端坑**：Starlette TestClient 下发送方必须 `receive_json()` 排空自己的
回声，否则 `publish`→`send_json` 在单线程 portal 积压并级联成 DB 死锁（与业务代码无关）。

---

## Task 6 — 全链路可观测染色（X-Request-ID → SQL 注释）

**改动点**
- `app/core/logging.py`：`contextvars.ContextVar _trace_id_var`；
  `sanitize_trace_id(value)`（正则 `[^A-Za-z0-9_.:-]`，截断 64 字符——**必须**，
  因为 X-Request-ID 来自客户端请求头，`*/ DROP TABLE users; --` 可闭合注释块注入）；
  `bind_request`/`clear_request`/`get_trace_id()`。
- `app/core/database.py`：用 dialect 级 **`do_execute` / `do_execute_no_params` 接管**
  注入 `/* trace_id=xxx */`（返回值 `True` 告知 SQLAlchemy 已处理）。

**对应 FastAPI 特性**：`contextvars` 跨 `Depends`/异常处理器/DB 驱动贯穿同请求上下文；
中间件写入 `X-Request-ID`，structlog 与 SQL 注释同源读取，串起
Nginx → 业务日志 → 慢 SQL 三条线。

**⚠️ 关键发现（已实测）**：SQLAlchemy 2.0.30 的 `before_cursor_execute` **返回值被忽略**
——监听器被调用、也返回改写语句，但数据库执行原语句（SELECT 42→99 oracle 验证）。
故改用 `do_execute` 接管。

**验证**：`tests/unit/test_trace_id_unit.py` 14 passed（Mock cursor 断言注入+接管；
do_execute 接管改变真实执行的 SELECT 42→99 oracle）。

---

## 验证总览

| 范围 | 结果 |
|------|------|
| `tests/unit/`（含 6 任务单测） | 145 passed |
| `tests/test_websocket.py`（含 3 个 Task 5 集成测试） | 7 passed |
| `tests/unit/test_trace_id_unit.py`（Task 6） | 14 passed |
| 全套 `pytest tests`（基线 305 passed + 1 xfailed） | **371 passed, 1 xfailed, 9 warnings**（222.19s），`FULLSUITE_EXIT=0`，净 +66，零回归 |

## 两个跨任务的可复用坑（已沉淀为 skill `sqlalchemy-testclient-gotchas`）
1. SQL 注释注入必须用 `do_execute` 接管，`before_cursor_execute` 返回值无效。
2. TestClient WS 测试必须排空发送方自身回声，否则级联 DB 死锁。
