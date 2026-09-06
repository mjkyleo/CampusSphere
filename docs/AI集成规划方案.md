# CampusSphere AI 集成规划方案

> 生成时间：2026-09-06
> 结论基于**源码取证 + 运行时实测**（后端已启动，`/api/ai/status` 与 OpenAPI 实际抓包验证）

---

## 〇、一句话结论

**AI 能力已真实落地、工程质量不错，但深度有限且默认关闭。**
简历中「httpx 异步直调 / app_config 动态开关 / `/api/ai/status` 实时状态 / 输入护栏」**四项全部属实，可保留**；
但「**降级**」这一层**代码中不存在**（失败即抛错，无兜底、无模型链），且多份文档存在过期漂移——
**建议先按本文 P0–P2 落地，再写进简历；在此之前移除「自动降级兜底文案」类描述。**

---

## 一、代码审查：AI 实现全景

### 1.1 资产清单（实测）

| 层 | 文件 | 行数 | 状态 |
|---|---|---|---|
| 后端业务 | `backend/app/modules/ai/service.py` | 285 | ✅ 完整 |
| 后端路由 | `backend/app/modules/ai/router.py` | 83 | ✅ 5 端点 |
| 后端模型 | `backend/app/modules/ai/schemas.py` | 57 | ✅ |
| 配置 | `config/school.yaml` `ai:` 段 | L234-242 | ✅ |
| 管理端 | `admin/router.py` `/api/admin/ai/config` GET+PUT | L349-372 | ✅ |
| 前端客户端 | `frontend/services/geminiService.ts` | 93 | ✅ 纯代理 |
| 前端客户端 | `frontend/services/api.ts` `ai:` 段 | L1609-1623 | ✅ 重复一套 |
| 消费页面 | HomePage / MarketPublish / CourseDetail / AdminDashboard | — | ⚠️ 见 1.3 |
| 测试 | `tests/integration/test_external/test_ai_service.py` | 171 | ✅ 有 |

### 1.2 实测端点（OpenAPI 抓取 + 运行时调用）

```
GET  /api/ai/status          公开（middleware.py:43 PUBLIC_PATHS）
POST /api/ai/insights        登录
POST /api/ai/item-description  登录
POST /api/ai/course-summary  登录
POST /api/ai/categorize      登录   ← 零调用方，死代码
GET  /api/admin/ai/config    管理员
PUT  /api/admin/ai/config    管理员
```

运行时实测：
```
GET /api/ai/status
→ {"code":0,"data":{"enabled":false,"available":false,"message":"AI 智能助手功能未开放"}}

POST /api/ai/insights（无 token）→ 401 {"code":40100,"message":"缺少访问令牌"}
GET  /api/admin/ai/config（无 token）→ 401
```

### 1.3 简历声称的能力逐项核对

| # | 声称 | 实测证据 | 判定 |
|---|---|---|---|
| 1 | 前端直调 AI | `geminiService.ts` 全部为 `fetch('/api/ai/*')`；`server.ts`(102行) 是 `http-proxy-middleware` 纯转发，**无任何 AI 逻辑、无 Key、无 SDK** | ✅ **不存在直调，可放心** |
| 2 | httpx 异步直调 Gemini | `service.py:170` `httpx.AsyncClient(timeout=30).post(generateContent)`，未引入 `google-generativeai` | ✅ **属实** |
| 3 | app_config 开关 | `_AI_FEATURE_KEY="ai.feature"` 写 `AppConfig` 表，DB 优先于 yaml（`:62-91`）；管理端可热改 | ✅ **属实** |
| 4 | `/api/ai/status` 实时状态 | 公开端点，实测返回 `enabled/available/message` | ✅ **属实** |
| 5 | 输入护栏 | `_MAX_CONTENT_LEN=3000`/`_MAX_REVIEW_TEXT_LEN=500`/`_MAX_INSIGHT_TOPIC_LEN=200`（`:43-45`），schema `max_length` 二次校验 | ✅ **属实** |
| 6 | **降级** | ❌ **不存在**。失败路径统一 `raise BizError`；测试注释明写「**绝不能返回假数据**」。无模型降级链、无内置兜底文案、无 `fallback:true` 字段（全仓 grep 无命中） | ⚠️ **不属实** |

