import { expect, test } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage.ts';
import { HomePage } from '../pages/HomePage.ts';
import { TEST_PASSWORD } from '../utils/test-data.ts';
import { createUser, injectUserSession } from '../utils/auth-helpers.ts';

/**
 * 场景 3：登录鉴权与会话保持。
 *
 * 需求对应：
 * - 正确账号密码登录成功；
 * - 错误密码返回失败提示；
 * - 会话保持（刷新页面 / 后续请求携带令牌仍可访问需登录接口）。
 */
test.describe('登录鉴权', () => {
  test('正确账号密码可登录并跳转首页', async ({ page }) => {
    const user = await createUser();
    const loginPage = new LoginPage(page);

    await loginPage.open();
    await loginPage.login(user.username, user.password);

    await expect(page).toHaveURL(/\/$/);
    expect(await loginPage.getStoredToken()).toBeTruthy();
  });

  test('错误密码登录失败并提示', async ({ page }) => {
    const user = await createUser();
    const loginPage = new LoginPage(page);

    await loginPage.open();
    await loginPage.login(user.username, 'WrongPassword!');

    // 停留在登录页，并给出错误反馈（toast 或内联提示）
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText(/错误|失败|不正确/).first()).toBeVisible({ timeout: 15_000 });
  });

  test('刷新页面后登录态保持（会话持久化）', async ({ page }) => {
    const user = await createUser();
    await injectUserSession(page, user);

    const home = new HomePage(page);
    await home.open();
    // 刷新：令牌来自 localStorage，应仍处于登录态
    await page.reload();
    await home.expectLoaded();

    const token = await home.getStoredToken();
    expect(token).toBe(user.accessToken);
  });

  test('登录后访问个人中心等需登录页面不被拦截', async ({ page }) => {
    const user = await createUser();
    await injectUserSession(page, user);

    await page.goto('/profile');
    await expect(page).toHaveURL(/\/profile/);
    // 未登录时会被重定向到 /login，此处应停留在个人中心
    await expect(page.getByText(/登录/).first()).not.toHaveCount(0); // 页面含"登录"字样亦可，重点是 URL 未被改
  });
});
