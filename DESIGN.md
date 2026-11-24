---
name: CampusSphere
description: 校园一站式生活平台 · 登机牌 · 航站屏视觉系统
colors:
  ink: "#0B0D10"
  slate: "#1C2127"
  steel: "#6B7178"
  panel: "#E6E8EB"
  surface: "#FFFFFF"
  ground: "#F2F3F5"
  hairline: "#D8DADD"
  alert: "#FFD400"
  success: "#1B6E3C"
  error: "#B3261E"
  zone-home: "#0B0D10"
  zone-market: "#B45309"
  zone-course: "#1E4FA0"
  zone-canteen: "#C2410C"
  zone-teammate: "#0F766E"
  zone-share: "#6D28D9"
  zone-job: "#4D7C0F"
  zone-message: "#475569"
typography:
  display:
    fontFamily: '"Space Grotesk", system-ui, sans-serif'
    fontSize: "2.75rem"
    fontWeight: 700
    lineHeight: 1.05
  heading-1:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.2
  heading-2:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
  heading-3:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
  label-mono:
    fontFamily: '"IBM Plex Mono", ui-monospace, monospace'
    fontSize: "0.6875rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.08em"
    textTransform: uppercase
  data-mono:
    fontFamily: '"IBM Plex Mono", ui-monospace, monospace'
    fontSize: "0.8125rem"
    fontVariantNumeric: tabular-nums
rounded:
  sm: "0.25rem"
  md: "0.5rem"
  lg: "0.75rem"
  board-row: "0"
spacing:
  "1": "0.25rem"
  "2": "0.5rem"
  "3": "0.75rem"
  "4": "1rem"
  "6": "1.5rem"
  "8": "2rem"
  "12": "3rem"
  "16": "4rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    typography: "{typography.label-mono}"
    rounded: "{rounded.sm}"
    padding: "12px 20px"
  button-primary-hover:
    backgroundColor: "{colors.slate}"
    textColor: "{colors.surface}"
    typography: "{typography.label-mono}"
    rounded: "{rounded.sm}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label-mono}"
    rounded: "{rounded.sm}"
    padding: "12px 20px"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 16px"
  card-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "16px 16px"
  badge-alert:
    backgroundColor: "{colors.alert}"
    textColor: "{colors.ink}"
    typography: "{typography.label-mono}"
    rounded: "{rounded.sm}"
---

# DESIGN

<!-- 世界：登机牌 · 航站屏（Boarding Pass & Gate Board）· 方向契约 · 依据 PRODUCT.md -->

> 视觉世界由用户在本轮方向决策页选定（challenger: vernacular-ephemera-boarding-pass-and-gate-board）。构建路径 **code-led**。craft bar 基准：`.impeccable/craft/boarding-hero.webp` 与 `boarding-board.webp`。按 impeccable 流程，替换世界的 DESIGN.md 本应在构建完成时由文档器从成品回写；此处按用户要求先落为「已确立方向 + 设计系统」，在逐 surface 构建完成后做最终校验回写（见「收尾」节）。

## 1. 世界陈述（World）

CampusSphere 是校园的**实时信息枢纽**：学生像在航站楼里一样"盯板、抓准登机口、行动"。每个模块 / 每个条目都像一张**分段登机牌**（把你带向一门课、一个档口、一件闲置、一个搭子、一份兼职）；各模块首页与关键列表是**实时航站屏**——按关键序（时间 / 热度 / 评分 / 价格）原位重排的行，任何**变更以唯一警示色点亮并保持，直到你注意到**。

**模式**：全局 Operate（可扫读、一致、原生预期 > 表达）。首页作为中枢以 Operate 为骨架；管理后台是"调度控制板"，同样克制。

**自检**：拒绝当前默认观感（靛紫渐变 hero + 六色浅彩模块卡 + 玻璃拟态 + 超大圆角 blob）；拒绝"蓝白政务门户"。任何一屏若看起来"是随便一个校园 App 都能猜中的样子"，即自检失败，须回炉。航站隐喻不得遮蔽任务、状态与熟悉操作（Operate 铁律）。

