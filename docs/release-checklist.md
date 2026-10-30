# CampusSphere 上线就绪清单（2026-10-01）

> 本文档是上线评审依据：汇总本轮"上线就绪冲刺"完成的修复、上线前必须人工完成的事项、
> 以及明确**接受并带着上线**的风险。配合 `docs/部署手册.md` 与 `docs/DEPLOYMENT.md` 使用。

## 一、本轮完成的修复与验证（feat/frontend-redesign 分支）

### 功能闭环
| 项 | 说明 |
| --- | --- |
| Meilisearch 写侧接线 | 此前只有读侧（搜索接口），索引恒空、搜索 100% LIKE 降级。现物品发布/更新/删除/审核（前台 + 管理端共 8 处调用点）与用户资料更新均异步同步索引（Celery 任务 `search_sync.*`），broker 不可达时静默降级 |
| 索引可见性闸门 | 搜索接口命中 Meili 时直接返回文档，不再过滤状态；因此只索引公开可见记录（排除待审核/已删除），防止未审核内容经搜索泄露 |
| 全量重建索引脚本 | `backend/scripts/reindex_search.py`，首次部署后灌存量数据 / 索引损坏后修复，幂等 |
| 演示数据脚本恢复 | `seed_demo_users.py` 曾被误删导致 README 指向空文件，已从历史恢复并验证幂等可用 |

### 安全
| 项 | 说明 |
| --- | --- |
| Refresh token 重用检测（RFC 6819） | 此前已轮换的 refresh token 被重放只报"已失效"。现轮换改 CAS 条件 UPDATE（并发下同 token 仅一方成功，消除刷新令牌克隆竞态）；已吊销 token 再次出现 → 吊销该用户**全部** refresh token 强制重登录，安全事件记 `refresh_token_reuse_detected` |
| WebSocket 首帧鉴权 | 此前 access token 走 `/ws?token=` 查询串，落入反代访问日志。现连接后首帧 `{"event":"auth","token":...}`（10s 超时），URL 仅保留非敏感游标参数；前端 `websocket.ts` 同步改造，40100 时停止自动重连。前后端同仓同版发布，无兼容窗口 |

### 可部署性（上线阻断级）
| 项 | 说明 |
| --- | --- |
| Alembic 0002 幂等化 ⚠️ | 0001 是"当前模型快照式"建表（`Base.metadata.create_all`），全新 PG 上 0002 的 `add_column` 全部撞"duplicate column"→ **生产 compose 启动命令 `alembic upgrade head` 直接崩、app 容器永远起不来**。已在空 PG 16 实测复现并修复（先探测列/索引存在性再执行），后续迁移必须遵守同约定（见 0002 文件头） |
| alembic check 零漂移 | 迁移产物与模型一致（`alembic check` 通过） |
| CI / compose Node 版本对齐 | CI 3 处 `node-version` 20 → 22，与 compose 构建器 `node:22-slim` 一致，消除 EBADENGINE 隐患 |
| 工程一致性 | 移除 `@google/genai` 死依赖与 bun/yarn 锁文件（统一 npm）；`.gitignore` 补 AI 工具目录 |
| Lint 清零 | ruff 存量 19 个错误清零（含 `require_scope` DI 白名单、异常链、`zip(strict=True)` 等），`ruff check app` 全绿——此前 CI 必红 |
| 跨平台 | `alembic.ini` 去 UTF-8 字符（configparser 按locale 编码读取，中文 Windows GBK 环境会 UnicodeDecodeError） |
| 文档 | `scripts/doc_sync.py` 修 `dict[str, Any]` 误报；`PROJECT_STATUS`/`DOC_DRIFT_REPORT`/`openapi.json` 全部重新生成（128 接口数与 README 一致）；`doc_sync --check` 通过 |

