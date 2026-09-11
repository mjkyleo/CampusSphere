# CI 测试分片方案与生产验证手册

> 基于当前仓库实际代码与本机实测数据整理（2026-09-10）。配套改造见 `.github/workflows/ci.yml`。

## 一、测试耗时分布与分片并行方案

### 1.1 实测耗时分布

全量 `pytest tests` 在本机（Windows / Python 3.11 / 临时 SQLite）实测约 **12.3 分钟**，超过 10 分钟上限会被中断。分层实测数据：

| 范围 | 命令 | 用例数 | 实测耗时 | 主要耗时来源 |
| --- | --- | --- | --- | --- |
| unit | `pytest tests/unit` | 147 | **3.13s** | 纯逻辑，bcrypt 哈希占大头（0.4~0.45s/用例） |
| integration（含 slow） | `pytest tests/integration` | 129 | **≈348s** | DB 集成；`sync_item_search`/`send_notify` 的 `.delay()` 在无 broker 时连接重试（每次数秒）是主要放大项 |
| regression（根用例） | `pytest tests --ignore=unit --ignore=integration` | 113 | **≈385s**（198s + 187s 两批） | 端到端业务链路，多次 HTTP 往返 |
| slow | `pytest tests -m slow` | 6 | 长 I/O | 文件上传等 |
| **合计（串行）** | — | **389** | **≈736s ≈ 12.3 min** | — |

> integration 耗时由「`tests/unit tests/integration` 合计 351s」减去 unit 的 3.13s 推得；slow 6 个用例已包含在上述 integration 的 129 内（`--collect-only` 显示 integration 共 129，其中 6 个被 `-m "not slow"` deselect）。

### 1.2 分片划分（依据：耗时量级 + 失败定位 + 依赖特征）

| 分片 | 选择命令 | 用例数 | timeout-minutes | 划分依据 |
| --- | --- | --- | --- | --- |
| `unit` | `pytest tests/unit -q` | 147 | **5** | 秒级、纯逻辑，应最先失败、最先反馈 |
| `integration` | `pytest tests/integration -q -m "not slow"` | 123 | **20** | 最重的 DB/降级集成；单独分片避免拖慢 unit；`not slow` 排除长 I/O |
| `regression` | `pytest tests -q --ignore=tests/unit --ignore=tests/integration -m "not slow"` | 113 | **20** | 根回归业务链路；`not slow` 避免与 slow 分片重复 |
| `slow` | `pytest tests -q -m slow` | 6 | **15** | 长 I/O（上传等）隔离，避免偶发超时误判 |

- **无重复校验**：`--collect-only` 实测 unit 147 + integration 123 + regression 113 + slow 6 = **389**，与全量一致；integration 内 6 个 slow 被 deselect、regression 也用 `not slow`，因此 slow 只在 `slow` 分片跑一次。
- **并行收益**：四个分片在不同 runner 上并行，墙钟时间由最长分片（regression ≈ 6.4 min）决定，实际约 **7 分钟**，远低于串行 12.3 分钟，且不会再触发 10 分钟中断。
- **`fail-fast: false`**：任一分片失败其余仍跑完，便于一次拿到全部失败信息再定位。

### 1.3 覆盖率合并方式

每个分片用 `COVERAGE_FILE` 产出**独立**数据文件，避免并行 `.coverage.<host>.<pid>` 临时文件在受限环境删除失败导致 `INTERNALERROR`（原 CI 踩过的坑，见文件头注释）：

```bash
# 分片内（working-directory: backend）
COVERAGE_FILE=.coverage.<shard> coverage run -m pytest <path> -q <args> \
  --junitxml=junit-<shard>.xml 2>&1 | tee pytest-<shard>.log
```

- 上传：`test-results-<shard>`（JUnit XML + pytest 日志）、`coverage-data-<shard>`（`.coverage.<shard>`），均 `if: always()`。
- `backend-coverage` job：`actions/download-artifact@v4` 以 `pattern: coverage-data-*`、`merge-multiple: true` 拉到 `backend/` → `coverage combine`（合并 `.coverage.*` 为单个 `.coverage`）→ `coverage report --fail-under=70`（门禁）→ `coverage xml` + `coverage html` → 上传 `backend-coverage`。
- **不使用** `pytest-cov` 的 `--cov-append`（并行临时数据文件在回收站不可用环境会删不掉）。

### 1.4 触发、并发与缓存

- **触发**：`push`/`pull_request` 到 `main`、`dev`，另加 `workflow_dispatch` 手动触发。
- **并发**：`concurrency.group: ci-${{ github.ref }}`；`cancel-in-progress: ${{ github.event_name == 'pull_request' }}` —— PR 取消旧运行省算力，**main/dev 推送不取消**（避免发布验证被中断）。
- **依赖缓存**：`actions/setup-python@v5` 的 `cache: pip` + `cache-dependency-path: backend/pyproject.toml`；前端 `cache: npm` + `package-lock.json`。四个测试分片共用同一份 pip 缓存键，安装阶段命中缓存。