### 1.4 文档漂移（重要，引用前必查）

以下描述**与代码不符**，属历史遗留（AI 曾放在前端层，后已迁后端）：

| 文档 | 声称 | 真相 |
|---|---|---|
| `docs/usage.md:180` | 「模型按 `gemini-2.5-flash → gemini-3.1-flash-lite → gemini-flash-latest` 自动降级」 | ❌ 单 `model` 字段，无链 |
| `docs/usage.md:180` | 「未配置 Key 自动返回内置兜底文案（响应带 `fallback: true`）」 | ❌ 抛错，且刻意不返假数据 |
| `docs/development.md:200-204` | 「`frontend/server.ts` 中的 `/api/ai/*` 调用 Gemini」 | ❌ server.ts 是纯代理 |
| `docs/全链路深度拆解与技术亮点.md:239` | 把「开关关闭」表述为「降级」 | ⚠️ 语义被泛化，实际是**开关**不是**降级** |

### 1.5 其他真实现状缺口

1. **入口隐藏不彻底** —— `MarketPublish.tsx:326` AI 润色按钮**无条件渲染**；`CourseDetail.tsx:147` AI 画像框**无条件渲染**。仅 `HomePage.tsx:137` 做了 `aiAvailable` 判断。
   → 违反「未配置 AI 时前端自动隐藏入口」，无 Key 时用户点按钮只会报错。
2. **默认关闭** —— `enabled: false`，线上/演示态**跑不到任何 AI 能力**，面试现场演示不了。
3. **双客户端并行** —— `api.ai.*` 与 `geminiService.*` 两套，状态缓存不共享（`AdminDashboard` 走后者，`HomePage` 走前者）。
4. **无 RAG** —— 无向量检索、无 embeddings；Meilisearch 索引恒空（既有结论）。
5. **无 AI 专属治理** —— 无超时分层、无重试/熔断、无用量日志、无 AI 级频控（仅走通用限流）。

---

## 二、简历建议（明确结论）

### ✅ 保留（有源码支撑，可展开讲）
- httpx 异步直调模型 REST 而非引入 SDK（降依赖树）
- `app_config` 动态开关：DB 覆盖 yaml，管理端热改、前端条件渲染
- 公开状态端点驱动前端**能力级**渲染，避免"假数据"误导
- 输入护栏（长度截断 + schema 上限 + 50 条评价上限）
- JSON mode + markdown 围栏容错解析（`_parse_categorize_result`）

### ❌ 移除 / 修正（会被追问击穿）
- 「模型自动降级链 `gemini-2.5-flash → ...`」→ **不存在**
- 「未配置 Key 自动返回内置兜底文案、`fallback: true`」→ **不存在**，且设计上刻意不返假数据
- 「前端/server.ts 层 AI 服务」→ **已下线**，现在是纯代理
- 「直调 + 护栏 + 降级 三层接入」→ **降级层缺失**；建议 P0–P2 落地后再写，或改为「直调 + 护栏 + 开关」

> 补充：AI 功能当前**默认关闭 + 默认无 Key**，即"演示态 0 次真实调用"。
> 若要靠 AI 讲 Agent 岗故事，**至少完成 P0/P1/P2 并保证有 1 条真实调用链路可演示**。

---

## 三、目标架构：OpenAI 标准接入

### 3.1 统一 Provider（替换 Gemini 私有协议）

现状 `_call_gemini` 硬编码 `generativelanguage.googleapis.com` + `generateContent` 协议。
改造为 **OpenAI Chat Completions 标准**，`httpx` 直调 `POST {base_url}/chat/completions`：

