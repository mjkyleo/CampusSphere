# review-2026-09-28 修复日志

对应报告：[review-2026-09-28.md](./review-2026-09-28.md)。按报告"建议修复顺序"逐项修复；每项完成后记录改动、验证方式与结果。分支：`feat/frontend-redesign`（改动未提交，待全部完成后统一决定提交拆分）。

**图例**：⬜ 未开始 / 🔧 进行中 / ✅ 已完成 / ⏭️ 跳过（附原因）

## 进度总览

| # | 编号 | 问题 | 状态 |
| --- | --- | --- | --- |
| 1 | P0-3 | ReportModal hooks 顺序 → 全站白屏 | ✅ |
| 2 | P1-3 | AdminDashboard 封禁按钮反转 | ✅ |
| 3 | P1-6 | ShareFeed 下载 URL 被丢弃 | ✅ |
| 4 | P1-8 | 占位管理员凭据通过 blocklist | ✅ |
| 5 | P0-1 | JWT secret_key 无启动校验 | ✅ |
| 6 | P2-8 | purpose 自由串注入限流键 | ✅ |
| 7 | — | 阶段一：后端全量测试 | ✅ 390 passed |
| 8 | P0-2 | WS 补发无参与者校验 | ✅ |
| 9 | P1-1 | 物品审核绕过 | ✅ |
| 10 | P1-2 | 存储键信任链（3 处） | ✅ |
| 11 | P1-7 | 评价去重唯一约束 + 迁移 | ✅ |
| 12 | P1-9 | auto-ban 统计口径 + 举报去重 | ✅ |
| 13 | P1-4 | changePassword 假 stub | ✅ |
| 14 | P1-5 | 生产 mock 回退伪造成功 | ✅ |
| 15 | — | 阶段二：后端全量测试 | ✅ 404 passed |
| 16 | P2-1/2 | 交易会话生命周期 + 会话创建同事务 | ✅ |
| 17 | P2-3 | job_applications 并发双插 | ✅ |
| 18 | P2-4 | team_members 并发双插 + 人数无上限 | ✅ |
| 19 | P2-5 | schema 长度/负数/非法 status | ✅ |
| 20 | P2-6 | 下载计数丢失更新 + owner 硬删级联 | ✅ |
| 21 | P2-7 | CORS 在网关内侧丢失头 | ✅ |
| 22 | P2-9 | WS 封禁可收发/无节流/无长度/伪造已读 | ✅ |
| 23 | P2-10 | WS Redis 监听死亡不重启 | ✅ |
| 24 | P2-11 | AI 端点无用户配额 | ✅ |
| 25 | P2-12 | /api/files/raw 401 | ✅ |
| 26 | P2-13 | OAuth bind state 可选 | ✅ |
| 27 | P2-14 | 验证码票据 TOCTOU | ✅ |
| 28 | P2-15 | 网关头非 ASCII → 500 | ✅ |
| 29 | P2-16 | token 全在 localStorage | ⏭️ 见跳过说明 |
| 30 | P2-17 | canteen/course 列表加载全库评价 | ✅ |
| 31 | P2-18 | teammate 列表 N 次 COUNT | ✅ |
| 32 | P2-19 | 会话列表无分页 | ✅ |
| 33 | P2-20 | 仪表盘无界 COUNT | ⏭️ 见跳过说明 |
| 34 | P2-21 | WS 重连用旧 token | ✅ |
| 35 | P2-22 | server.ts 挂起/handleReport 丢字段/6 处硬编码 mock | ✅ |
| 36 | P2-23 | devctl 用占位 env 启 compose | ✅ |
| 37 | P2-24 | bootstrap 密码空值"无病"上线 | ✅ |
| 38 | P2-25 | nginx /metrics 死配置 | ✅ |
| 39 | P2-26 | CI 构建废弃 Dockerfile | ✅ |
| 40 | — | 阶段三：后端全量测试 | ✅ 404 passed |
| 41 | P3 | 简表 18 项（13 修 / 5 跳） | ✅ |

---

## 修复明细

### 1. P0-3 ReportModal hooks 顺序 → 全站白屏 ✅

