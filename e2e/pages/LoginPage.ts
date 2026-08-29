import { expect } from '@playwright/test';
import { BasePage } from './BasePage.ts';

/**
 * 登录 / 注册页页面对象。
 *
 * 选择器全部来自 ``frontend/pages/LoginPage.tsx`` 的真实文案：
 * 四个模式 Tab（账号登录 / 短信登录 / 邮箱注册 / 新户注册），
 * 各 Tab 下的表单使用 placeholder 定位，稳定性优于 class 选择器。
 */
export class LoginPage extends BasePage {
  // ---- 模式切换 ----
  private tab(name: '账号登录' | '短信登录' | '邮箱注册' | '新户注册') {
    return this.page.getByRole('button', { name, exact: true });
  }

  async open(): Promise<void> {
    await this.goto('/login');
    await expect(this.tab('账号登录')).toBeVisible();
  }

  async switchToPasswordLogin(): Promise<void> {
    await this.tab('账号登录').click();
  }

  async switchToEmailRegister(): Promise<void> {
    await this.tab('邮箱注册').click();
  }

  // ---- 账号密码登录 ----
  get accountInput() {
    return this.page.getByPlaceholder('用户名 / 邮箱 / 手机号');
  }

  get passwordInput() {
    return this.page.getByPlaceholder('请输入登录密码');
  }

  get loginSubmit() {
    return this.page.getByRole('button', { name: /立即登录系统/ });
  }

  /** 用账号（用户名/邮箱/手机号）+ 密码登录。 */
  async login(account: string, password: string): Promise<void> {
    await this.switchToPasswordLogin();
    await this.accountInput.fill(account);
    await this.passwordInput.fill(password);
    await this.loginSubmit.click();
  }

  // ---- 邮箱验证码注册 ----
  get emailInput() {
    return this.page.getByPlaceholder('student@example.edu.cn');
  }

  get registerPasswordInput() {
    return this.page.getByPlaceholder('不少于6位');
  }

  get nicknameInput() {
    return this.page.getByPlaceholder('例如: 阳光学长');
  }

  get emailCodeInput() {
    return this.page.getByPlaceholder('6位邮件验证码');
  }

  get sendCodeButton() {
    return this.page.getByRole('button', { name: /获取邮箱验证码|后重发/ });
  }

  get registerSubmit() {
    return this.page.getByRole('button', { name: /完成邮箱认证并进入/ });
  }

  /** 请求邮箱验证码（debug 模式下前端会自动回填，见 doSendCode）。 */
  async requestEmailCode(email: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.sendCodeButton.click();
  }

  /**
   * 完整邮箱注册：填表 → 获取验证码 → 等待自动回填 → 提交。
   *
   * 返回注册时使用的邮箱，便于后续用例复用同一账号登录。
   */
  async registerByEmail(
    email: string,
    password: string,
    nickname = 'E2E同学',
  ): Promise<void> {
    await this.switchToEmailRegister();
    await this.emailInput.fill(email);
    await this.registerPasswordInput.fill(password);
    await this.nicknameInput.fill(nickname);

    await this.sendCodeButton.click();
    // 测试模式：验证码随响应返回并自动填入输入框
    await expect(this.emailCodeInput).not.toHaveValue('', { timeout: 15_000 });

    await this.registerSubmit.click();
  }
}