```python
# app/modules/ai/provider.py（新增）
class OpenAICompatibleClient:
    def __init__(self, base_url, api_key, timeout_ms=8000): ...
    async def chat(self, *, model, messages, temperature=0.7,
                   max_tokens=512, json_mode=False) -> str: ...
```

**一套代码兼容**：OpenAI、DeepSeek、通义 Qwen、Kimi、智谱 GLM、Groq、本地 Ollama / vLLM / LM Studio。
（Gemini 亦提供 OpenAI 兼容端点，无需单独适配。）

### 3.2 配置扩展（`config/school.yaml` + 环境变量覆盖）

```yaml
ai:
  enabled: false                    # 总开关，默认关
  provider: openai_compatible
  base_url: "https://api.deepseek.com/v1"
  api_key: ""                       # 强烈建议用环境变量 AI_API_KEY 注入
  model: "deepseek-chat"
  fallback_models: ["qwen-turbo", "glm-4-flash"]   # 模型级降级链
  timeout_ms: 8000
  max_retries: 1
  circuit_breaker: { threshold: 5, cooldown_sec: 60 }
  capabilities:                     # 能力级开关 + 可降级标记
    greeting:          { enabled: true, degradable: true  }
    item_description:  { enabled: true, degradable: true  }
    course_summary:    { enabled: true, degradable: true  }
    moderation:        { enabled: true, degradable: false }  # 不可降级→转规则引擎
```

### 3.3 真正的三层（补齐「降级」）

```
L0 开关层  未开启 / 无 Key → status.available=false → 前端隐藏入口，主流程零阻塞
L1 能力层  调用失败/超时 →
            degradable=true  → 模板库兜底，返回 source:"fallback"（UI 正常，不报错）
            degradable=false → 转规则引擎（敏感词表），不阻塞发布
L2 模型层  主模型 429/5xx/超时 → 依次 fallback_models → 全失败再进 L1
附加        超时 8s + 重试 1 次（退避）+ 熔断器（连续 5 次失败熔断 60s，期间直接降级）
```

**关键原则**：任何 AI 失败都**不得阻塞主流程**，且**不得静默返回假数据**（保留现有设计哲学，但用显式 `source` 字段标明来源）。

### 3.4 状态端点增强（能力级粒度，替代全局布尔）

```jsonc
GET /api/ai/status   // 仍为公开端点
{
  "code": 0,
  "data": {
    "enabled": true,
    "available": true,
    "provider": "openai-compatible",
    "model": "deepseek-chat",
    "capabilities": {
      "greeting":         { "available": true,  "degraded": false },
      "item_description": { "available": true,  "degraded": false },
      "course_summary":   { "available": false, "degraded": false },
      "moderation":       { "available": true,  "degraded": true  }
    },
    "message": "AI 助手运行中"
  }
}
```

前端统一 hook `useAiCapability(name)`，按**能力**而非全局布尔渲染入口。

---

## 四、首页问候功能设计（重点）

### 4.1 产品定义：「每日问候 · 微采集」

对标：Notion AI 每日摘要 / Duolingo 每日激励 / 微信读书每日一句。
核心：**用一次极轻量的"信息采集"换取一条真正个性化、且每次都不同的问候语**，而不是千篇一律的「你好，XXX」。

### 4.2 交互流程

```
启动/进首页
  │
  ├─ GET /api/ai/status → capabilities.greeting
  │
  ├─ 不可用 ──→ 本地模板问候（前端内置 60 条，按 时段 × 星期 × 日期种子 伪随机）
  │              零网络、零阻塞、每次也不同
  │
  └─ 可用 ──→ 展示「微采集卡」（1 题，从问题池随机，避免连日重复）
                「今天状态是？」 元气满满 / 稳中求进 / 有点疲惫 / 冲刺备战
                「今天最想搞定？」 课业 / 竞赛 / 社交 / 摸鱼
                        │ 用户点选（1 次/天，可改）
                        ▼
                POST /api/ai/greeting { mood, focus, clientSeed, tz }
                        ▼
                后端组装上下文 + 多样性种子 → LLM → 卡片渲染
                        ▼
                「换一句」按钮（regenerate:true，换表达手法）
```