- **文件**：`frontend/components/ReportModal.tsx`
- **改动**：把 `if (!reportModal.isOpen) return null;` 从 `useEffect` 之前移到之后（effect 内部本就有 `isOpen` 守卫），使全部 6 个 hook 在早退前声明；加注释说明约束。
- **验证**：`npx tsc --noEmit` 通过；仓库无该组件既有测试，属结构性修复（hook 数量在开合两态下恒为 6）。

### 2. P1-3 AdminDashboard 封禁按钮反转 ✅

- **文件**：`frontend/pages/AdminDashboard.tsx`
- **改动**：修正 3 处与 `UserStatus`（Normal=0/Banned=1）相反的三元——状态徽章（原被封号显示"正常"）、操作按钮文案+配色（原对被封号者显示"封禁账号"）、成功 toast（原解封后提示"已封禁"）。`handleToggleUserBan` 的 toggle 计算本身正确，未动。
- **验证**：`npx tsc --noEmit` 通过（exit 0）。

### 3. P1-6 ShareFeed 假下载 → 接到真实下载 URL ✅

- **文件**：`frontend/pages/ShareFeed.tsx`（`handleDownload`）
- **改动**：`api.shares.download` 返回的 `download_url` 此前被丢弃（只弹 toast + 本地计数）。现校验 URL 为 `http(s)` 开头后 `window.open(url, '_blank', 'noopener')` 真正触发下载；非 http(s)（如后端配置异常返回 `javascript:` 类地址）报"下载链接无效"；`code !== 0` 或缺 `download_url` 时透出后端 message。
- **验证**：`npx tsc --noEmit` 通过；下载链接协议白名单为纯前端校验逻辑，无既有测试覆盖该页面。

### 4. P1-8 占位管理员凭据通过 blocklist ✅

- **文件**：`backend/app/core/config.py`（`validate_admin_security`）、`backend/tests/test_admin_gateway.py`
- **改动**：
  - blocklist 补录 school.yaml 模板的 `-16plus` 精确变体（`change-me-admin-gateway-key-16plus` / `change-me-deploy-with-strong-pw-16plus`）；
  - 新增 `_is_placeholder` 前缀模式校验：`change-me*`（大小写不敏感）与 `<` 开头（`deploy/.env.example` 的 `<GENERATE_RANDOM_16+>` 形式）——模板后续再加变体也拦得住；
  - gateway key、bootstrap password、Meili/MinIO 基础设施密钥三处统一应用（基础设施密钥的 `_known_weak` 匹配改为大小写不敏感并加前缀模式）。
- **测试**：新增 `test_placeholder_variants_fail_fast`（4 种占位组合全部 SystemExit）。
- **验证**：`pytest tests/test_admin_gateway.py` 8 passed。

### 5. P0-1 JWT secret_key 无启动校验 ✅

- **文件**：`backend/app/core/config.py`、`backend/tests/conftest.py`、`backend/tests/test_admin_gateway.py`
- **改动**：`validate_admin_security` 新增 SECRET_KEY 校验（空值/已知占位串/`change-me*` 前缀/`<` 占位/长度 <32 → SystemExit）。**刻意放在 `admin_gateway_enforce` 放宽分支之前**：签名密钥泄露影响全站用户身份（可伪造任意 access token），不随管理网关联调开关豁免；仅 `DEBUG=true` 可跳过（本地开发）。
- **配套**：conftest 强制 `os.environ["SECRET_KEY"] = "test-only-secret-key-..."`（36 字符）——lifecycle 类测试真实跑 lifespan，非 debug 下沿用仓库默认占位密钥会整批 SystemExit；`test_strong_config_passes_validation` 补设强 secret_key；新增 `test_default_secret_key_fails_fast_even_without_gateway_enforce`（仓库默认值/空/过短/尖括号占位四种均 SystemExit）。
- **验证**：全量 16 个此前误伤的 lifecycle/shutdown 用例恢复通过；阶段一全量 390 passed。

### 6. P2-8 purpose 自由串注入限流键 ✅

