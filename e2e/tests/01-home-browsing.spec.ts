import { expect, test } from '@playwright/test';
import { HomePage } from '../pages/HomePage.ts';

/**
 * 场景 1：主页访问与公开内容浏览（**未登录**）。
 *
 * 需求对应：
 * - 前端渲染正常；
 * - 公共列表（二手、课程、食堂等）能正常加载；
 * - 未登录状态下各页面可浏览。
 */
test.describe('主页与公开内容浏览（未登录）', () => {
  test('首页正常渲染且展示公共区块', async ({ page }) => {
    const home = new HomePage(page);
    await home.open();
    await home.expectPublicSections();
    await expect(page).toHaveURL(/\/$/);
  });

  test('未登录可浏览二手市场公开列表', async ({ page }) => {
    const home = new HomePage(page);
    await home.gotoMarket();
    // 列表页应能加载（无数据也应展示空态而非报错页）
    await expect(page.getByText(/二手|闲置|市场/).first()).toBeVisible();
    await expect(page).toHaveURL(/\/market/);
  });

  test('未登录可浏览课程与食堂页面', async ({ page }) => {
    for (const [path, keyword] of [
      ['/courses', /课程/],
      ['/canteens', /食堂/],
    ] as const) {
      await page.goto(path);
      await expect(page.getByText(keyword).first()).toBeVisible();
    }
  });

  test('首页无未捕获的 JS 错误', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const home = new HomePage(page);
    await home.open();

    expect(errors, `首页存在未捕获错误: ${errors.join(' | ')}`).toHaveLength(0);
  });
});