---

## 二、生产环境验证手册

### 2.1 MeiliSearch 索引同步

**准备**
1. 部署 Meilisearch，配置后端：`MEILI_HOST`（默认 `http://localhost:7700`）、`MEILI_API_KEY`，或在 `config/school.yaml` 的 `meilisearch.host / api_key` 配置（见 `app/core/config.py`）。
2. 重启后端；启动 Celery worker 监听 `search` 队列（Linux：`celery -A app.tasks.celery_app.celery_app worker -Q search,notify,email`；Windows 必须加 `-P solo`）。

**验证步骤**
1. 用卖家账号 `POST /api/items` 发布物品，记录 `item_id` 与标题。
2. 等待 2–3 秒（任务异步），查询 Meili：
   `curl "$MEILI_HOST/indexes/items/documents/<item_id>" -H "Authorization: Bearer $MEILI_API_KEY"`
3. 或直接 `GET /api/items/search?q=<标题关键词>`，应返回该物品。
4. 历史数据回填：`python backend/scripts/rebuild_search_index.py`（argparse 支持 `items`）。
5. 下架/删除：`PUT /api/items/{id}` 改 `status` 为下架，或 `DELETE /api/items/{id}`；再查该文档应为 404/不存在。

**判定标准**
- 发布后 `items` 索引存在该文档，且 `status == ON_SALE`；后端日志出现 `meili_connected`，无 `meili_unavailable`（否则说明走了降级）。
- 非在售 / 软删除的物品**必须**从索引移除（`sync_item_search` 会投递 `delete_doc`）。
- `/api/items/search` 返回结果来自 Meili（而非 SQL LIKE 降级）：可临时在日志中确认无 `meili_unavailable`。

**失败排查与回滚**
- 文档缺失：先看 worker 是否消费 `search` 队列、Redis broker 是否通；后端日志若出现 `search_sync_dispatch_failed` 说明 `.delay()` 投递失败（broker 不可达），此时索引不会更新但业务不受影响。
- 日志出现 `meili_unavailable` / `meili_index_failed`：Meili 连接失败，已降级；检查 host/key 与网络。
- **回滚**：将 `MEILI_HOST` 置空或还原 school.yaml 并重启后端，即回到 SQL LIKE 降级（搜索功能不受影响）；Meili 中已有索引保留，可后续用 `rebuild_search_index.py` 重建。
- 索引脏数据：执行全量重建脚本，或删除 `items` 索引后由写操作/重建脚本重新填充。

### 2.2 AI 预审链路（内容安全）

**准备**
- 配置 AI（OpenAI 兼容：`OPENAI_BASE_URL` / `OPENAI_API_KEY` 等，按 `app/modules/ai` 配置段）；若暂无 AI，也**必须**验证规则引擎降级分支。

**验证步骤**
1. 管理员登录获取 token：`POST /api/admin/login`（dev 若开启网关强制，需先 `POST /api/admin/discover` 换 `X-Admin-Gateway`）。
2. 开启预审：`PUT /api/admin/content-moderation/config`，body `{"enabled": true, "action": "reject"}`，带 `Authorization: Bearer <admin>`；再 `GET` 同一路径确认 `enabled=true`。
3. 普通用户发违规内容：`POST /api/shares`（或 `/api/teams`、`/api/jobs`），在 `title`/`description` 放入敏感词（参考 `app/modules/ai/service.py::_rule_moderation` 的词表）。
4. 关闭 AI 总开关（后台 `PUT /api/admin/ai/config` 或 `app_config` 表 `ai.feature.enabled=false`），重复步骤 3。
5. 关闭预审（`{"enabled": false}`），重复步骤 3。

**判定标准**
- 预审开启 + 命中敏感词：接口返回 **HTTP 403 / 业务码非 0**，`message` 含「发布内容涉嫌违规」，且**数据库未新增记录**。
- AI 不可用（总开关关闭或无 Key）时：仍被拦截（规则引擎降级生效），日志出现 `content_safety_ai_disabled_fallback_rule` —— 证明审核不依赖 AI 可用性。
- 预审关闭：正常发布成功（`code=0`）。
- 注意：`action="pending"` 目前为**预留扩展**，实际仍按 `reject` 处理（见 `ContentModerationConfig` 注释与 `check_content_safety` 实现）。

**失败排查与回滚**
- 发布卡住/500：检查 `check_content_safety` 是否捕获 `BizError` 并降级到 `_rule_moderation`（代码已实现）；若未降级，看 AI 调用是否抛了非 `BizError` 异常。
- 误杀正常内容：调整/清空敏感词表，或把 `action` 改为 `pending`（待实现）后观察。
- **回滚（无需发版）**：`PUT /api/admin/content-moderation/config {"enabled": false}` 即关闭；配置走 `AppConfig` 表，实时生效。
- 配置异常：直接改库 `UPDATE app_config SET value=... WHERE key='content.moderation'`，或删除该行回退默认值（默认 `enabled=false`）。

