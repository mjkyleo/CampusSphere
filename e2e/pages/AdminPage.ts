import { expect } from '@playwright/test';
import { BasePage } from './BasePage.ts';
import { ADMIN_GATEWAY_KEY, ADMIN_PASSWORD, ADMIN_USERNAME } from '../utils/test-data.ts';

/**
 * 管理后台页面对象：管理员登录 → 查看举报列表 → 处理工单。
 *
 * 管理端受**网关密钥**保护（``/login?admin=1`` 打开管理登录表单，
 * 需要填写网关密钥 + 管理员账号 + 密码），
 * 密钥由 playwright.config.ts 通过 ADMIN_GATEWAY_KEY 注入后端。
 */
export class AdminPage extends BasePage {
  get gatewayKeyInput() {
    return this.page.getByPlaceholder(/网关/);
  }

  get adminUsernameInput() {
    return this.page.getByPlaceholder('管理员账号');
  }

  get adminPasswordInput() {
    return this.page.getByPlaceholder('管理员密码');
  }

  /** 以引导管理员身份登录管理后台。 */
  async login(): Promise<void> {
    await this.goto('/login?admin=1');
    await expect(this.adminUsernameInput).toBeVisible();

    await this.gatewayKeyInput.fill(ADMIN_GATEWAY_KEY);
    await this.adminUsernameInput.fill(ADMIN_USERNAME);
    await this.adminPasswordInput.fill(ADMIN_PASSWORD);
    await this.page.getByRole('button', { name: /登录|进入/ }).last().click();

    await this.expectUrl(/\/admin/);
  }

  /** 打开「举报/工单」相关面板。 */
  async openReportsTab(): Promise<void> {
    await this.page.getByText(/举报|工单/).first().click();
  }

  /** 举报列表（可能为空）区域可见。 */
  async expectReportsVisible(): Promise<void> {
    await expect(this.page.getByText(/举报|工单/).first()).toBeVisible();
  }
}
