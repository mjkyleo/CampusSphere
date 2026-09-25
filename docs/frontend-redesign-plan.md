# CampusSphere 前端视觉重设计 · 任务清单

> 依据 impeccable（v4.3.1）技能方法论制定。本文件是**计划与任务跟踪**，不含代码改动。
> 当前轮不修改任何前端代码；本清单供执行阶段逐项核对与打勾。

## 0. 已确认的决策

| 决策点 | 结论 |
|---|---|
| 重构含义 | **视觉 / UX 全面重设计**（redesign：替换现有视觉世界，保留产品事实 / 内容 / 功能 / 约束） |
| 主导模式 | Operate（任务完成型 App UI），首页 / 管理后台按场景微调 |
| 范围 | 按 surface 分组，覆盖全部 16 页面 + 外壳/导航 + 3 路由守卫 + 2 验证码组件（已确认） |
| 品牌资产 | **我方自定策略**：执行阶段不阻塞于真实品牌素材；先用中性占位 + DESIGN.md 内标注“待用户提供”清单，主流程零阻塞 |
| 新指令冲突 | 以最新指令为准，偏离前说明理由并取得同意 |

## 1. 已核实的现状证据（执行前基线，勿凭印象）

- 项目内**无 PRODUCT.md / DESIGN.md**；`.impeccable` 仅 `config.local.json`（hook 同意）。
- `tailwind.config.js` 的 `theme.extend` 为**空** → 无任何定制设计令牌。
- `index.css` 仅 Tailwind base + Inter 字体 + `.glass-effect` / `.no-scrollbar` 两个工具类 → 无设计系统。
- 外壳视觉：`bg-slate-50/60 + text-slate-800 + indigo-600` 主色（loading 转圈亦 indigo）→ 默认 Tailwind 观感，作为“反例 / 被替换对象”。
- 前端规模：16 页面 + 7 组件（含 AdminRoute / ProtectedRoute / PublicOnlyRoute / GeetestCaptcha / SliderCaptcha）+ AuthContext / ToastContext + useWebSocket + services(api / geminiService / websocket)。
- 技术栈：React 19 / TypeScript / Vite 6 / Tailwind 3 / react-router-dom 7 / recharts / lucide-react；Express 5 作代理层。
- **待核实异常**：`node_modules` 含 `@reduxjs/toolkit / react-redux` 但 `package.json` 未声明 → 执行阶段第一步核实是否真在使用，圈定状态管理范围。

## 2. 不变量（重设计必须保留，属产品事实）

- 全部业务内容、功能行为、表单逻辑、路由结构、鉴权规则（PublicOnly / Protected / Admin）。
- 多校可配置语义（`config/school.yaml` 驱动）与 AI 可开关降级（无 Key 时入口自动隐藏）在 UI 上对应的行为。
- WebSocket 即时消息、举报、验证码等既有交互流。

## 3. 任务清单

> 状态图例：⬜ 待办 · 🟦 进行中 · ✅ 完成
> 验收标准逐项列出，供完成时勾核。

### 阶段 0 · 启动与上下文
- [ ] **T0.1 加载 impeccable 上下文**（`impeccable context`；启动器不可用则按技能回退直接读现有上下文）。核对 tokens / CSS / 组件与重构目标无冲突。验收：上下文就绪、现状基线与本清单第 1 节一致。
- [ ] **T0.2 确认路线**：无 DESIGN.md 且为重设计 → `init → new-work`（替换视觉世界，不在旧观感上打磨）。验收：路线记录在案。

### 阶段 1 · 固化产品事实（`init` → 产出 PRODUCT.md）
- [ ] **T1.1 写 PRODUCT.md**：定位（一站式校园生活平台）、用户（本校师生）、8 大模块（账号 / 二手 / 课程 / 食堂 / 兼职分享组队 / 即时消息 / 举报 / 管理后台 + AI）的核心任务与品牌基调；来源以 README 与现有页面为准，不编造。验收：每项事实可回溯来源。
- [ ] **T1.2 定义模块“成功画面”与模式**（以 Operate 为主）。验收：每个 surface 有明确模式。

### 阶段 2 · 确定重设计方向（`new-work` → 产出 DESIGN.md + surface briefs）
- [ ] **T2.1 确立新视觉世界**（配色 / 字体 / 材质 / 动效基调），写入 DESIGN.md，替换 slate/indigo 默认观感。验收：DESIGN.md 完整、可执行（token 已落到具体值）。
- [ ] **T2.2 为每个 surface 写 brief**：auth / shell / home / course / market / canteen / social / messaging / profile / admin。验收：10 个 brief 齐全，各含成功画面与约束。