- **文件**：`backend/app/modules/auth/schemas.py`、`backend/app/modules/auth/service.py`
- **改动**：`SendCodeRequest.purpose` / `VerifyCodeRequest.purpose` 由自由串收敛为 `Literal["login", "register", "bind_email", "bind_phone"]`（堵死 `purpose="limit:login"` 把验证码写进限流计数键、`"tries:*"` 作废他人待验证码的注入路径）；service 层 `send_code`/`verify_code` 以 `_CODE_PURPOSES` 兜底（服务层直调/测试同样受限；非法 purpose 在 `verify_code` 返回 False、在 `send_code` 抛 42200）。
- **验证**：阶段一全量 390 passed（既有测试全部使用合法 purpose，无需改动）。
- **收尾**：前端 `api.ts` 的 `sendCode` 类型联合中存在死值 `'email'`（后端从未支持），已与后端枚举对齐移除，防未来误用踩 422。

### 7. 阶段一：后端全量测试 ✅

- **结果**：`pytest tests -q` → **390 passed**（含本轮新增用例），0 failed，7m21s。

### 8. P0-2 WS 断线补发无参与者校验 ✅

- **文件**：`backend/app/modules/message/ws.py`、`backend/tests/test_websocket.py`
- **改动**：新增 `_is_participant(conversation_id, user_id)`（查 `Participant` 表）；`websocket_endpoint` 在执行任何补发（`last_seq` / `since` 两口径）前校验连接者是会话参与者，非参与者回 `{"event":"error","code":40300,"message":"无权读取该会话"}` 且**不断开连接**（实时收发能力不受影响）。REST 侧 `get_messages` 的既有校验不变。
- **测试**：新增 `test_ws_compensate_rejects_non_participant`——无关第三者带 `conv&last_seq=0` 连接收 40300 且收不到任何消息；同一请求由卖家（参与者）发起正常补发。
- **验证**：`pytest tests/test_websocket.py` 8 passed。

### 9. P1-1 物品审核可被发布者绕过 ✅

- **文件**：`backend/app/modules/item/router.py`（PATCH `/{item_id}`）、`backend/tests/test_item_review.py`
- **改动**：路由层新增闸门——物品处于 `PENDING` 且请求要变更 `status` 时，非 `Scope.ADMIN` 主体一律 403（"待审核物品的状态需由管理员审核后变更"）。状态机的 `PENDING → ON_SALE/OFF_SHELF` 出口保留给管理员审核路径（`admin.service.approve/reject_item` 走独立 CAS 直写，不经此路由）；发布者对标题/价格等编辑字段不受影响。
- **测试**：新增 `test_owner_cannot_self_approve_pending_item`——发布者 PATCH `status=0` 被拒且物品仍 PENDING、改标题成功、管理员 approve 正常。
- **验证**：`pytest tests/test_item_review.py tests/test_item.py` 8 passed。

### 10. P1-2 存储对象键信任链（3 处） ✅

- **文件**：`backend/app/core/storage.py`、`backend/app/modules/storage/router.py`、`backend/app/modules/item/schemas.py`、`backend/app/modules/item/service.py`、`backend/app/modules/share/schemas.py`、`backend/app/modules/share/service.py`、`frontend/services/api.ts`、测试 8 个文件
- **改动**（同一根因三处，统一信任链）：
  1. **服务端命名空间**：新增 `gen_user_object_key(user_id, filename)` → `uploads/{user_id}/{uuid}{ext}`；`presign` 不再采信客户端 `prefix`（参数保留兼容），签发的 key 恒在调用者命名空间内。
  2. **入库形态 + 归属校验**：`OBJECT_KEY_RE`（`^uploads/{36位UUID}/{32位hex}.{1-8位ext}$`）；`ItemImageIn.object_key` / `ShareCreate.file_key` schema 层把关形态，`create_item` / `create_share` service 层校验键内用户段 == 记录 owner（不属本人 → 42200），堵死"把他人 key 挂上自己的物品/资源"。
  3. **upload 端点绑定上传者**：`/api/files/upload` 先经 `ensure_user_object_key(key, user.id)`，他人命名空间的 key 一律 400——不可再覆盖他人对象。
  4. **presigned PUT → POST policy**：新增 `presigned_upload_post`（minio `PostPolicy`：`key` 精确等于签发键 + `content-length-range 1..10MB` + `content-type starts-with image/`，签名校验由 MinIO 服务端强制），响应增加 `fields`；前端 `uploadImage` 直传分支改为 POST form-data（policy 字段在前、file 最后）。
