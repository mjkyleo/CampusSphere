---
target: frontend/pages
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
target_identity: "file:D:\\Phase3\\Projects\\CampusSphere\\frontend\\pages"
timestamp: 2026-09-25T04-36-48Z
slug: frontend-pages
---
Method: dual-agent (A: s_000cXafHdba · B: s_000cXafHN9X)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | 骨架屏+spinner+WS 在线绿点齐备；但 board 数据失败时静默走 mock fallback，无错误行提示；admin 待处理举报用 error 红大字而非 alert 黄灯行 |
| 2 | Match System / Real World | 3 | 文案贴近校园场景；但"芝麻校园分"碰瓷式命名、"双向加密"无证据、ADMIN GATE 术语未解释 |
| 3 | User Control and Freedom | 2 | 删除物品只用 window.confirm 原生弹窗；移动端底部 8 项导航无"我的/登录"入口；弹窗只能点 ✕，无 Esc 关闭 |
| 4 | Consistency and Standards | 2 | ReportModal 是另一套设计语言（rose-600/rounded-3xl/shadow-2xl/backdrop-blur）；AdminDashboard 混用 rounded-sm/rounded-lg；微信/QQ 硬编码 #07C160/#12B7F5 且对比度不足 |
| 5 | Error Prevention | 2 | MarketPublish 预填第一张 Unsplash 图当作用户物品图；ShareFeed 预填假 URL；删除无二次确认设计 |
| 6 | Recognition Rather Than Recall | 3 | 分类 pill 可见、聊天有快捷回复 chips；但"全站搜索"名不副实（只跳 /market?keyword=）；admin 9 个 tab 无分组 |
| 7 | Flexibility and Efficiency | 3 | 路由懒加载、快捷回复、Enter 提交；但无键盘快捷键、无筛选记忆、移动端无搜索入口 |
| 8 | Aesthetic and Minimalist Design | 3 | 中性基底克制、留白好；但 919px 下底部 8 个 icon+标签挤一行、admin tab 溢出截断；Unsplash 实拍图与 UI 风格冲突 |
| 9 | Error Recovery | 3 | Toast+字段级红框+空态 CTA；但 404 通配静默重定向首页、无错误边界、聊天断连只靠一条 toast |
| 10 | Help and Documentation | 2 | 微信/QQ 登录按钮可见但点了只弹"未配置"——死控件；其余无任何帮助入口 |
| **Total** | | **26/40** | **Acceptable（20–27 区间）：基础扎实，但一致性、错误预防、用户控制和帮助四个维度有显著缺口** |

## Design Specificity Verdict

**Verdict: mixed — 外壳是真的，内页是通用的。**

**LLM assessment：** 首页和外壳层是为 CampusSphere 量身定制的——每个模块头部有 mono 大写眉题（MARKET · 二手交易市集 / COURSE · 课程评价社区 / CANTEEN · 食堂航站屏 / TEAM · 组队登机口 / MESSAGE · 实时通信 / ADMIN GATE），导航激活态用对应区域色实心块，主按钮一律 ink 实心、hairline 分割、tabular 价格，加载态文案是"正在登机..."。但一旦离开首页，"航站屏=固定列行+原位重排"的隐喻就消失了：market/course/canteen/teammate/share/job 全部退化成 2-4 列通用 SaaS 卡片网格，换个产品名完全成立。更严重的是，世界签名组件 PassCard（含 mono 扫描码块）和 BoardRow 的 changed/alert 点亮属性都写好了，却没有任何页面真正使用——登机牌隐喻在产品里是缺席的。区域色用对了身份位，但 amber alert 被挪用为装饰色（点赞心形 fill-alert、选中档口评分 text-alert、AI 区块 Sparkles text-alert），信号纯度被稀释。

**Deterministic scan：** impeccable v0.1.5 静态正则扫描 17 个 .tsx 文件返回 0 条（exit 0）。已验证引擎真实运行（engine-probe 输出 impeccable-engine 0.1.5），即使注入满是内联样式的 sanity.tsx 也返回空——该版本非 HTML 正则扫描器不抓渲染后 DOM 问题。所有真实发现来自浏览器渲染模式：
- **/login**：2 条低对比度（微信 #07C160 on #fff = 2.4:1，QQ #12B7F5 on #fff = 2.3:1，均需 4.5:1）+ 1 条 nested-cards
- **/market**：23 条（bu 注入）/ 30 条（引擎 URL 模式）——低对比度 x8（#6b7178 on #f2f3f5 = 4.4:1 / on #e6e8eb = 4.0:1）、过小功能文本 x11（10px "12" badge）、标题节奏 x4（h3 上方 8px vs 下方 45px）、标题层级跳跃 x1（h1 直接到 h3，缺 h2）、图片 hover 变换 x10
- **/**（首页）：9 条 nested-cards（经核实为列表行 border-b 被误判，属过度报告）
- **/admin**：1 条 nested-cards
- **/messages**：2 条