## 2. 方向契约（Direction Contract）

- **THESIS**：校园生活 = 盯航站屏、抓准登机口；界面 = 分段凭证（登机牌）+ 实时重排信息板。拒绝"渐变 + 玻璃 + 多彩贴纸"的默认校园观感。
- **OWN-WORLD**：高对比中性色（INK / SLATE / STEEL / PANEL / SURFACE），**唯一警示色铬黄 #FFD400 只留给"变更 / 需注意"**；mono 大写 UI 标签 + tabular 数据 + mono 扫描码块；行身份保持的原位重排；底部导航。
- **STORY**：学生打开即见"屏上有变动、有方向"；先看板 → 选一行 → 看凭证 → 行动即达；变更永不静默，已办从板上退场。
- **FIRST VIEWPORT**（首页）：顶部 = 全局"找"查询台 + 导航；主体 = 多块实时信息板（二手最新 / 热搜 / 课程 / 食堂 / 搭子），每行 = 关键序 + tabular；变更行亮警示色并保持；底部栏。
- **FORM**：航站屏 + 分段凭证融合成一套 Operate 语言；mono 标签 / 数据、tabular 数字、行身份原位重排为**签名交互**。
- **FINISH**：unreviewed and undocumented is unfinished；本轮以 finish review、DESIGN.md、每张交付栅格带 provenance 为结束条件。

## 3. 色彩（Color）

物理场景：学生在课间、户外与食堂日光灯下用手机，光线亮 → **浅色优先、高对比**。深色模式为未决项，暂不默认（记录为开放决策）。

**策略**：Restrained（中性基底 + 单警示色）。模块间靠 PANEL / SLATE 处理与 mono 标签区分，**不靠多色散射点缀**。

| 角色 | Token | 值 | 用途 |
|---|---|---|---|
| 墨色 / 主文本 | `ink` | `#0B0D10` | 标题、正文、主按钮 |
| 深灰 / 面板内文字 | `slate` | `#1C2127` | 次级文字、深面板 |
| 钢灰 / 次文本 | `steel` | `#6B7178` | 说明、标签、禁用 |
| 面板 | `panel` | `#E6E8EB` | 面板底、信息板行底 |
| 表面 / 卡片 | `surface` | `#FFFFFF` | 卡片 / 凭证底 |
| 地面 | `ground` | `#F2F3F5` | 页面底 |
| 分隔 | `hairline` | `#D8DADD` | 发丝分隔 |
| **警示 / 变更** | `alert` | `#FFD400` | **仅**变更 / 需注意 / 新状态（原位置重排点亮） |
| 成功 | `success` | `#1B6E3C` | 成功反馈（功能语义，克制） |
| 错误 | `error` | `#B3261E` | 错误（功能语义，克制） |

规则：`alert` 是**品牌级唯一警示色**，只出现在"需要你注意的变更"上；**不兼任主按钮 / 品牌强调色**（主按钮用 `ink` 实心），以保证信号纯粹；success / error 属功能语义、低频使用，不与 alert 混用；任何 12 字以下正文在 INK / ALERT 底上满足 WCAG AA 对比。

**区域色（Zone Accent · 已确认 方案1）**：为使"模块 = 可导航区域"的导视记忆更强，为 8 个导航模块各配一枚**区域身份色**（中性基底 + 单警示色的世界不变；区域色只是身份层，克制使用）。用法**仅限身份位**——导航激活态、模块头标 / 眉题标记、徽标底、对应板块关键动作；页面基底、正文、面板仍走中性，变更仍只归 `alert`。

| 模块 | 区域色 | 值 | 依据 |
|---|---|---|---|
| 首页 | 中性 ink | `#0B0D10` | 中枢 / 基底 |
| 二手 | 琥珀 | `#B45309` | 交易 / 价值 |
| 课程 | 深蓝 | `#1E4FA0` | 学术 / 信任 |
| 食堂 | 陶土橙 | `#C2410C` | 餐饮 / 暖 |
| 搭子 | 青绿 | `#0F766E` | 同伴 / 社区 |
| 分享 | 紫 | `#6D28D9` | 资料 / 创作 |
| 兼职 | 橄榄 | `#4D7C0F` | 收入 / 勤工 |
| 消息 | 石板蓝 | `#475569` | 通信 / 中性 |

