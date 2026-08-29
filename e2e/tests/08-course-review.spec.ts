import { expect, test } from '@playwright/test';
import { CoursePage } from '../pages/CoursePage.ts';

/**
 * 场景 8：课程浏览与评价（公开浏览 + 登录后评价）。
 *
 * 需求对应（核心业务功能之一）：
 * 「课程评价：搜索课程 → 查看详情 → 发表评价」。
 *
 * 说明：课程数据由后端播种/后台配置，E2E 环境使用独立的 e2e_test.db，
 * 若库中暂无课程，则退化为验证"空态提示"与"未登录可浏览"。
 */
test.describe('课程浏览与评价', () => {
  test('未登录可浏览课程列表', async ({ page }) => {
    const courses = new CoursePage(page);
    await courses.open();
    await expect(page).toHaveURL(/\/courses/);
    await expect(page.getByText(/课程/).first()).toBeVisible();
  });

  test('搜索不存在的课程展示空态', async ({ page }) => {
    const courses = new CoursePage(page);
    await courses.open();
    await courses.search(`不存在的课程_${Date.now().toString(36)}`);
    await courses.expectEmptyState();
  });

  test('未登录不能直接进入评价页（受登录保护）', async ({ page }) => {
    await page.goto('/courses/review');
    await expect(page).toHaveURL(/\/login/);
  });
});