### 验证结果（本机实测）
- 后端 pytest **410 passed**（新增搜索接线 5 + refresh 重用检测 1；WS 13 用例按新协议重写后全绿）
- 前端 `tsc --noEmit` ✓ / vitest 14 ✓ / `npm run build` ✓
- Docker 双 target 镜像构建成功（app + worker）
- `docker compose up -d` 全栈 6 容器 **healthy**（app 内 `alembic upgrade head` 一次通过）
- 冒烟：登录 → 资料 → 发布物品 → **Meilisearch 搜索命中（Celery→Meili 全链路，worker 日志确认任务执行）** → 发起交易，全通
- WS 新协议容器内实测：首帧 auth → `auth:ok` → ping/pong 正常
- E2E：见下方第四节

## 二、上线前必须人工完成（无法在代码层替你做）

1. **服务器上重新生成 `deploy/.env`**：本地/仓库中的任何 .env 都不可复用。`SECRET_KEY`、
   `MINIO_ACCESS_KEY/SECRET_KEY`、`MEILI_API_KEY`、管理员引导密码等用 `scripts/devctl.py` 生成强随机值。
2. **SMTP 真实凭据**：注册链路依赖邮箱验证码；`EXPOSE_VERIFICATION_CODE` 生产必须 false（已默认）。
3. **TLS 证书**：拓扑 A 放 `deploy/nginx/ssl/`；拓扑 B 在宝塔签发。无证书时可用 `nginx.http-only.conf` 联调，**不可上线**。
4. **OAuth 微信/QQ 凭据**：`config/school.yaml` 仍为 placeholder，对应登录入口不可用（前端有"暂未开放"提示）。
   上线前要么配置真实凭据，要么接受该入口停用。
5. **首次部署后重建索引**：`docker compose exec app python scripts/reindex_search.py`
   （增量同步只覆盖部署后的变化）。
6. **容量观测**：compose 内存上限是推算值，上线后用 `docker stats` 观察 2C2G 实际占用再调
   `*_MEM_LIMIT`；长期贴顶说明该扩容而非加限制。
7. **监控拍板**：prometheus/grafana 不在 compose 默认组，是否随生产启用需明确决定（启用见 `deploy/prometheus/`）。

## 三、明确接受的风险（带病上线项，均已评估）

| 风险 | 评估与缓解 |
| --- | --- |
| Token 存 localStorage（P2-16 遗留） | XSS 得手可窃取。缓解：access 仅 15 分钟 + refresh 轮换 + **本轮新增重用检测（盗用即全家吊销）** + 封禁即时生效。迁移到 HttpOnly Cookie 需 CSRF 防体系与产品决策，单独排期 |
| 验证码经任务参数入 Celery broker | broker 为内网 Redis（生产 compose 未暴露端口），泄露面 = 服务器被入侵，届时验证码非最敏感资产。可接受 |
| `/api/items/search` 返回 Meili 原始文档 | 文档形状与 ItemOut 对齐（有测试守护）；用户文档 email/phone 先脱敏再入索引 |
| notify / summary Celery 任务已注册无生产者 | 死基础设施但不影响运行（worker 消费空队列），已在代码注释与本清单声明，防止运维误以为通知/摘要已生效 |
| OAuth 登录不可用 | 见第二节第 4 条，属产品决策项 |
| CI 无自动部署 | 发布为手动 compose 流程（见部署手册），单校规模可接受 |

## 四、发布流程建议

1. 本分支 `feat/frontend-redesign` 领先 dev 35+ 提交（含全部 P0~P3 修复与本轮冲刺），
   dev 上的落后提交仅为历史快照，**建议直接合入 dev → main**（fast-forward 或 PR 均可），
   合并后 CI 全绿作为最终门禁。
2. 打 tag（如 `v1.0.0`），生产机按 `docs/部署手册.md` 拉取部署。
3. 首次启动后：管理员登录 → 后台改默认密码 → 配置分类/邮箱规则 → 跑 reindex → 观测 `docker stats`。
4. 回滚预案：`docker compose down` + 回退 tag 重新 up；数据卷（pgdata）不动即无数据损失，
   迁移仅前向新增（0002 可安全重放）。