### 4.3 上下文采集（服务端组装，防前端伪造）

| 类别 | 字段 | 来源 |
|---|---|---|
| 时间 | 时段（清晨/上午/午后/夜晚）、星期、是否考试周、学期阶段 | 服务端计算 |
| 用户 | 今日课程数、待办数、最近浏览/发布行为 | DB |
| 采集 | `mood`、`focus` | 用户点选（枚举白名单） |
| 多样性 | `variation_hint` | `hash(user_id + date + clientSeed)` 映射 |

`variation_hint` 是**保证"每次不同"的关键**：从手法池映射，如
`用一个校园比喻` / `用一个反问句` / `带一个冷知识` / `模仿弹幕语气` / `用一句歌词感` / `做一个极小挑战`。

### 4.4 Prompt 与输出

```
系统：你是校园助手，为大学生生成今日问候。
用户：
  时间：周四 夜晚，考试周前 2 周
  状态：有点疲惫
  今日重点：课业
  表达手法（必须体现）：用一个校园比喻
  约束：40-60 字，中文，口语化，不说教，不空洞鸡汤
  输出 JSON：{"text":"...","emoji":"单个 emoji"}
```

生成参数：`temperature=1.0`（求新）、`max_tokens=128`、`json_mode=true`、小模型（flash/lite 级）控成本。

### 4.5 缓存与"每次不同"的平衡

- 缓存键 `greeting:{user_id}:{date}:{mood}:{focus}`，TTL 至次日 0 点
- **同一天同一状态复用缓存** —— 刷新页面不变，避免"刷新就变"显得廉价
- **每次启动生成不同** 通过两个途径达成：
  1. 当日**新的微采集**（改了 mood/focus）→ 新键 → 新生成
  2. 「换一句」→ `regenerate:true` → 换 `variation_hint` → 新生成（限 5 次/天）
- 频控：10 次/天/用户

### 4.6 降级（无 Key / 调用失败）

后端返回**服务端模板库**组合结果，仍带 `source` 字段：

```jsonc
{ "text": "周四夜里还在啃书？先喝口水，你已经很能扛了。",
  "emoji": "🌙", "source": "fallback" }
```

前端**正常渲染卡片，不报错、不弹红框**，`source==="fallback"` 时隐藏「AI」角标即可。

### 4.7 护栏

- `mood`/`focus` 走**枚举白名单**，自由文本 ≤ 20 字（防 prompt 注入）
- 输出长度硬截断 60 字 + 敏感词过滤
- JSON 解析失败 → 直接降级模板（不重试第二次，控延迟）

---

## 五、各模块 AI / RAG 切入点（对标同类产品）

