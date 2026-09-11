# CampusSphere 能力链路闭环排查结论与优化计划

> 排查时间：2026-09-09
> 排查范围：搜索同步、metrics 埋点、AI 分类调用方、Celery 空队列
> 排查依据：源码读取 + grep 调用链 + `ruff` + `pytest` 验证

---

## 一、任务概述

针对上一阶段架构审视中识别出的四条「已实现但未真正闭环」的能力链路，本次排查逐一定位根因、设计落地改动方案，并明确验收标准与责任人。其中 **metrics 埋点已在本次会话中直接落地**，其余三条因涉及业务决策与较大改动面，先输出计划并按优先级推进。

---

## 二、链路逐项排查

### 1. Metrics 埋点

#### 现状与根因

- `app/modules/launcher/metrics.py` 已定义：
  - `REQUEST_COUNT = Counter("campus_http_requests_total", ..., ["method", "endpoint", "status"])`
  - `REQUEST_LATENCY = Histogram("campus_http_request_latency_seconds", ..., ["endpoint"])`
- 全局 grep（`REQUEST_COUNT\.inc|REQUEST_LATENCY\.observe`）**无命中**，说明指标实例从未被代码写入。
- 根因：`GatewayMiddleware.dispatch` 已经计算了请求耗时 `cost_ms`，但缺少把耗时与状态写入 Prometheus 指标的步骤。此前 `/metrics` 端点只能返回进程默认指标，自定义业务指标恒为 0。

#### 已落地改动

- 文件：`app/core/middleware.py`
- 内容：
  - 引入 `REQUEST_COUNT` / `REQUEST_LATENCY`；
  - 新增 `_endpoint_label(request)`：优先取 FastAPI 匹配到的路由模板（如 `/api/items/{item_id}`），避免动态 ID 导致 Prometheus label cardinality 爆炸；未匹配路由时回退原始 path 并截断；
  - 新增 `_record_metrics(...)`：失败静默忽略，不影响主请求；
  - 在 `dispatch` 的三个提前返回点（限流 429、认证限流 429、管理员网关 404）与正常返回点统一埋点。

#### 验收标准

- [x] `ruff check app/core/middleware.py` 通过（已验证）。
- [x] `pytest tests/unit` 145 通过（已验证）。
- [x] `pytest tests/integration/test_auth` 26 通过（已验证）。
- [ ] 启动应用后访问 `/metrics`，可观察到 `campus_http_requests_total` 与 `campus_http_request_latency_seconds` 非零样本（需真实运行验证）。
- [ ] 验证限流 429 与管理员 404 路径也被计数（可通过 curl 触发后抓 `/metrics`）。

#### 责任人
- **已完成**：WorkBuddy（本次会话落地）。
- **后续验证**：Ky（启动后端后 curl 访问 `/metrics` 确认）。

#### 优先级
- **P0**（已落地）。

---

### 2. 搜索同步（Meilisearch 索引同步）

#### 现状与根因

- 已具备：
  - `app/search/client.py`：Meilisearch 客户端，支持 `index_document` / `delete_document` / `search`，无 Meili 时 `enabled=False`；
  - `app/tasks/search_sync.py`：定义了 `sync_user` / `sync_item` / `delete_doc` 三个 Celery 任务；
  - `app/modules/item/router.py` 的 `GET /api/items/search` 已接入 Meili 搜索，失败降级到 SQL `LIKE`。
- 根因：全局 grep `sync_user|sync_item|delete_doc` 在 `app/` 下**无 `.delay()` 调用方**。`item/service.py` 的 `create_item` / `update_item` / `delete_item`、`admin/service.py` 的 `admin_update_item` / `admin_delete_item` / `approve_item` / `reject_item` 均未触发索引同步。
- 结果：索引恒空，真实搜索 100% 走 SQL `LIKE` 降级；README 与文档中「发布即同步」「Meilisearch 全文搜索」未实际落地。

#### 影响

