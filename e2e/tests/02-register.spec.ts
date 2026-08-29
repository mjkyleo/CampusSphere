import { expect, test } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage.ts';
import { TEST_PASSWORD, uniqueEmail } from '../utils/test-data.ts';

/**
 * 场景 2：用户注册全链路（**走真实 UI**）。
 *
 * 需求对应：滑块验证 → 获取验证码 → 提交注册 → 自动登录并跳转。
 *
 * 环境说明：E2E 环境下 CAPTCHA_ENABLED=false（自动化难以模拟类人拖动轨迹，
 * 滑块能力由 tests/unit/test_captcha_unit.py 与集成测试覆盖），
 * 因此这里不出现滑块弹层；后端 DEBUG=true 时验证码会随响应返回并由前端自动回填。
 */
test.describe('邮箱注册', () => {
  test('填表 → 获取验证码 → 注册成功并自动登录跳转首页', async ({ page }) => {
    const email = uniqueEmail('reg');
    const loginPage = new LoginPage(page);

    await loginPage.open();
    await loginPage.registerByEmail(email, TEST_PASSWORD, 'E2E新生');

    // 注册即登录：应跳转到首页
    await expect(page).toHaveURL(/\/$/);
    // 登录态：localStorage 中已存在访问令牌
    const token = await loginPage.getStoredToken();
    expect(token, '注册后应已签发访问令牌').toBeTruthy();
  });

  test('重复注册同一邮箱会被拒绝并给出提示', async ({ page }) => {
    const email = uniqueEmail('dup');
    const loginPage = new LoginPage(page);

    // 第一次注册
    await loginPage.open();
    await loginPage.registerByEmail(email, TEST_PASSWORD, '首次注册');
    await expect(page).toHaveURL(/\/$/);

    // 登出后再用同一邮箱注册
    await page.evaluate(() => window.localStorage.clear());
    await loginPage.open();
    await loginPage.switchToEmailRegister();
    await loginPage.emailInput.fill(email);
    await loginPage.registerPasswordInput.fill(TEST_PASSWORD);
    await loginPage.sendCodeButton.click();
    await expect(loginPage.emailCodeInput).not.toHaveValue('', { timeout: 15_000 });
    await loginPage.registerSubmit.click();

    // 应停留在登录页并提示邮箱已注册
    await expect(page.getByText(/已注册|已存在/).first()).toBeVisible({ timeout: 15_000 });
  });
});