规则：区域色不与 `alert` 冲突（`alert` 仍唯一管"变更 / 需注意"）；每枚区域色只作身份强调、不作大面积填充，保证高对比与可扫读。

## 4. 字体（Typography）

- **Body / UI / 表单**：**Inter**（既有，UI 工作马）。
- **所有 UI 标签 + 数据（tabular）+ 扫描码块**：**IBM Plex Mono**（mono，风格档位 B：更强）。**全部 UI 标签——按钮文字、导航项、眉题、信息板列名、凭证字段名——一律 mono 大写**（`text-transform: uppercase` + letter-spacing），仪表感更重；数字一律 `font-variant-numeric: tabular-nums`。
- **展示 / 登机口大数**（h1、关键数字、大号 "门牌"）：**Space Grotesk**（bold）。回退 `system-ui`。

| 尺度 | 字号 / 行高 | 用途 |
|---|---|---|
| display-gate | 2.75–3rem / 1.05，700 Space Grotesk | 大号关键数字、hero 数据 |
| heading-1 | 1.75rem / 1.2，600 | 区块主标题 |
| heading-2 | 1.25rem / 1.3，600 | 卡片 / 板标题 |
| heading-3 | 1rem / 1.4，600 | 条目标题 |
| body-1 | 0.9375rem / 1.5 Inter | 正文 |
| body-2 | 0.8125rem / 1.45 | 辅助说明 |
| caption | 0.75rem / 1.4 | 时间戳、小标签 |
| mono-label | 0.6875rem / 1.3，uppercase 0.08em | **所有 UI 标签**：按钮、导航、眉题、列名、字段名 |
| mono-data | 0.8125rem，tabular | 价格 / 时间 / 编号 / 确认码 |

规则：价格、数量、时间、编号一律 tabular；mono 只用于标签 / 数据 / 扫描码块，不做大段正文。

## 5. 间距 / 圆角 / 阴影 / 动效（Spacing · Radius · Shadow · Motion）

- **间距**：4pt 基线 `--sp-*`：1–2–3–4–6–8–12–16（0.25rem 起）。板块间距 > 卡片间距 > 行间距；标题上方留白 > 下方。
- **圆角**：面板感、克制——`--radius`：sm 0.25rem（按钮 / 输入）、md 0.5rem（卡片 / 凭证段）、lg 0.75rem（面板 / 弹层）、0（信息板行）。**废除** 3xl 超大 blob。
- **阴影**：少——`--shadow`：none / hairline（仅分隔，无投影）/ surface（1 层弱，卡片）/ elevate（弹层）。默认不堆投影。
- **动效**：`--ease` cubic-bezier(0.2,0,0.3,1)；`--dur` 120–200ms（反馈）/ 260–320ms（重排 / 过渡）。**签名交互 = 行身份原位重排**（rerank in place）：数据变动时行不消失重来，而在原位移动、变更行亮 `alert` 并保持，直至被注意；已办 / 已读行退场。提交 / 刷新可有一拍轻微 overshoot。默认内容可见；禁止无意义 hover 抖动与全局装饰动效。

## 6. 布局与响应式（Layout & Responsive）

- **移动优先**：断点 `sm 640 / md 768 / lg 1024 / xl 1280`；导航在移动端为**底部栏**（映射为区域：信息板 / 列表 / 搜索 / 我的），桌面为顶部栏。
- **信息板（board）**：固定列网格（如 `列名 = 关键序 + 目标 + 动作 + 状态`），行 = 控件；窄屏按优先级收列、**不缩字号**。
- **凭证（pass）**：分段卡片；窄屏段纵向堆叠，tabular 数字保持。
- 外壳：`ground` 底、墨色文本；登录 / 后台登录不渲染导航（保持路由约束）。

## 7. 组件语言（Component Language）