- 搜索功能名存实亡；
- 部署 Meilisearch 成为纯运维成本，无业务收益；
- 文档与代码再次漂移，写简历/面试时易引用不实描述。

#### 优化方案

**方案 A：让搜索真正可用（推荐）**

1. 在 `item/service.py` 的写操作后异步同步索引：
   - `create_item` → `search_sync.sync_item.delay(...)`
   - `update_item` / `admin_update_item` / `approve_item` / `reject_item` → 同步最新状态
   - `delete_item` / `admin_delete_item` → `search_sync.delete_doc.delay("items", item_id)`
2. 在 `admin/service.py` 的 `promote_user_to_admin` 或用户资料更新处，视需求同步 `users` 索引。
3. 索引 doc 字段与 `SearchClient._ensure_index` 中 `searchable` 字段对齐（title/description/category）。
4. 失败降级：任务内部已处理 `client.enabled` 判断；若 Meili 不可用，任务不抛异常，不影响主流程。
5. 增加初始化/重建索引脚本：
   - `backend/scripts/rebuild_search_index.py`：全量读取 items 写入 Meili，供首次启用或数据修复。

**方案 B：明确下线搜索模块**

1. 删除 `app/tasks/search_sync.py`、清空 `app/search/`（保留降级时直接走 SQL 的列表查询）；
2. 更新 README/文档，移除「Meilisearch 全文搜索」相关描述；
3. 从 `deploy/docker-compose.yml` 移除 meilisearch 服务，减少部署依赖。

> 建议：若当前阶段搜索不是核心体验，可先选方案 A 的最小闭环（只同步 items），保留 Meili；若资源有限则选方案 B。

#### 验收标准

- [ ] 发布/修改/删除物品后，Meilisearch 索引中对应文档被更新/删除（可用 Meili dashboard 或 `/api/items/search?q=...` 验证）。
- [ ] `grep -R "sync_item.delay\|delete_doc.delay" app/` 有命中。
- [ ] 新增/更新集成测试：Meili 可用时走索引搜索，Meili 不可用时降级到 SQL LIKE。
- [ ] 新增 `rebuild_search_index.py` 脚本并通过一次全量重建验证。
- [ ] 文档同步更新，消除「搜索同步」漂移。

#### 建议排期
- **1-2 天完成最小闭环**（items 索引同步 + 1 个重建脚本）。

#### 责任人
- **后端实现**：Ky / 后端开发
- **测试与文档同步**：Ky

#### 优先级
- **P1**（高，涉及能力与文档一致性）。

---

### 3. AI 分类调用方

#### 现状与根因

- 已具备：
  - `app/modules/ai/service.py` 的 `categorize_content`：支持 LLM 分类 + 规则引擎兜底，返回 `category / isSafe / summary / source`；
  - `app/modules/ai/router.py` 的 `POST /api/ai/categorize`：已暴露端点；
  - 前端发布页已有 `normalize_category` 把分类收敛到后台配置列表。
- 根因：`categorize_content` **未被任何业务发布路径调用**。`share/service.create_share`、`teammate/service.create_team`、`job/service.create_job` 均只做了分类归一化，没有调用 AI 预审。
- 结果：AI 内容安全审核能力未落地；社区内容仍依赖人工举报后置处理。

#### 影响

- AI 模块当前仅有 4 条显式入口（greeting / insights / item-description / course-summary），`categorize` 成为死接口；
- 违规内容（如代考、刷单、枪支等）无法发布前自动拦截；
- 内容分类依赖用户/前端选择，未利用 AI 自动纠正。

#### 优化方案

**目标**：在帖子/组队/兼职发布路径中**可选调用** `categorize_content`，对 `isSafe=False` 的内容进入「待审核」或「拒绝发布」状态；对分类结果用于辅助修正用户选择的分类。

1. **在业务 Service 层增加异步/同步预审钩子**：
   - `share/service.py`：`create_share` 在 `normalize_category` 后调用 `categorize_content`。
   - `teammate/service.py`：`create_team` 同样位置调用。
   - `job/service.py`：`create_job` 同样位置调用。