- **测试**：新增 `test_upload_rejects_foreign_namespace_key`、`test_presign_issues_user_namespace_key`；既有上传/穿越/发布类用例的 object_key 全部迁移为 `helpers.user_key()/key_from_token()` 生成的命名空间键（含 unit 层 schema 规则用例）。
- **验证**：相关 89 个后端测试通过；`npx tsc --noEmit` 通过。

### 11. P1-7 评价去重非并发安全 → 唯一约束 + 迁移 ✅

- **文件**：`backend/app/modules/course/models.py`、`backend/app/modules/canteen/models.py`、`backend/app/core/database.py`、`backend/app/modules/course/service.py`、`backend/app/modules/canteen/service.py`、`backend/tests/test_course_canteen.py`
- **改动**：
  - 两张评价表加命名唯一索引（模型层 `Index(..., unique=True)`，create_all 对新库生效）：`uq_course_review_user(course_id, user_id)`、`uq_canteen_review_user(dish_id, user_id)`；
  - `_SQLITE_INDEX_MIGRATIONS` 补两条 CREATE UNIQUE INDEX（老库幂等补齐，失败仅记日志不阻断启动——沿用 trade_sessions 既有策略）；
  - 两个 `add_review` 捕 `IntegrityError` → rollback → 409（并发双插兜底，范式与 auth/service 一致）。
- **测试**：新增 `test_course_review_duplicate_rejected`（端到端 40900）与 `test_course_review_unique_index_blocks_concurrent_insert`（绕过应用层直接双插 → IntegrityError，证明索引真实存在）。
- **验证**：`pytest tests/test_course_canteen.py` 6 passed。

### 12. P1-9 自动封禁可被单人操纵 ✅

- **文件**：`backend/app/modules/report/schemas.py`、`backend/app/modules/report/models.py`、`backend/app/modules/report/service.py`、`backend/app/core/database.py`、`backend/tests/test_p1.py`
- **改动**：
  - `submit_report`：`(reporter_id, target_type, target_id)` 命名唯一索引（模型层 + SQLite 迁移）兜底并发，重复举报 IntegrityError → 409"请勿重复提交相同举报"；
  - `check_auto_ban` 统计口径改为 **distinct 举报人 × 状态 PENDING/RESOLVED**——同一人重复提交只算一票；管理员驳回（REJECTED）不再永久计入，历史驳回不会让目标"永不超标"；
  - `target_type` 收敛为 `Literal["user","item","message","comment","share","course","stall"]`（与前端 types.ts 对齐），未知类型 422。
- **测试**：新增 4 例——重复举报 409、非法 target_type 拒绝、同一人灌 8 次不触发封禁、"2 驳回 + 4 有效不封禁 / 第 5 名有效举报人触发封禁"。
- **验证**：`pytest tests/test_p1.py tests/integration/test_admin` 20 passed。

### 13. P1-4 修改密码假成功 stub → 真实端点 ✅

- **文件**：`backend/app/modules/auth/schemas.py`、`backend/app/modules/auth/service.py`、`backend/app/modules/auth/router.py`、`frontend/services/api.ts`、`backend/tests/test_auth_login.py`
- **改动**：
  - 后端新增 `POST /api/auth/password`（`ChangePasswordRequest{old_password, new_password≥6}`，需登录）：`change_password` 服务函数先 `check_password` 验原密码（错误 → 42200"原密码不正确"，绝无静默成功），新旧相同拒绝，`set_password` 落库；
  - 前端 `api.users.changePassword` 从 `Promise.resolve({code:0})` stub 改为请求真实端点并透出错误（UserProfile 既有 `res.code !== 0 → error(res.message)` 分支自动生效）；
  - `/api/auth/password` 加入 `AUTH_REAL_PATHS`：后端不可达时返回网络错误而非 mock 假成功。
- **测试**：新增 4 例——改密成功后新密码可登录/旧密码失效、原密码错误被拒且密码未变、未登录 401、新旧相同拒绝。
- **验证**：`pytest tests/test_auth_login.py` 13 passed；`npx tsc --noEmit` 通过。