检测器额外捕获了 LLM 评审未明确指出的问题：OAuth 按钮对比度不达标、MarketList 标题层级跳跃（h1→h3）、标题上下间距节奏失衡。nested-cards 在首页和列表页的命中经核实为误报（带 border-b 的列表行被判定为卡片嵌套）。

**Visual overlays：** 浏览器注入成功。preflight 确认可变注入可用（document.title 改为 impeccable-preflight，注入 script 执行 window.__impeccableProbeRan=42）。live-server 监听 127.0.0.1:8400，/detect.js（2.2MB）注入后在首页、market、admin、messages 页均成功执行 window.impeccableScan()，console 输出 findings 与引擎 URL 模式一致。

## Overall Impression

首页的 Board 原语和 mono 眉题系统 genuinely 落地了"登机牌·航站屏"世界——固定列网格、tabular 数据、hairline 行分割，在首页真实复现了航站屏观感。但这个世界只活在首页的四张 board 里：内页全部退化为通用卡片网格，签名组件 PassCard 和 BoardRow.changed 零引用，设计承诺与产品实现之间有断层。最尖锐的问题不是视觉不够好看，而是**信任时刻的设计缺席**——举报诈骗用 rose 粉色另一套语言、删除物品用浏览器原生 confirm、假 Unsplash 图冒充真实商品——这些恰恰是用户最需要产品可靠的瞬间。26/40 说明基础扎实，但一致性（2）、错误预防（2）、用户控制（2）、帮助（2）四个维度拉低了整体。

## What's Working

1. **模块身份色 + mono 眉题系统**：8 个模块各一枚 zone 色，导航激活态/眉题/分类 pill 三处一致使用，扫一眼就知道身在哪个航站区域。这是 DESIGN.md 方案 1 被真正执行的部分。
2. **首页 Board 原语**：固定列网格 + mono 列名 + tabular 数据 + hairline 行，在首页真实复现了航站屏观感，比卡片网格更符合"盯板行动"的世界隐喻。
3. **WebSocket 消息中心的运营质感**：在线/重连态、关联物品条带、快捷回复 chips、乐观发送+去重、上拉补历史并保持视口位置——Operate 模式下完成度最高的一页。

## Priority Issues

### [P0] ReportModal 完全脱离设计系统
- **What**：举报弹窗使用 rose-600 主按钮、rounded-3xl、shadow-2xl、backdrop-blur、rose-50 图标块，与全站 ink+hairline+alert 世界是两个产品；且举报本身是 error 语义却用 rose 粉而非 error token。
- **Why it matters**：举报是用户遭遇诈骗时的高信任时刻。视觉语言的突然切换会让用户怀疑"这是不是同一个 App"，进而怀疑举报是否真的会被处理。error 语义用 rose 粉也削弱了严重性感知。
- **Fix**：用现有 Button/PassCard 语言重写：ink 实心提交按钮、rounded-md、shadow-elevate、error token 边框替代 rose。删除所有 rose-*/rounded-3xl/shadow-2xl/backdrop-blur 类名。
- **Suggested command**：`$impeccable polish`（聚焦 frontend/components/ReportModal.tsx 设计系统对齐）

### [P1] 移动端底部导航 8 项溢出且无"我的/登录"入口
- **What**：919px 宽实测 8 个 icon+标签挤一行且 overflow-x 可滑动；profile/login/退出只在 lg≥1024 的右侧控件渲染。手机用户无法访问 /profile、无法退出登录。
- **Why it matters**：这是导航可达性 bug，不是美学问题。移动端用户（Casey persona）被锁在核心功能之外——无法查看个人资料、无法管理发布、无法退出账号。overflow-x 滚动无渐变提示，用户甚至不知道还有更多项。
- **Fix**：按 DESIGN.md 把移动底部栏收敛为 4 项（信息板/列表/搜索/我的），其余模块收进"更多"或顶栏；profile 必须在移动端可达。
- **Suggested command**：`$impeccable layout`（聚焦 frontend/components/Navbar.tsx 移动端导航重构）

### [P1] Unsplash 假图冒充真实内容
- **What**：AirPods 列表主图是 iPad 实拍、自行车列表也是同一张 iPad、卖家头像全是同一张 unsplash 女性照；MarketPublish 预填第一张 preset 图当作用户物品图；ShareFeed 预填假 URL（campus-resources.example.edu）。
- **Why it matters**：DESIGN.md 反模式明确写"通用 Unsplash 占位冒充真实内容"。二手交易场景里假图直接摧毁信任——用户看到 AirPods 挂着 iPad 照片，会立刻怀疑整个平台的真实性。发布页预填假图更是引导用户用假图上架。
- **Fix**：无图时用中性占位块（图标+模块色），不要用真实照片 URL；发布页预填图改为空态；全局替换 images.unsplash.com 兜底为 ImagePlaceholder 组件。
- **Suggested command**：`$impeccable harden`（聚焦假图/假数据占位替换）

