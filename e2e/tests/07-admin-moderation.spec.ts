import { expect, test } from '@playwright/test';
import { AdminPage } from '../pages/AdminPage.ts';
import { injectAdminSession } from '../utils/auth-helpers.ts';

/**
 * 场景 7：管理后台内容治理。
 *
 * 需求对应：「管理员登录 → 查看举报列表 → 处理工单」。
 *
 * 已知限制（由后端集成测试固化为 xfail，见 docs/TESTING.md）：
 * 举报处置端点 ``/api/reports/{id}/handle`` 目前未校验管理员身份，
 * 因此本场景只覆盖到"管理员登录 + 举报列表可查看"，
 * 处置动作的 UI 验证待该缺陷修复后补充。
 */
test.describe('管理后台', () => {
  test('管理员可用网关密钥登录并进入后台', async ({ page }) => {
    const admin = new AdminPage(page);
    await admin.login();
    await expect(page).toHaveURL(/\/admin/);
  });

  test('管理员可查看举报工单面板', async ({ page }) => {
    await injectAdminSession(page);
    const admin = new AdminPage(page);
    await page.goto('/admin');

    await admin.openReportsTab();
    await admin.expectReportsVisible();
  });

  test('未登录访问管理后台被重定向到登录页', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/login/);
  });
});