### 14. P1-5 生产构建保留 mock 回退 → DEV 门控 ✅

- **文件**：`frontend/services/api.ts`（`handleMockFallback`）、`frontend/tsconfig.json`
- **改动**：`handleMockFallback` 顶部以 `import.meta.env.DEV` 门控——生产构建（Vite 静态替换为 `false`）后端不可达时一律返回 `{code:-1, message:"网络连接失败，请稍后重试"}`，发物品/兼职/资源/评价/组队等写路径不再落回 localStorage 伪造"发布成功"；DEV 环境保留离线原型能力（含 AUTH_REAL_PATHS 的既有加固）。tsconfig `types` 补 `vite/client` 以识别 `ImportMeta.env`。
- **验证**：`npx tsc --noEmit` 通过；`npm run build` 成功，且生产 bundle 中确认包含门控错误分支字符串。

<!-- 每完成一项，在下方追加一个 "### <编号> <标题>" 小节 -->

### 15. P2-1/2 交易会话无生命周期 / 会话创建破坏原子性 ✅

- **文件**：`backend/app/modules/item/service.py`、`backend/app/modules/item/router.py`、`backend/app/modules/message/service.py`
- **改动**：
  - 新增生命周期端点（此前 `TradeSession.status` 创建后永不变更，RESERVED 物品被重新上架后部分唯一索引让新抢占全部 409，物品永久卡死）：`POST /api/items/trades/{id}/complete`（双方确认，会话→COMPLETED、物品 RESERVED→SOLD，两 CAS 同事务）、`POST /api/items/trades/{id}/cancel`（双方取消，会话→CANCELLED、物品释放回 ON_SALE，物品已非 RESERVED 时跳过释放不阻断取消）——cancel 即报告所说"无解困路径"的出口；
  - `create_conversation` 移除内部 `db.commit()`：调用方（`create_trade_session`）需要把会话创建与物品 CAS 放在同一事务，内部提交会在异常时残留 `conversation_id=NULL` 的 PENDING 会话。当前唯一调用方由自己提交，行为不变。
- **验证**：`pytest tests/test_item.py tests/test_message.py tests/test_e2e_flow.py` 通过；阶段三全量见第 40 行。

### 16. P2-3 兼职申请并发双插 ✅

- **文件**：`backend/app/modules/job/models.py`、`service.py`、`backend/app/core/database.py`
- **改动**：`uq_job_application(job_id, applicant_id)` 命名唯一索引（模型层 + SQLite 迁移），`apply_job` 捕 IntegrityError → 409"已申请过该岗位"。
- **验证**：阶段三全量通过。

### 17. P2-4 组队并发双插 + max_members 从未生效 ✅

- **文件**：`backend/app/modules/teammate/models.py`、`service.py`、`backend/app/core/database.py`
- **改动**：`uq_team_member(team_id, user_id)` 唯一索引兜底并发；`join_team` 执行 **max_members 上限**（此前全仓无任何引用，队伍人数无上限、FULL 状态永不出现）——满员拒绝并把队伍置 `TeamStatus.FULL`，入队后同步收敛状态。
- **验证**：阶段三全量通过。

### 18. P2-5 输入校验缺口 ✅

- **文件**：`backend/app/modules/{item,job,teammate,share}/schemas.py`
- **改动**：字符串字段补 `max_length`（对照列宽：title 128、description 2000、company/required_roles/contact_info 128/255/255、category 32-64、note/role 500/64）；`JobCreate.salary` 加 `ge=0, le=99_999_900`（此前接受负数）；`TeamCreate.max_members` 约束 1..100；`ItemUpdate.status` 加枚举校验——此前 `PATCH status=99` 在状态机 `ItemStatus(99)` 处抛未捕获 ValueError 变 500，现提前转 422。
- **验证**：阶段三全量通过。

### 19. P2-6 下载计数丢失更新 + owner 硬删除语义冲突 ✅

- **文件**：`backend/app/modules/share/service.py`、`backend/app/modules/item/service.py`
- **改动**：`increment_download` 改单条原子 UPDATE（`downloads = downloads + 1`），并发下载不再互相覆盖；owner 删除物品从硬删除（级联销毁进行中的交易会话）改为与管理员一致的**软删除**（`deleted_at`），历史交易凭据保留。
- **验证**：阶段三全量通过。