### 阶段 3 · 设计系统地基
- [ ] **T3.1 建立设计令牌**：品牌色 + 中性色 + 语义色、字体阶、间距 / 圆角 / 阴影 / 描边、动效时长与缓动 → 写入 `tailwind.config.js`（当前 `theme.extend` 为空）+ CSS variables。验收：无硬编码颜色 / 字号残留于页面。
- [ ] **T3.2 建组件基元库**：按钮 / 输入 / 卡片 / 徽标 / 导航 / 列表 / 骨架 / 空态 / 错误 / 加载；从现有组件 `extract` 可复用 token 与组件。验收：基元可复用、命名一致。
- [ ] **T3.3 响应式断点系统**（移动优先）+ 暗色 / 主题决策。验收：断点覆盖移动 / 平板 / 桌面。
- [ ] **T3.4 核实 redux 实际使用情况**，圈定状态管理在重构中的范围。验收：结论落档（使用则纳入，未使用则清理声明 / 注明）。

### 阶段 4 · 逐 surface 重设计（保留内容与功能，替换视觉）
> 每页验收通用项：视觉层级、空 / 错误 / 加载态、表单与可交互态（hover / focus / disabled / loading）均已重画且一致。
- [x] **T4.1 外壳与导航**：App shell（loading / 背景 / 主色）、Navbar、ReportModal、3 个路由守卫门禁态。
- [x] **T4.2 认证**：LoginPage、AdminLoginPage（含 Geetest / SliderCaptcha 交互态）。
- [x] **T4.3 首页**：HomePage。
- [x] **T4.4 课程**：CourseSearch、CourseDetail、CourseReview。
- [x] **T4.5 二手**：MarketList、MarketDetail、MarketPublish。
- [x] **T4.6 食堂**：CanteenList、CanteenStall。
- [x] **T4.7 社交 / 兼职**：TeammatePost、ShareFeed、JobList。
- [x] **T4.8 消息**：MessageCenter（含 WebSocket 在线 / 断开态）。
- [x] **T4.9 个人**：UserProfile。
- [x] **T4.10 管理后台**：AdminDashboard（recharts 看板）。

> **阶段 4 执行说明（完成时追加）**：全部 16 页已按“登机牌·航站屏”世界重写，业务逻辑 / 状态 / API / 守卫原样保留。后台 AdminDashboard 采用 code-led 令牌替换（9 个 Tab，2053 行）。执行中发现并修正一处系统性缺陷：主题字号键为 `heading-1…`，Tailwind 生成的工具类带 `text-` 前缀，初版误用裸 `heading-*`，已用正则全量改为 `text-heading-*`（50 处，含裸 `caption` 1 处）。验证：全量 `tsc --noEmit` PASS、`vite build` PASS（2335 模块）；真实渲染抽查首页与登录 / 后台登录页符合世界契约。

### 阶段 5 · 评估（`critique` + `audit`）
- [x] **T5.1 启发式评审**（critique）：每 surface 的清晰 / 反馈 / 一致 / 层级 / 认知负荷。验收：每 surface 有评分与问题清单。
- [x] **T5.2 无障碍 audit**：WCAG 对比度、focus、ARIA、键盘可达（含验证码组件）。验收：无 A 级违例。
- [x] **T5.3 性能 audit**：路由懒加载、包体、图片尺寸、recharts 使用方式。验收：问题项列清单并排优先级。
- [x] **T5.4 响应式 adapt**：断点全覆盖（移动优先）。验收：三档断点均无溢出 / 遮挡。

> **T5.2 无障碍已执行**：OAuth 按钮对比度达标（微信 #0B7A3B、QQ #0E6FA8，实测 5.44:1）；全局 `:focus-visible` 焦点环（index.css）；BoardRow 加 tabIndex=0 + Enter/Space 键盘激活；过小功能文本 text-[10px]→text-[11px]（Navbar 未读、MarketList 点赞、MessageCenter 未读、MarketPublish 提示、TeammatePost 状态、AdminDashboard 封面）；MarketList 标题层级 h1→h3 跳跃修正为 h1→h2。
> **类型健全（@types/react 已安装）**：审计中发现项目原本**未安装 @types/react**（React 类型为隐式 any）。已安装 `@types/react@^19.3.0` + `@types/react-dom@^19.3.0`，`tsc --noEmit` 仅暴露 6 处真实类型错误并全部修复：①`api.admin.reports` 返回类型由 `ReportOut[]` 更正为 `AdminReportOut[]`（后台接口实际为管理员工单形态）；②AdminDashboard 三处 setState 补全缺失的 `image` 字段；③CourseSearch `review_count`→`reviews_count`（字段名与类型对齐）；④JobList `getSalaryLabel` 参数放宽为 `SalaryType | string`。ErrorBoundary 随之从鸭子类型改为标准 `extends React.Component<Props, State>`。tsc / vite build / vitest 均通过（14/14）。
> **T5.4 响应式已核对**：544px（移动，5 项底部导航+更多抽屉）、~800-922px（中档）均无溢出；桌面 ≥1024 导航为既有无改动版本（此前轮次已截图核对）。受限于浏览器窗口最大宽度，>1024 断点本轮未复拍。

