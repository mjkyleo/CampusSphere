import { defineConfig, devices } from '@playwright/test';

/**
 * 真实用户场景冒烟测试配置。
 * 与 playwright.config.ts 的区别：
 * - 复用已运行的开发服务（8000 + 5173），不拉起独立 E2E 服务；
 * - 直连开发库 dev.db，验证 seed_full_data.py 灌入的真实数据；
 * - 只跑 tests/real-user-*.spec.ts。
 */
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';

export default defineConfig({
  testDir: './tests',
  testMatch: /real-user-.*\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  outputDir: process.env.TEMP ? `${process.env.TEMP}/cs-e2e-dev` : '/tmp/cs-e2e-dev',
  use: {
    baseURL: BASE_URL,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