### 20. P2-7 CORS 中间件在网关内侧 ✅

- **文件**：`backend/app/main.py`、`backend/app/core/middleware.py`
- **改动**：Starlette 后添加者在**外侧**——调整为网关（最内）→ `SecurityHeadersMiddleware`（新加，见 P3-1）→ CORS（最外），预检 OPTIONS 与网关 401/429 响应现在都携带 CORS 头与安全头。
- **验证**：阶段三全量通过（既有网关测试未受顺序影响）。

### 21. P2-9 WS 通道四项加固 ✅

- **文件**：`backend/app/modules/message/ws.py`
- **改动**：
  1. `_authenticate` 查 `User.status`——封禁账号此前保留完整 WS 收发能力（REST 才拦截）；
  2. 每用户发送节流：进程内滑动窗口 30 条/分钟（断开时清理窗口），超限回 42900；
  3. `content` 限长 1..2000（此前无上限）；
  4. `message:read` 已读回执前校验参与者（此前可对任意会话伪造已读）。
- **验证**：既有 WS 测试 8 项全过（节流阈值不影响正常用例）。

### 22. P2-10 WS Redis 监听死亡永不重启 ✅

- **文件**：`backend/app/modules/message/ws.py`
- **改动**：`_redis_listen` 改为自愈循环——运行中异常按指数退避（1s→30s）重启订阅，多实例部署的跨实例投递不再静默失效；仅 `stop_listener` 的主动取消退出；无 Redis（降级内存）语义不变。

### 23. P2-11 AI 端点无每用户配额 ✅

- **文件**：`backend/app/modules/ai/router.py`
- **改动**：4 个生成类端点统一挂 `enforce_ai_quota` 依赖——按自然日 Redis 计数（`ai:quota:{user}:{yyyymmdd}`），超限 429"今日 AI 使用次数已达上限"；限额 `ai.daily_limit_per_user` 可配置（缺省 20）；Redis 不可用 fail-open（与全局限流一致）。

### 24. P2-12 本地模式匿名图片 401 ✅

- **文件**：`backend/app/core/middleware.py`
- **改动**：`/api/files/raw` 加入网关公开清单——设计模型是"key 内含 128 位 uuid 即能力凭证"（同签名 URL），`<img src>` 也无法携带 Header；缺席白名单使本地降级模式图片全挂。

### 25. P2-13 OAuth bind state 可选 ✅

- **文件**：`backend/app/modules/auth/router.py`、`frontend/services/api.ts`、`frontend/pages/UserProfile.tsx`
- **改动**：后端 `bind/oauth` 强制要求 state（缺失或校验失败一律 403，不再"不传即跳过"）；前端绑定前先调 `GET /api/auth/{provider}/state` 领取一次性 state 再提交（新增 `api.auth.oauthState`）。

### 26. P2-14 验证码票据 get-then-delete TOCTOU ✅

- **文件**：`backend/app/core/redis.py`、`backend/app/modules/auth/captcha.py`
- **改动**：新增 `redis_getdel`（原生 GETDEL，旧版 Redis/内存兜底退化为 get+delete）；`consume_ticket` 改原子"读取即作废"，并发双请求不再都能读到票据。

### 27. P2-15 非 ASCII 网关头致 500 ✅

- **文件**：`backend/app/modules/admin/gateway.py`
- **改动**：令牌比较统一编码为 bytes（恒定时间语义不变），含代理字符无法编码时直接判 False——未认证请求回到 404 影子而非 500。

### 28. P2-17 canteen/course 列表把全库评价载入内存 ✅

- **文件**：`backend/app/modules/{canteen,course}/models.py`
- **改动**：`Dish.reviews` / `Course.reviews` 从模型级 `lazy="selectin"` 改回默认惰性——两处响应都不序列化评价，eager 装载等于每次列表把全库评价拉进内存；删除时的级联清理由 flush 内按需惰性加载 + DB 级 ON DELETE CASCADE 完成（首版用查询级 `noload()` 覆盖，发现 SQLAlchemy 2.1 已弃用该选项后改为模型级收敛）。