> **T5.1 critique 已执行（dual-agent）**：双隔离子代理（设计评审 A + 检测器/浏览器证据 B），**总分 26/40（Acceptable）**。报告与快照见 `.impeccable/critique/2026-09-25T04-36-48Z__frontend-pages.md`；detector 为浏览器渲染模式（TSX 静态扫描器不抓 DOM）。
> **critique 修复已按 `docs/frontend-critique-fix-plan.md` 落地（F0–F6）**：F0 ImagePlaceholder 基元；F1 [P0] ReportModal 对齐设计系统（error 语义 / ink 按钮 / Esc 关闭 / focus 管理）；F2 [P1] Navbar 移动端 8→4 主项 + 我的/登录入口 +「更多」抽屉；F3 [P1] 假图/假数据替换（发布页预填图库删除、分享假 URL 清空、头像/列表/详情占位）；F4 [P1] PassCard 落地 MarketDetail「交易登机牌」/ CourseDetail「选课登机卡」+ HomePage BoardRow.changed 点亮 + 搭子列头修正；F5 [P2] alert 信号纯度（心形/评分/AI 装饰移出）+ OAuth 对比度达标（微信 #0B7A3B、QQ #0E6FA8，均 5.44:1）；F6 主按钮统一 ink（CanteenList / ShareFeed）+ CanteenStall 标签去伪 + 举报度量改 alert 徽标。
> **验证**：`tsc --noEmit` PASS、`vite build` PASS（主 chunk 312KB）、`vitest` 14/14 PASS；真实渲染核对（移动 544px 视口）——移动端 5 项导航 +「更多」抽屉、假图→占位、PassCard 两处、搭子列头「动作」、登录/OAuth 均正确。

### 阶段 6 · 打磨与强化
- [x] **T6.1 harden**：错误 / 空 / 边界态、i18n、表单校验反馈、WebSocket 断开恢复。验收：各失败路径有可用界面。
- [x] **T6.2 clarify**：UX 文案 / 标签 / 错误信息。验收：无歧义、无技术性报错原文直出。
- [x] **T6.3 typeset / layout**：字体层级、间距节奏、视觉层级。验收：层级分明、节奏一致。
- [x] **T6.4 animate / colorize / delight**（按需，避免过度）。验收：动效有目的、不影响可达性与性能。
- [x] **T6.5 optimize**：落地性能修复项。验收：T5.3 问题项已处理或明确延后。

> **T6 打磨已执行**：T6.1 harden——新增 **404 页**（NotFound，替代静默重定向）与**路由级 ErrorBoundary**（渲染异常降级界面，原为白屏/重定向）；T6.2 clarify——"芝麻校园分"→"校园信用分"、"双向加密"→"加密传输"、OAuth 死控件改明确"未接入"禁用态+说明文案；T6.3——MarketList 标题层级修正；T6.4——已评估不需额外动效（登机牌世界动效已有 duration-rerank，避免过度）；T6.5——路由懒加载与 recharts 独立 chunk 已落地（主 chunk 315KB）。

### 阶段 7 · 验证（impeccable 关键约束：有界通过，不做无限自 QA）
- [x] **T7.1 全量构建后一次性批量检查**（桌面 + 移动截图一起看），一轮修完所有发现。
- [x] **T7.2 至多再一轮确认后停止打磨**。
- [x] **T7.3 三件套**：`tsc --noEmit`（lint）+ `vitest run`（test）+ `vite build`（build）；应用可运行时用视觉回归金样兜底。
- [x] **T7.4 逐 surface 截图交叉核对**：内容与功能未被破坏。