| 模块 | 对标产品 | 切入点 | 价值 | 优先级 |
|---|---|---|---|---|
| **首页** | Notion AI / Duolingo | **每日问候微采集**（本文四章）<br>今日速览：聚合今日课程+待办+热帖 → 3 条建议 | 留存、打开率 | **P2** |
| **闲置市场** | 闲鱼 AI 发布 / 转转估价 | 描述润色（**已有，补降级**）<br>**定价建议**：RAG 检索同类成交价 → 价格区间<br>**图片识别**：多模态自动填标题/类目/成色<br>**自然语言搜物**：「500 以内自行车」→ 结构化筛选 | 发布转化率 | P3 |
| **课程评价** | 大众点评 AI 摘要 / Amazon 评论摘要 | 评价画像（**已有，补降级**）<br>**RAG 选课问答**：「点名严吗？作业多吗？」带**引用溯源**<br>两课对比推荐 | 决策效率 | **P3** |
| **组队搭子** | Boss 直聘匹配 / Soul | 帖子+用户画像向量化 → **语义匹配推荐**（替代关键词）<br>组队邀请话术生成 | 匹配成功率 | P4 |
| **实习就业** | Boss 直聘 AI 诊断 | JD ↔ 技能匹配度打分<br>岗位推荐理由生成、简历要点润色 | 投递转化 | P4 |
| **食堂** | 大众点评帮你选 | 「今天这个窗口吃什么」评价汇总<br>饮食偏好 → 菜品推荐 | 日活 | P5 |
| **社区发帖** | 知乎瓦力 / 小红书审核 | **内容安全预审 + 自动分类**（`/api/ai/categorize` **已实现但零调用方，直接接线**）<br>话题标签自动生成、标题优化建议 | 审核成本 | **P1** |
| **消息** | Gmail Smart Reply | 快捷回复建议（好的 / 稍后联系 / 已出） | 沟通效率 | P5 |
| **管理后台** | 内容平台审核台 | 举报内容 AI 预判定 → 优先队列、违规聚类 | 审核效率 | P5 |

### RAG 技术选型建议

- **向量库选 pgvector**（生产已是 PostgreSQL 16），**不要指望 Meilisearch** —— 既有结论：Meili 索引恒空、`search_sync` 零触发点，真实检索 100% 走 SQL LIKE 降级。
- 语料：课程评价、商品描述、帖子正文、公告、食堂评价
- 新增表：`EmbeddingChunk(id, source_type, source_id, chunk_text, embedding vector(N), created_at)`
- 检索：pgvector 余弦相似度 Top-K → 拼上下文 → LLM 生成，**答案带 `[1][2]` 引用**，可溯源（这是面试最能讲的一点）

---

## 六、最小后端 API 设计

> 项目**已有完整后端**（FastAPI，128 个 REST 端点 + `/ws`，Postgres/SQLite + Redis），因此是**扩展**而非从零搭建。

### 6.1 MVP 最小闭环（先做这个）

| Method | Path | 说明 | 鉴权 |
|---|---|---|---|
| GET | `/api/ai/status` | 改造：返回 capabilities 粒度 | 公开 |
| POST | `/api/ai/greeting` | 首页每日问候（微采集） | 登录 |
| PUT | `/api/admin/ai/config` | 扩展：base_url / model / fallback_models / timeout | 管理员 |

### 6.2 完整 API（增量）

| Method | Path | 说明 | 鉴权 |
|---|---|---|---|
| POST | `/api/ai/insights` | 保留 | 登录 |
| POST | `/api/ai/item-description` | 保留 + 降级 | 登录 |
| POST | `/api/ai/course-summary` | 保留 + 降级 | 登录 |
| POST | `/api/ai/moderation` | 由 `categorize` 改名扩展，**接进发帖流程** | 登录 |
| POST | `/api/ai/price-suggest` | 定价建议（RAG） | 登录 |
| POST | `/api/ai/course-qa` | 选课问答（RAG，带引用） | 登录 |
| POST | `/api/ai/search/items` | 自然语言搜物 | 登录 |

**统一响应约定**：所有 AI 响应携带 `"source": "llm" | "fallback" | "rule"`，前端据此决定是否显示 AI 角标。

### 6.3 数据模型（最小新增）