### 29. P2-18 teammate 列表 N+1 COUNT ✅

- **文件**：`backend/app/modules/teammate/service.py`
- **改动**：一条 `GROUP BY team_id` 取回本页全部队伍成员计数，替代每行一次 COUNT（页大小 ≤100 → 最多 100 次往返）。

### 30. P2-19 会话列表无分页 ✅

- **文件**：`backend/app/modules/message/service.py`、`router.py`
- **改动**：`GET /api/messages/conversations` 加 `page/page_size`（默认 50 与前端单次拉取量对齐）；分页后窗口函数与批量查询的扫描范围收敛到当前页会话。响应形状不变（list），前端零改动。

### 31. P2-21 WS 重连永远用旧 token ✅

- **文件**：`frontend/services/websocket.ts`
- **改动**：每次 `openSocket()` 重读 localStorage 最新 access token——此前重连固定用 `connect()` 捕获的旧 token，REST 静默刷新后 WS 进入永久"正在重连…"循环；本地无令牌（登出）时停止重连。

### 32. P2-22 server.ts 挂起 / handleReport 丢字段 / 硬编码 mock ✅

- **文件**：`frontend/server.ts`、`frontend/services/api.ts`、`frontend/pages/{UserProfile,MarketDetail,CourseDetail}.tsx`、后端配套端点
- **改动**：
  1. `server.ts` 代理 `on.error` 补 502 JSON 响应——此前只 console.error 且覆盖了默认响应器，后端挂掉时浏览器请求无限悬挂；
  2. `api.admin.handleReport`：此前把 UI 的 `ReportAction` 枚举（user_ban/warning…）原样透传给只认 resolve/reject/ban 的后端且丢弃 status——所有分支都不命中，**工单状态经 UI 永不变更**。现按 UI 意图映射（Rejected→reject；Resolved→ban(选了封禁)/resolve）；
  3. 六个假成功 mock 接真实端点：`users.getItems`（物品列表加 `owner_id` 过滤参数）、`users.getFavorites`、`courses.likeReview`、`shares.like`、`teammates.apply`、`teammates.close`；
  4. 为此新增后端能力：`UserFavorite` 收藏表（唯一索引 + GET/POST/DELETE `/api/users/me/favorites`，收藏幂等、禁收藏自己的物品）；`CourseReview.helpful_count` 列 + `POST /api/courses/reviews/{id}/like`（原子计数）；`ShareResource.likes` 列 + `POST /api/shares/{id}/like`（原子计数）；`POST /api/teams/{id}/close`（仅队长，→DISBANDED）；对应 SQLite 列/索引迁移；MarketDetail 收藏按钮从纯 toast 接到真实 API；CourseDetail 点赞以服务端计数为准。
- **验证**：`npx tsc --noEmit` 通过；`npm run build` 成功。

### 33. P2-23 devctl 用占位 env 启动 compose ✅

- **文件**：`scripts/devctl.py`
- **改动**：`_compose_base` 优先使用 `deploy/.env` 真值；不存在时从模板生成（密钥类 `<...>` 占位替换为随机强值，DB_USER/DB_NAME/YOUR_DOMAIN 给可读默认，SMTP_* 留空）并一次性写入 `deploy/.env`——MinIO 容器不再拿占位 root 凭据、Postgres 不再落弱默认密码。

### 34. P2-24 bootstrap 密码可空值"无病"上线 ✅

- **文件**：`backend/app/core/config.py`、`backend/app/modules/admin/service.py`、`backend/tests/conftest.py`
- **改动**：`validate_admin_security` 在生产判定块（独立于网关开关）新增：`admin_bootstrap_enabled` 且未配置密码 → SystemExit；`ensure_seed` 的 `admin123` 弱口令回退收敛到**仅 debug 生效**，非 debug 未配置则 CRITICAL 告警并跳过创建管理员（纵深防御：即使网关联调被放宽也不会凭空造出弱口令管理员）；conftest 为测试进程统一注入强 bootstrap 密码（全部测试经由 `settings.admin_bootstrap_password or "admin123"` 表达式，行为自动一致）。

### 35. P2-25/26 nginx 死配置 / CI 构建废弃镜像 ✅