- **信息板（Board）**：固定列网格行；行即控件；变更行亮 `alert` 并保持；已办退场；空板给空态 + 可行动作。
- **登机牌凭证（Pass / Card）**：分段式卡片——`目标（模块 / 分类）` + `关键序（时间 / 热度 / 评分 / 价格，tabular）` + `动作（联系 / 加入 / 购买 = 登机口）`；交易 / 验证场景带 mono **扫描码 / 确认码块**。
- **按钮**：primary（`ink` 实心，按下 0.98）、secondary（hairline + 墨文本）、text（墨 + 方向箭头）；按钮文字一律 **mono 大写**；active 态明确；清晰 :focus-visible。
- **输入 / 搜索（"找"查询台）**：hairline 描边，聚焦显 `ink` 环；全局搜索是首页主入口；确认码类输入用 mono 回显。
- **导航**：底部栏（移动）/ 顶部栏（桌面），导航项文字一律 **mono 大写**；激活项以该模块**区域色**作激活身份（实心 / 标记 / 下划线），中枢"首页"仍用 ink。
- **状态**：加载（骨架 / 板行脉冲）、空态（空板 + 一句可行动文案 + 下一步）、错误（行 / 弹条亮 `alert` 或 `error` + 可重试）、禁用（明确不可点）、**变更（原位重排 + alert 保持）**。

## 8. 反模式（明确拒绝 / 旧世界）

- 靛紫渐变 hero、玻璃拟态毛玻璃、超大 `rounded-3xl` blob、六色浅彩贴纸图标。
- **静默更新**（数据变了用户毫无察觉）。
- 通用 Unsplash 占位冒充真实内容；无数据时的假预览。
- 无意义装饰动效、无限 hover 抖动。

## 9. 各 surface 指引（Surface Map，映射为登机牌 / 航站屏）

| Surface | 页面 | 要点 |
|---|---|---|
| shell | App / Navbar / 守卫 / ReportModal | 航站屏式导航 + 底部栏 + 全局"找"；loading 用骨架；守卫态清晰 |
| auth | Login / AdminLogin | 凭证式表单；验证码呈现为扫描码 / 确认码块；状态明确 |
| home | HomePage | 查询台 + 多块实时信息板（二手 / 课程 / 食堂 / 搭子 / 热搜），变更行 alert 保持（见 FIRST VIEWPORT） |
| market | MarketList / Detail / Publish | 闲置=登机牌（价格 / 分类 / 卖家 / 联系=登机口）；列表=信息板；发布=强引导凭证表单 |
| course | CourseSearch / Detail / Review | 课程=凭证（名称 / 教师 / 评分）；评价=板；AI 摘要如实标注 |
| canteen | CanteenList / Stall | 档口 / 菜品=凭证 + 板；口味 / 评分 tabular |
| community | TeammatePost / ShareFeed / JobList | 招募 / 共享 / 兼职=凭证；申请=登机口动作；流转清晰 |
| messaging | MessageCenter | 会话=实时重排板；新消息=alert 保持；WebSocket 在线 / 断开态明确 |
| profile | UserProfile | 一卡通式个人凭证卡（个人信息 + 关键数据） |
| admin | AdminDashboard | 调度控制板：看板 + 举报 / 工单=需处理的行，alert 保持；发丝排版 |

## 10. 收尾与演进（Finish & Governance）

- 本 DESIGN.md 为「已确立方向 + 设计系统」；逐 surface 构建完成后按成品回写校验，确保令牌与实装一致（token-bearing + `.impeccable/design.json`）。
- 令牌与 CSS 落地以 `tailwind.config.js` `theme.extend`（当前为空）与 CSS variables 为准；任何硬编码颜色 / 字号视为违例。
- **craft bar**：以所选世界 hero / 看板（`.impeccable/craft/`）为完成度基准，构建达到其工艺与承诺水平，但为 CampusSphere 服务、非照抄构图。
- 品牌资产占位：正式 Logo / 真实校园素材未到位前用中性占位，单列"待用户提供"清单，不伪装真实。
- 暗色模式、深色令牌为开放决策，进入时单独评审。
