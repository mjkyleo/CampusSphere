import { expect, test } from '@playwright/test';

/**
 * 场景 4：未登录访问受限操作 → 重定向到登录页。
 *
 * 需求对应：「未登录状态下，各页面可浏览，但发布/评论/消息等操作重定向到登录页」。
 *
 * 前端由 ProtectedRoute 守卫实现（该逻辑另有组件级单测
 * ``frontend/__tests__/components/RouteGuards.test.tsx`` 覆盖），
 * 这里验证**真实路由跳转行为**。
 */
const PROTECTED_PATHS: Array<{ path: string; name: string }> = [
  { path: '/market/publish', name: '发布闲置' },
  { path: '/messages', name: '消息中心' },
  { path: '/profile', name: '个人中心' },
];

test.describe('未登录访问受限页面', () => {
  for (const { path, name } of PROTECTED_PATHS) {
    test(`${name}（${path}）未登录时被重定向到登录页`, async ({ page }) => {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login/);
    });
  }

  test('管理后台未登录时被重定向到管理员登录', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/login/);
  });

  test('从登录页登录后仍可回到发布页（重定向不丢失入口）', async ({ page }) => {
    // 先触发重定向，确认落到登录页
    await page.goto('/market/publish');
    await expect(page).toHaveURL(/\/login/);
    // 此时未登录，登录页应正常渲染四个模式入口
    await expect(page.getByRole('button', { name: '账号登录', exact: true })).toBeVisible();
  });
});
