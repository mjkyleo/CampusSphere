# 端到端测试（Playwright）

覆盖 **8 个核心用户旅程场景**，采用**页面对象模式（Page Object Model）**组织：
页面结构变化时只改 `pages/` 下的一个类，`tests/` 里的用例无需改动。

## 场景清单

| 文件 | 场景 | 对应需求 |
|---|---|---|
| `01-home-browsing.spec.ts` | 首页渲染、公开列表加载、未登录可浏览、无 JS 报错 | 主页访问 |
| `02-register.spec.ts` | 填表 → 获取验证码 → 注册成功并自动登录；重复邮箱被拒 | 用户注册（正常 + 异常） |
| `03-login-session.spec.ts` | 正确登录、错误密码、刷新后会话保持 | 登录鉴权 |
| `04-unauthorized-redirect.spec.ts` | 发布/消息/个人中心/管理后台未登录时重定向登录页 | 未登录重定向 |
| `05-publish-and-bargain.spec.ts` | 发布 → 列表可见 → 详情 → 发起议价生成会话 | 二手发布 |
| `06-messaging.spec.ts` | 进入会话、发送消息、消息可见 | 即时消息 |
| `07-admin-moderation.spec.ts` | 管理员登录 → 举报工单面板 | 管理后台 |
| `08-course-review.spec.ts` | 课程列表浏览、空态、评价页受登录保护 | 课程评价 |

## 快速开始

```bash
cd e2e

npm install                        # 安装 @playwright/test
npx playwright install chromium    # 首次需要下载浏览器内核

npm run reset-db                   # 可选：删除上次遗留的 e2e_test.db
npm test                           # 运行全部场景
npm run test:headed                # 有界面模式（调试选择器时强烈推荐）
npm run report                     # 打开 HTML 报告
```

> Playwright 会按 `playwright.config.ts` 的 `webServer` 配置**自动拉起**
> 后端（uvicorn :8000）与前端代理层（Express + Vite :5173）。
> 若本地已经启动过，会因 `reuseExistingServer` 直接复用，无需手动起服务。

## 关键设计

1. **E2E 专用数据库**：后端以 `DB_URL=sqlite+aiosqlite:///./e2e_test.db` 启动，
   与开发库 `dev.db` 完全隔离；`npm run reset-db` 可一键重置。
2. **关闭滑块验证**（`CAPTCHA_ENABLED=false`）：滑块依赖"类人拖动轨迹"
   （位置容差 + 耗时下限 + 轨迹形态三重判定），自动化脚本难以稳定通过。
   滑块本身由 `backend/tests/unit/test_captcha_unit.py` 与集成测试深入覆盖，
   E2E 关注业务链路，因此在此关闭。
3. **验证码自动回填**（`DEBUG=true`）：后端无 SMTP 时会在响应里回传 `debug_code`，
   前端 `doSendCode` 会自动填入输入框，E2E 因此无需真实邮箱。
4. **登录态预置**：发布/消息/管理等场景的被测对象不是注册流程，
   它们通过 `utils/auth-helpers.ts` 调 API 建号后把令牌注入 `localStorage`
   （键名 `cs_access_token` / `cs_admin_access_token` / `cs_admin_gateway_token`，
   与前端真实行为一致），又快又稳。注册流程本身由 `02-register.spec.ts` 走完整 UI 覆盖。
5. **串行执行**（`workers: 1`）：用例共享同一套服务与数据库，并行会互相干扰数据。

## 选择器维护提示

`pages/` 里的选择器取自前端页面的**真实文案**（placeholder、按钮文字、role）。
若某次前端改版后用例开始报"找不到元素"，优先用有界面模式定位：

```bash
npm run test:headed
```

## 已知限制

- 举报工单的**处置动作**未做 UI 验证：后端 `/api/reports/{id}/handle` 目前
  存在管理员身份校验缺陷（已由后端集成测试固化为 xfail），
  待修复后再补充处置场景。详见 `../docs/TESTING.md` §8.2。
- 消息场景只验证**单端连接与收发**；双端实时互收的广播链路由后端
  `tests/integration/test_messaging/` 覆盖（双连接 E2E 容易因子连接残留消息而挂死）。
