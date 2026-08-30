import path from 'path';
import { defineConfig, devices } from '@playwright/test';

/**
 * 端到端测试配置。
 *
 * 设计要点
 * --------
 * 1. **自动拉起整套服务**：Playwright 的 ``webServer`` 会先后启动
 *    后端（uvicorn :8000）与前端代理层（Express + Vite :5173），
 *    ``reuseExistingServer`` 让本地开发时复用已启动的服务（更快）。
 * 2. **E2E 专用数据库**：通过环境变量把后端指向 ``e2e_test.db``，
 *    绝不污染开发库 ``dev.db``；跑之前可用 ``npm run reset-db`` 重置。
 * 3. **关闭滑块验证**：滑块依赖"类人拖动轨迹"（耗时下限 + 轨迹形态 + 位置容差），
 *    自动化脚本难以稳定通过，属于**被单测/集成测试覆盖的独立能力**；
 *    E2E 关注业务链路，因此在此关闭（CAPTCHA_ENABLED=false）。
 * 4. **串行执行**：用例共享同一套服务与数据库，并行会互相干扰数据。
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';
const BACKEND_URL = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8000';
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: './tests',
  // 端到端用例共享服务与数据库，串行执行最稳
  fullyParallel: false,
  workers: 1,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  timeout: 90_000,
  expect: { timeout: 12_000 },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],

  use: {
    baseURL: BASE_URL,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    // 失败时保留现场，便于定位
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: path.resolve(__dirname, '../backend'),
      url: `${BACKEND_URL}/api/health`,
      reuseExistingServer: !isCI,
      timeout: 180_000,
      env: {
        // E2E 专用库：与开发库隔离
        DB_URL: 'sqlite+aiosqlite:///./e2e_test.db',
        // 关闭滑块（自动化难以模拟类人轨迹），开启 debug 以便前端自动回填验证码
        CAPTCHA_ENABLED: 'false',
        DEBUG: 'true',
        // 关闭热点缓存，保证列表断言读到最新数据
        CACHE_ENABLED: 'false',
        // 置空 SMTP：E2E 不应真的发信。留空后 send_code 跳过派发，
        // 验证码改为经 DEBUG=true 从响应回传，由前端自动回填。
        // 若不置空，会继承 backend/.env 的真实 SMTP 并向队列（或真实邮箱）投递。
        SMTP_HOST: '',
        // 允许从响应读取验证码（注册场景需要）。
        // 不用 DEBUG 代替：DEBUG=true 会关闭管理员网关校验，
        // 导致 07-admin 里"未带网关令牌应被拒"的用例失效。
        EXPOSE_VERIFICATION_CODE: 'true',
        // 放宽限流：认证端点默认 10 次/分钟（防爆破），但 E2E 会批量
        // 创建用户/登录，同一分钟内必然超限（42900）导致用例互相干扰。
        // 限流能力本身由集成测试覆盖，这里只需让业务链路不被节流。
        RATE_LIMIT_PER_MINUTE: '10000',
        AUTH_RATE_LIMIT_PER_MINUTE: '10000',
        // 验证码发送频率（同一 target 每分钟 1 次）会阻断"重复注册同一邮箱"等
        // 需要为同一邮箱再次取码的用例，同样放宽。
        CODE_SEND_LIMIT_PER_MINUTE: '100',
        // 管理端：网关密钥 + 引导管理员（管理后台场景需要）
        // 注意密码需 ≥16 位，否则生产校验会拒绝（config.admin_bootstrap_min_length）
        ADMIN_GATEWAY_KEY: process.env.ADMIN_GATEWAY_KEY || 'e2e-gateway-key',
        ADMIN_BOOTSTRAP_PASSWORD: process.env.ADMIN_PASSWORD || 'E2EAdminPass123456',
      },
    },
    {
      command: 'npm run dev',
      cwd: path.resolve(__dirname, '../frontend'),
      url: BASE_URL,
      reuseExistingServer: !isCI,
      timeout: 180_000,
    },
  ],
});