2. **预审结果处理策略**（可配置）：
   - `isSafe=False`：直接抛 `BizError(ErrorCode.FORBIDDEN, "内容涉嫌违规，请修改后重试")` 或进入 `PENDING_REVIEW` 状态。
   - `category` 与前端传入不一致时：若 AI 置信度高（可新增 `score` 字段）则自动覆盖，否则保留用户选择并记录日志。
3. **性能与降级**：
   - `categorize_content` 内部已有 LLM → 规则引擎降级；无 Key 时走规则兜底，不阻塞发布。
   - 建议用 `asyncio.wait_for` 限制单次调用最大 3 秒，超时直接走规则兜底。
4. **可观测性**：
   - 在 `AiGenerationLog` 中记录 moderation 调用来源（share/job/team）。

#### 验收标准

- [ ] `grep -R "categorize_content" app/modules/{share,teammate,job}` 有命中。
- [ ] 发布含敏感词（如「代考」）的内容时，接口返回明确拒绝或进入待审核。
- [ ] 发布普通内容时，分类被自动归一化（命中 `_CATEGORY_KEYWORDS` 时）。
- [ ] 新增集成测试覆盖：AI 可用时 LLM 分类、AI 不可用时规则兜底、敏感词拒绝。
- [ ] 后台配置增加「内容预审开关」与「处置方式（拒绝/待审核）」，避免一刀切。

#### 建议排期
- **1-2 天完成最小闭环**（share / teammate / job 三处调用 + 敏感词拒绝策略）。

#### 责任人
- **后端实现**：Ky
- **前端配合**：若增加「待审核」状态，需前端对应展示；当前若仅拒绝，前端无需改动。

#### 优先级
- **P1**（高，直接提升社区内容安全）。

---

### 4. Celery 空队列

#### 现状与根因

- `app/tasks/celery_app.py` 配置了三个队列：
  - `email`：有真实调用方（`auth/service.py::_dispatch_code_email` 调用 `email_tasks.send_email.delay`）。
  - `notify`：`app/tasks/notify.py::send_notify` 定义，但 `app/` 下**无 `.delay()` 调用方**。
  - `search`：`app/tasks/search_sync.py` 定义，但 `app/` 下**无 `.delay()` 调用方**。
- `app/tasks/summary.py::generate_trade_summary` 只在 docstring 示例中出现 `.delay()`，无真实调用方。
- 根因：这些任务模块是「提前建设」的异步化占位，但对应业务事件（通知、搜索同步、交易摘要）未接入队列。

#### 影响

- Worker 启动后 `notify`/`search` 队列长期空闲，资源分配依据不足；
- 搜索同步空队列与问题 2 是同一问题的不同侧面；
- `summary` 任务若长期不接入，应移除或明确接入点，避免成为死代码。

#### 优化方案

**目标**：每个队列要么有真实负载，要么被移除。

#### 4.1 notify 队列

**接入点建议**：
- 交易会话创建：买家发起交易后通知卖家；
- 入队申请：用户申请加入队伍后通知队长；
- 兼职申请：用户投递简历后通知发布者；
- 举报处理结果：管理员处理举报后通知举报人与被举报人。

**最小改动**：在 `item/service.py::create_trade_session`、`teammate/service.py::join_team`、`job/service.py::apply_job` 成功后调用：
```python
from app.tasks.notify import send_notify
send_notify.delay(str(target_user_id), title, content, channel="inapp")
```

**验收标准**：
- [ ] 上述三个业务事件触发后，Redis 频道 `notify:{user_id}` 收到消息（可用 fakeredis 单元测试断言）。
- [ ] WebSocket 在线用户能收到 `event: notify` 推送。

#### 4.2 search 队列

与「搜索同步」问题合并处理：在物品写操作处调用 `sync_item.delay(...)` / `delete_doc.delay(...)`。

#### 4.3 summary 队列

**两种选择**：