> **T7.4 逐 surface 核对已执行（登录态 verify_7339，~800-920px 视口）**：逐路由 innerText 确认渲染 + 关键页截图——`/`（首页信息板 + 首行 changed 点亮）、`/market`（MARKET 眉题 / 4 列卡片 / 占位）、`/courses`（COURSE / 学部院系 pill）、`/courses/review`（评课登机口表单）、`/canteens`（CANTEEN 航站屏 / 4 食堂卡片 / 学部·类型筛选）、`/teammates`（TEAM 组队登机口 / 分类 pill / 空态 CTA）、`/share`（SHARE 资源库 / 分类）、`/jobs`（JOB 勤工登机口 / 分类）、`/messages`（MESSAGE / 空态 / 加密传输）、`/profile`（已认证学生 / 4 Tab / 资料表单 / 退出）、`/admin`（守卫重定向 `/admin/login`，ADMIN GATE）。空态验证：`/canteens/1`（未找到该食堂）、`/market/1`（不存在或已下架）、`/courses/1`（未找到对应课程）均正确降级。**注意**：搭子/分享路由为 `/teammates`、`/share`（非 `/community`、`/shares`，后者本就 404，属正确行为）。观察项（非本轮引入）：页面挂载首帧 Navbar 短暂显示「登录」后恢复用户头像——AuthContext 异步初始化瞬时态，非视觉重设计破坏，如需消除可在 AuthProvider 增加就绪门控。

> **遗留缺口闭合（本轮）**：
> - **T5.3 性能——路由懒加载已落地**：App.tsx 全量改用 `React.lazy + Suspense`（fallback「正在登机...」）。`vite build` 主 chunk **934KB → 307KB**（gzip 99KB），AdminDashboard(含 recharts 447KB) 独立懒加载，>500KB 告警消失。
> - **T7.3 vitest 已运行**：`vitest run` → **2 文件 / 14 用例全 PASS**（RouteGuards 9 + SliderCaptcha 5）。
> - **T7.4 消息 / 后台两页登录后核对完成**：原后端(8000)未运行致此前无法登录；本轮启动后端(Python 3.11 + uvicorn, dev.db)后登录核对——AdminDashboard 概览（ADMIN 眉题 / 9 Tab / 指标卡 / INK 描边 DAU·成交图表）与 MessageCenter（MESSAGE 眉题 / 会话列表 / 空态 / 消息导航选中态=石板蓝）均按世界契约正确渲染。凭证：管理员 `admin/admin123`（dev.db 种子，网关密钥取自 school.yaml）；核对消息页时经 API 注册普通用户 `verify_7339`。

### 阶段 8 · 交付与文档
- [x] **T8.1 替换 DESIGN.md + 落盘各 surface brief**。
- [x] **T8.2 交付说明**：验证方式、覆盖范围、遗留缺口。
- [x] **T8.3 可选 `doctor`**：检查上下文漂移。

> **T8 已执行**：T8.1——DESIGN.md 已替换（含第 9 节 Surface Map），surface briefs 已落盘 `.impeccable/surface-briefs.md`（10 面成功画面 / 约束 / 世界签名）；T8.2——交付说明见本轮回复；T8.3——`impeccable doctor` 已运行。
> **小问题收尾（本轮）**：①**doctor 漂移已修复**——DESIGN.md 顶部新增标准 YAML frontmatter（colors/typography/rounded/spacing/components tokens，值取自 `tailwind.config.js`，live panel 现可渲染真实 token）；`.impeccable/design.json` 补 `schemaVersion: 2`；`impeccable doctor` 重跑 → **No drift found**。②**auth 首帧「登录」闪烁已消除**——Navbar 用 AuthContext 既有 `loading` 门控：auth 未就绪时用户槽渲染中性骨架占位（`…`），不再误显示「登录」入口（桌面用户区 + 移动 ProfileSlot 均覆盖）。验证：tsc 0 错误 / build PASS / vitest 14/14。

## 4. 品牌资产占位策略（我方自定）

- 执行阶段**不因缺素材而阻塞**：优先用中性占位 / 插画式处理完成设计；在 DESIGN.md 中单列“待用户提供”清单（如正式 Logo、真实校园 / 食堂 / 二手商品示例图、品牌主视觉）。
- 任何占位均标注“占位，待替换”，不伪装成真实素材。
- 素材到位后再做一次性替换与 T7 验证，不中途返工旧观感。

## 5. 验证与交付约定（沿用技能要求）

- 构建完整 → 桌面 + 移动一次批量查看 → 一轮修复 → 至多一轮确认 → 停止。开环自 QA 视为失败。
- 所有结论区分“已核实”与“待验证”；证据不足处显式标注不确定性与验证办法。