### 2.3 `/metrics` 返回真实数据（非占位）

**步骤**
1. 确保生产 `DEBUG=false`，`GatewayMiddleware` 生效（生产默认）。
2. 先造流量：`curl` 几个业务接口（如 `GET /api/items`、`GET /api/items?page=1`），至少数次。
3. 拉取指标：`curl -s http://<host>/metrics | grep campus_`（路由见 `app/modules/launcher/router.py` 的 `GET /metrics`）。

**判定标准（必须同时满足）**
- `campus_http_requests_total{method="GET",endpoint="/api/items",status="200"}` 的值为**非 0 整数**，且再次请求后**递增**（证明是真实埋点，不是占位/常量）。
- 存在 `campus_request_latency_seconds`（Histogram：`_bucket` / `_sum` / `_count`），`_count` 非 0。
- **`endpoint` label 必须是路由模板**，例如 `/api/items/{item_id}`；**不得**出现具体 UUID 或数字 ID（否则 cardinality 爆炸，说明 `_endpoint_label()` 没取到 `request.scope["route"]`）。
- 进阶（可选）：快速刷新触发限流后，应出现 `status="429"` 的计数；未带网关令牌访问 `/api/admin/*` 应出现 `status="404"`（网关隐藏）的计数 —— 对应中间件里三个提前返回出口的埋点。

**失败排查与回滚**
- `/metrics` 只有 `# HELP` 无样本 / 全 0：确认有业务流量经过中间件；检查 `/metrics` 是否被 `PUBLIC_PATHS` 跳过导致自身不计数（正常）——但**业务请求**应计数；确认 `core/middleware.py::_record_metrics` 在四个出口（限流 429、认证限流 429、网关 404、正常返回）都被调用。
- `endpoint` 是具体 ID：`_endpoint_label()` 未命中路由，排查路由注册/`request.scope["route"]` 是否为 `None`（可临时加日志）。
- Prometheus 侧抓不到：检查 scrape target 是否为 `http://<host>/metrics`，以及容器网络。
- **回滚**：指标埋点是 `try/except` 静默的，失败不影响业务；如需彻底关闭，回滚 `core/middleware.py` 的埋点改动（对应提交 `67278d7 feat(metrics): ...`），或 `git revert` 该提交。

---

## 三、如何验证 CI 工作流能在分支上正常触发并通过

1. **触发**：新建分支并推送（或开 PR 到 `main`/`dev`）：
   ```bash
   git checkout -b ci/verify-sharding
   git commit --allow-empty -m "chore: trigger ci sharding verification"
   git push -u origin ci/verify-sharding
   ```
   由于 `on.push.branches` 包含 `dev`，推到 `dev` 同样会触发；PR 到 `main`/`dev` 也会触发。
2. **观察点（GitHub → Actions → CI）**：
   - 作业列表应包含：`backend-lint`、`backend-test (unit)`、`backend-test (integration)`、`backend-test (regression)`、`backend-test (slow)`、**四个 test 分片并行**（同一时间窗内启动）、`backend-coverage`、`backend-image`、`frontend`、`e2e`、`worker-image`、`migrations`、`dependency-audit`、`secret-scan`。
   - 分片日志：unit 显示 `147 passed`；integration 显示 `123 passed, 6 deselected`；regression 显示 `113 passed`；slow 显示 `6 passed`（数字以实际为准，量级应一致）。
   - `backend-coverage` 日志：`coverage combine` 成功 → `coverage report` 输出 TOTAL 百分比 → `Required test coverage of 70% reached`（当前实测 TOTAL ≈ 70%，若低于 70 会失败，属预期门禁）。
3. **产物（Artifacts）**：应出现 `test-results-unit/integration/regression/slow`（各含 `junit-*.xml` 与 `pytest-*.log`）、`coverage-data-*`、`backend-coverage`（`coverage.xml` + `htmlcov/`）、`frontend-coverage`、`playwright-report`、`frontend-dist`。
4. **并发验证**：同一 PR 连续推送两次，前一次运行应被 `cancel-in-progress` 取消（main 推送则不取消）。
5. **本地替代验证（无 GH runner 时）**：
   - YAML 语法：`python -c "import yaml;yaml.safe_load(open('.github/workflows/ci.yml'))"`（已验证通过）。
   - 分片选择合法性：在 `backend/` 下执行四条 `--collect-only` 命令，确认计数分别为 147 / 123 / 113 / 6 且合计 389 无重复（已验证）。
   - 单分片实跑：`pytest tests/unit -q` → `147 passed in 3.13s`（已验证）。
   - 可选：安装 `act` 后 `act -j backend-test --matrix shard:unit` 本地模拟 job（需 Docker）。