- **文件**：`deploy/nginx/nginx.conf`、`.github/workflows/ci.yml`
- **改动**：删除 `/metrics` 的 `allow 10.0.0.0/8` 死配置（Docker 端口映射下永不匹配、prometheus 直连 app:8000 不经网关——纯"已设防"错觉，留注释说明收敛入口）；CI worker 镜像改用真实部署路径 `docker build --target worker -f backend/Dockerfile`（`deploy/Dockerfile.worker` 已声明废弃）。

### 36. P3 简表（13 修 / 5 跳）✅

**已修**：
- 安全响应头：新增 `SecurityHeadersMiddleware`（nosniff / X-Frame-Options: DENY / CSP `default-src 'none'; frame-ancestors 'none'` / Referrer-Policy），全应用生效；
- admin 登录与 discover 纳入严格限流（10/min/IP，与认证端点同级）；
- 审计 IP 取 XFF **最后一段**（`$proxy_add_x_forwarded_for` 追加语义，第一段可被客户端伪造）；
- 邮箱白名单非法正则从**静默放行**改 fail-closed（注册规则配置异常时明确报错），后台保存规则时校验正则可编译（ReDoS 源在入口拦截）；
- `create_course` 并发重复 code 由唯一约束兜底转 409；department 收敛到后台配置院系列表（脏值落空串）；
- ILIKE 通配符转义：新增 `common.utils.escape_like`，item/job/course/user 四处搜索全部套用（`%`/`_` 不再退化匹配）；
- `/api/items/search` limit 补 `ge=1`；
- 管理端审计写入补全：封禁/解封/提权/物品审核通过/拒绝/物品删除/审核开关变更七类关键动作写 `audit_logs`（此前 `ADMIN_*` 动作定义了零调用）；
- AI 课程画像提示注入缓解：UGC 评价用 `<review>` 定界符包裹 + system instruction 明示不可信；
- CourseDetail：切课程先清空上一门课的 AI 画像（防串课文案），AI 摘要补 `.catch`（未处理拒绝）；
- 非生产环境对 minioadmin/masterKey 默认基础设施密钥启动告警；
- nginx 补 `X-Content-Type-Options` 等安全头（与应用层双保险）；
- prometheus 注释掉默认拓扑下常驻 DOWN 的 `nginx:80` 抓取目标（消除"狼来了"告警）；`start_dev.bat` 横幅账号改为 siteadmin；`verify_render.py` 移除个人绝对路径（默认落仓库 `.run/screenshots`，可用 OUT_DIR 覆盖）。

**跳过（附原因）**：
- `/ws?token=` 查询串：需要客户端协议升级（首消息鉴权 / subprotocol），token 仅 15 分钟有效，风险可接受，留作协议演进项；
- `tasks/notify.py` 死通道：当前无任何调用方，接入时再按订阅模型设计；
- 验证码随 Celery 任务参数入 broker 队列 / `send_email` 非幂等：内部信任面，改动涉及任务可靠性语义（acks_late），单独排期；
- P2-16 token 全在 localStorage：无已知 XSS sink，迁移 sessionStorage/cookie 影响多标签页会话语义，需产品决策；
- P2-20 仪表盘无界 COUNT：管理端、量级尚可（报告原注）；
- P3-15 models/alembic/SQLite 三处同步漂移：本批已为全部新索引/列补齐三处清单，漂移面收敛，结构性重构（单一生成源）另行规划。

### 37. 阶段三：后端全量测试 ✅

- **结果**：`pytest tests -q` → **404 passed**，0 failed，6m51s。期间唯一一次失败（`test_bind_oauth`）为 P2-13 state 必传的预期行为变化，已将用例更新为新流程（领取一次性 state → 绑定；缺 state 断言 40300）后全绿。
- **配套验证**：`npx tsc --noEmit` 通过；`npm run build` 成功。

至此，[review-2026-09-28.md](./review-2026-09-28.md) 的 P0 全部 3 项、P1 全部 9 项、P2 全部 24 项（22 修 + 2 跳）与 P3 全部 18 项（13 修 + 5 跳）处理完毕；跳过项均已在上方明细中记录原因。改动留在 `feat/frontend-redesign` 工作区未提交。