**A. 落地交易摘要**
- 在 `item/service.py::create_trade_session` 与交易状态变更处调用 `generate_trade_summary.delay(str(ts.id))`；
- 前端交易详情页读取 Redis 缓存中的摘要（需新增 API）。

**B. 移除空任务**
- 删除 `app/tasks/summary.py`；
- 从 `celery_app.py` 的 `autodiscover_tasks` 影响范围中移除；
- 从文档中删除相关描述。

> 建议：当前阶段交易详情页未显示摘要，**优先选 B 移除**，避免死代码；未来确有需求时再重新设计。

#### 整体验收标准

- [ ] `grep -R "send_notify.delay\|sync_item.delay\|delete_doc.delay\|generate_trade_summary.delay" app/` 的命中均为真实业务调用，而非 docstring/示例。
- [ ] `celery -A app.tasks.celery_app:celery_app inspect active` 或 flower 中可见对应队列有任务消费。
- [ ] 若选择移除 `summary`，则 `app/tasks/summary.py` 不存在或为空文件，且文档无残留描述。

#### 建议排期
- **notify 队列接入**：0.5-1 天。
- **search 队列接入**：与问题 2 同步，1-2 天。
- **summary 处理**：0.5 天（移除）或 1-2 天（落地）。

#### 责任人
- **后端实现**：Ky
- **产品确认**：若接入站内通知，需确认通知文案与接收方；若移除 summary，需确认无前端依赖。

#### 优先级
- **notify：P2**（中，提升用户体验）。
- **search：P1**（与搜索同步合并）。
- **summary：P2**（中，技术债清理）。

---

## 三、总体优先级与排期建议

| 优先级 | 事项 | 预计耗时 | 责任人 | 状态 |
|---|---|---|---|---|
| P0 | Metrics 埋点 | 已落地 | WorkBuddy | 完成 |
| P1 | 搜索同步闭环（items 索引同步 + 重建脚本） | 1-2 天 | Ky | 待做 |
| P1 | AI 分类调用方（share/team/job 预审） | 1-2 天 | Ky | 待做 |
| P2 | Celery notify 队列接入 | 0.5-1 天 | Ky | 待做 |
| P2 | Celery summary 任务移除或落地 | 0.5-2 天 | Ky | 待做 |

---

## 四、风险与注意事项

1. **Metrics 高基数风险**：本次已使用 FastAPI 路由模板作为 endpoint label，可避免 UUID/ID 导致 cardinality 爆炸。但仍需观察 `/metrics` 实际输出，确认异常 404 路径不会产生无限 label。
2. **Meilisearch 索引同步的幂等性**：`sync_item.delay` 可能在 update 时反复调用，Meili `add_documents` 对同一主键是覆盖写入，天然幂等；但需确保 doc 包含完整字段，避免部分更新导致旧字段残留。
3. **AI 分类延迟**：`categorize_content` 调用外部 LLM，若直接放在同步发布路径中，可能拖慢发布响应。建议保留其内部「LLM 失败 → 规则兜底」逻辑，并设置调用超时；必要时可改为 Celery 异步预审，但会增加架构复杂度。
4. **Celery 任务循环导入**：在 `item/service.py` 中引入 `app.tasks.search_sync` 时，注意避免与 `celery_app.py` 形成循环导入。建议以模块形式导入（如 `import app.tasks.search_sync as search_sync_tasks`）。
5. **文档同步**：每完成一项改动，同步更新 README / API_Reference / 开发指南，避免新一轮漂移。

---

## 五、已验证命令记录

```bash
# metrics 改动后验证
cd backend
python -m ruff check app/core/middleware.py   # All checks passed!
python -m pytest tests/unit -q              # 145 passed
python -m pytest tests/integration/test_auth -q  # 26 passed
```

后续真实运行验证：
```bash
python scripts/devctl.py up --backend-only
# 另开终端
curl http://127.0.0.1:8000/metrics | grep campus_http_requests_total
curl http://127.0.0.1:8000/metrics | grep campus_http_request_latency_seconds
```