### [P1] 世界签名交互（PassCard/BoardRow.changed）已建未用
- **What**：BoardRow 的 changed 属性、PassCard 的 scanCode 都写好了，但 17 页没有一处传 changed=true、没有一张凭证卡用 PassCard。"登机牌·航站屏"世界的签名交互是空话。
- **Why it matters**：设计特异性的核心缺口。如果把所有 mono 眉题和 zone 色去掉，剩下的列表页和任何校园二手模板没有区别。签名交互（原位重排+alert 保持+扫描码）是让这个产品不可替代的关键，现在只是写了但没人接的组件库。
- **Fix**：至少把 MarketDetail/CourseDetail 改造成 PassCard 分段卡（目标+关键序+登机口动作+扫描码）；新消息/新预订行用 changed 点亮并保持直到被注意。
- **Suggested command**：`$impeccable delight`（聚焦签名交互落地：PassCard 复用 + changed 行点亮）

### [P2] alert 铬黄被挪作装饰色 + OAuth 按钮对比度不达标
- **What**：契约说 alert #FFD400 是唯一变更信号、不兼装饰；实测市集心形徽章 fill-alert、档口选中评分 text-alert、CourseDetail AI 区 Sparkles/spinner text-alert、"已预订"状态 bg-alert。同时检测器确认微信 #07C160（2.4:1）和 QQ #12B7F5（2.3:1）在白底上对比度远低于 WCAG AA 4.5:1。
- **Why it matters**：alert 信号纯度被稀释后，真变更出现时不再亮眼——用户会忽略"有新消息"的铬黄，因为点赞心形也是这个颜色。OAuth 按钮对比度不达标则是可访问性硬伤（Sam persona）。
- **Fix**：全局搜 fill-alert/text-alert/bg-alert 逐处审计，只保留 unread badge 与真变更行；心形/评分/icon 装饰改用 zone 色或 steel；OAuth 按钮加深品牌色或加深色底。
- **Suggested command**：`$impeccable colorize`（聚焦 alert 信号纯度 + OAuth 对比度修复）

## Persona Red Flags

**Casey (Distracted Mobile User)**：底部导航 8 项挤一行、可横向滑动但无渐变提示，用户不知道能滑也找不到"我的"；移动端完全没有登录/退出入口（右侧控件 lg 才渲染）；市集卡片在窄屏仍是大圆角图+大价格，垂直滚动密度低；分类 pill 横滑最后几项（美妆服饰/其他）看不见。**手机用户被锁在个人中心之外。**

**Jordan (Confused First-Timer)**：首页问候"你好，????同学 👋"+随机 AI 洞察，首屏没有引导也没有"这是什么"；微信/QQ 两个登录大按钮点了只弹 toast 说没配置——死控件误导；"芝麻校园分 4.9/5.0"像金融产品，新生不知道是真是假；发布闲置第一步就已经替你选好了一张 iPad 假图。**新用户在信任建立前就被假图和死控件劝退。**

**Sam (Accessibility-Dependent User)**：BoardRow/PassCard 用 div role=button 但无 tabIndex、无键盘 Enter 处理，键盘用户进不了任何一行；导航激活态只靠区域色实心块，无文字粗细/下划线差异；未读 badge 是 10px 铬黄小圆点，对比度与尺寸都弱（检测器确认 undersized-ui-text x11）；Tab 组（profile/admin）无 aria-selected/键盘左右切换；OAuth 按钮对比度 2.3-2.4:1 远低于 4.5:1。**键盘用户和低视力用户无法完成核心浏览流程。**

## Minor Observations

- 首页"热门搭子招募"列表头写"需求"列，实际渲染的是"加入"动作胶囊——列名与数据错位。
- CourseDetail 深色 slate AI 画像面板是全产品最接近 craft bar 的一刻，但里面用 alert 黄做图标色。
- Navbar 头像兜底是同一张 unsplash 女性照，所有未设头像用户长一个样。
- CanteenStall 每道菜都标"口碑力推"，与数据无关，标签贬值。
- AdminDashboard 待处理举报数用 error 红大字，按契约应是 alert 黄灯行。
- CanteenList 食堂卡片主 CTA 直接用 zone-canteen 实心大按钮，而 market 页主按钮是 ink——主按钮色不统一。
- MarketList 标题层级跳跃：h1"二手交易市集"直接到 h3，缺 h2（检测器确认 skipped-heading x1）。
- MarketList h3 标题上方间距 8px、下方 45px，节奏失衡（检测器确认 heading-rhythm x4）。
- 发布页"快速选择示例校园图片库"5 张 unsplash 缩略图暗示用户可以用假图上架。
- 404 通配静默重定向首页，无错误边界组件。

## Questions to Consider

- 如果把所有 mono 眉题和 zone 色都去掉，剩下的列表页和任何一个校园二手模板有区别吗？——登机牌世界是不是只活在首页的四张 board 里？
- 签名交互（原位重排+alert 保持+扫描码）是设计承诺还是只是写了但没人接的组件库？产品价值到底在哪一行上被用户感知到？
- 为什么产品里信任等级最高的两个时刻——举报诈骗、删除自己的东西——一个用 rose 粉色另一套语言、一个用浏览器原生 confirm，反而是最低设计优先级？
