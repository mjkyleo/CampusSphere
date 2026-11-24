# CampusSphere 前端 critique 修复规划

> 依据 impeccable 阶段 5 critique（dual-agent，2026-09-25）结论制定。基线分：**26/40（Acceptable）**，5 个优先问题（1 P0 + 3 P1 + 1 P2）。
> 原则：只改视觉层，保留全部业务逻辑 / 状态 / API / 路由 / 守卫；每批完成后跑 `tsc --noEmit`，全部完成后跑 `vite build` + `vitest` + 桌面/移动截图核对。

## 0. 修复目标（评审优先问题 → 阶段映射）

| 评审问题 | 严重度 | 阶段 |
|---|---|---|
| ReportModal 完全脱离设计系统（rose 语言） | P0 | F1 |
| 移动端底部导航 8 项溢出、无"我的/登录"入口 | P1 | F2 |
| Unsplash 假图 / 假数据冒充真实内容 | P1 | F3 |
| 世界签名交互 PassCard / BoardRow.changed 零引用 | P1 | F4 |
| alert 铬黄被挪用为装饰色 + OAuth 按钮对比度不达标 | P2 | F5 |
| 次要观察项（主按钮色不统一 / admin 举报红字 / 标签贬值 / 头像兜底等） | P2/P3 | F6 |

## F0 · 基元与令牌（先建，后续各阶段依赖）

- [ ] **F0.1 新建 `ImagePlaceholder` 组件**：无图/图加载失败时的中性占位（模块色图标 + 简洁文案），替代 `images.unsplash.com` 兜底与假实拍图。放 `frontend/components/ui/`。
- [ ] **F0.2 alert 语义审计清单**：全局搜 `fill-alert / text-alert / bg-alert`，登记每一处用途（变更信号 or 装饰），作为 F5 的输入。

## F1 · [P0] ReportModal 对齐设计系统

- [ ] 用现有 Button / PassCard 语言重写：ink 实心提交按钮、rounded-md、shadow-elevate、error token 描边/图标块替代 rose-*。
- [ ] 删除全部 `rose-* / rounded-3xl / shadow-2xl / backdrop-blur` 类名。
- [ ] 弹窗支持 Esc 关闭 + 聚焦管理（可访问性）。
- 验收：举报弹窗与全站 ink+hairline+alert 世界一致；error 语义用 error token；无 rose 残留。

## F2 · [P1] Navbar 移动端导航重构

- [ ] 移动底部栏 8 项收敛为 **4 项**（信息板/列表/搜索/我的），其余模块收进顶栏或"更多"入口。
- [ ] 移动端必须可达 **/profile** 与登录/退出。
- [ ] 修复 overflow-x 无提示：默认不横滑，多的项收纳。
- 验收：919px 下底部 4 项不溢出；手机用户可达个人中心与退出。

## F3 · [P1] 假图 / 假数据占位替换

- [ ] 全局替换 `images.unsplash.com` 兜底为 `ImagePlaceholder`（列表 / 详情 / 头像）。
- [ ] MarketPublish：去掉"快速选择示例校园图片库"预填，预填图改空态。
- [ ] ShareFeed：预填假 URL（campus-resources.example.edu）改真实可用的占位 / 留空。
- [ ] 头像兜底：去掉同一张 unsplash 女性照，改中性头像占位。
- 验收：全站无 unsplash 兜底冒充真实内容；发布页默认空态。

## F4 · [P1] 世界签名交互落地

- [ ] 详情页用 `PassCard` 分段卡：MarketDetail / CourseDetail 改造（目标+关键序+登机口动作+扫描码块）。
- [ ] 列表页"新消息 / 新预订 / 变更行"用 `BoardRow.changed` 点亮并保持直到被注意（至少市场列表 / 消息中心）。
- 验收：PassCard 与 changed 点亮出现真实引用；登机牌隐喻从首页延伸到内页。

## F5 · [P2] alert 信号纯度 + OAuth 对比度

- [ ] 按 F0.2 清单逐处审计：只保留 unread badge / 真变更行用 alert；心形 / 评分 / icon 装饰改用 zone 色或 steel。
- [ ] "已预订"等状态徽标：区分 alert（需注意）与 steel/success（中性状态）。
- [ ] 微信 / QQ 登录按钮：加深品牌色或加深色底，达到 WCAG AA（文本对比 ≥4.5:1）；或加底纹/图标块处理。
- 验收：alert 只出现在变更/需注意处；OAuth 按钮对比度达标。

## F6 · 次要观察项批量修复

- [ ] 主按钮色统一：食堂卡片主 CTA 由 zone 实心改 ink（与 market 一致）；模块身份色只留身份位。
- [ ] AdminDashboard 待处理举报：error 红大字改 alert 黄灯行（变更信号语义）。
- [ ] CanteenStall"口碑力推"标签：与数据解耦，去掉标签贬值或按真实字段展示。
- [ ] 首页"热门搭子"列头"需求"与内容"加入"对齐。
- [ ] AdminDashboard rounded-sm/lg 混用收敛为 token 圆角。

## F7 · 验证与交付

- [ ] `tsc --noEmit` PASS；`npx vitest run` PASS；`vite build` PASS（懒加载 chunk 不回退）。
- [ ] 浏览器截图核对：桌面(≥1024) + 移动(≈390) 各代表性页（首页/市场/详情/消息/个人/后台）。
- [ ] 更新 docs/frontend-redesign-plan.md（T5.1 critique 已跑 + 本修复计划引用）。
- [ ] 交付说明：改动范围、验证方式、仍存在缺口（如 OAuth 真实配置缺失属后端项）。