```sql
-- 生成日志：成本控制 + 可观测（面试可讲"AI 调用可观测"）
CREATE TABLE ai_generation_log (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT,
  capability    VARCHAR(32),     -- greeting / item_description / ...
  model         VARCHAR(64),
  source        VARCHAR(16),     -- llm / fallback / rule
  latency_ms    INT,
  prompt_tokens INT,
  ok            BOOLEAN,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 问候当日缓存
CREATE TABLE user_daily_greeting (
  user_id    BIGINT,
  day        DATE,
  mood       VARCHAR(16),
  focus      VARCHAR(16),
  text       VARCHAR(200),
  emoji      VARCHAR(8),
  source     VARCHAR(16),
  PRIMARY KEY (user_id, day, mood, focus)
);

-- RAG 向量（P3 启用，pgvector）
CREATE TABLE embedding_chunk (
  id          BIGSERIAL PRIMARY KEY,
  source_type VARCHAR(32),       -- course_review / item / post / ...
  source_id   BIGINT,
  chunk_text  TEXT,
  embedding   vector(1024),
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

---

## 七、落地实况（2026-09-06）

P0–P2 已落地，P3/P4 留作 TODO。

**与原方案的一处偏离（更安全的工程选择）**：原方案把 item_description / course_summary 也标为
`degradable: true`。实施时改为 `degradable: false`——失败即友好提示，**绝不返回假数据**
（沿用项目既有"绝不能返回假数据"的设计哲学，润色/画像这类会被当作真实内容发布的语义，
模板兜底是反直觉且危险的）。当前 degradable=true 的能力仅：

- `greeting` → 60 条本地模板（时段 × 状态 × 重点组合 + 日期种子）
- `moderation` → 关键词分类 + 敏感词表规则引擎

**交付清单**：
- 后端：`provider.py`（OpenAI 标准客户端 + LLMError）/ `templates.py`（降级模板库）/
  `models.py`（`ai_generation_log` + `ai_daily_greeting`）/ `service.py` 重写
  （能力级 status + 模型链 + 重试 + 熔断）/ `schemas.py`+`router.py` 新增 `POST /api/ai/greeting`
- 前端：`services/aiService.ts`（合并双客户端 + `getGreeting` 含本地降级）/
  `components/AiGreetingCard.tsx`（微采集 + 换一句）/ `MarketPublish` & `CourseDetail`
  AI 入口能力级 gating；旧的 `services/geminiService.ts` 已删除
- 配置：`school.yaml` `ai` 段扩展（provider/base_url/model/fallback_models/circuit_breaker/
  capabilities）；`.env.example` 增加 `AI_API_KEY`/`AI_BASE_URL`/`AI_MODEL`
- 测试：AI 集成测试从 7 个增至 21 个，全部通过；全量 387/387 通过；前端 `tsc`+`vitest`+`build` 全绿

## 八、实施路线（仍适用于 P3/P4）

| 阶段 | 内容 | 产出 |
|---|---|---|
| **P0** | OpenAI 标准 provider 替换 Gemini 私有协议；status 端点能力级改造；**补 MarketPublish / CourseDetail 入口 gating**；合并双客户端为一套 | 未配 Key 时入口真正隐藏 |
| **P1** | 降级层：模板库 + 模型链 + 重试/熔断 + `ai_generation_log`；`/api/ai/categorize` 接进发帖流程 | 「降级」名副其实，简历可写 |
| **P2** | **首页问候微采集**（前后端 + 缓存 + 换一句 + 本地模板兜底） | 可演示的真实 AI 链路 |
| **P3** | RAG：pgvector + 课程评价问答（带引用）+ 定价建议 | 面试最强亮点 |
| **P4** | 多模态图片识别发布、语义匹配推荐 | 差异化 |

**建议**：P0–P2 完成后再更新简历，届时「直调 + 护栏 + 降级 三层接入」才真正成立，且现场可演示。

---

## 附：审查方法（可复现）

```bash
# 端点实测
python scripts/devctl.py up --foreground
curl http://127.0.0.1:8000/api/ai/status
curl http://127.0.0.1:8000/openapi.json   # 枚举 /api/ai/* 与 /api/admin/ai/*

# 降级真实性核查（均无命中 → 确认不存在）
grep -rn "fallback" backend/app/modules/ai/
grep -rn "categorizePost" frontend/pages frontend/components   # 零调用方
```
