import type { Locator, Page } from '@playwright/test';
import { expect } from '@playwright/test';

/**
 * 页面对象基类：封装所有页面共用的导航与断言能力。
 *
 * 页面对象模式（Page Object Model）的价值：
 * 页面结构变化时**只改 pages/ 下的一个类**，测试脚本（tests/）无需改动。
 */
export abstract class BasePage {
  constructor(protected readonly page: Page) {}

  /** 访问站内路径（相对 baseURL）。 */
  async goto(path = '/'): Promise<void> {
    await this.page.goto(path);
  }

  /** 等待跳转到指定路径（用正则匹配，忽略查询串差异）。 */
  async expectUrl(pathPattern: RegExp | string): Promise<void> {
    await expect(this.page).toHaveURL(pathPattern);
  }

  /** 按可见文本断言元素存在。 */
  expectText(text: string | RegExp): Locator {
    return this.page.getByText(text);
  }

  /** 等待一段提示文案出现（登录/发布等操作的 toast 反馈）。 */
  async waitForToast(textPattern: string | RegExp): Promise<void> {
    await expect(this.page.getByText(textPattern).first()).toBeVisible();
  }

  /** 当前页面是否已经登录（依据导航栏是否出现"退出/个人中心"等登录态入口）。 */
  async isLoggedIn(): Promise<boolean> {
    const logout = this.page.getByText(/退出登录|退出/).first();
    return (await logout.count()) > 0;
  }

  /** 读取 localStorage 中的令牌（用于校验"会话保持"）。 */
  async getStoredToken(): Promise<string | null> {
    return this.page.evaluate(() => {
      for (const key of Object.keys(window.localStorage)) {
        const value = window.localStorage.getItem(key) || '';
        if (key.toLowerCase().includes('token') && value.length > 20) {
          return value;
        }
      }
      return null;
    });
  }
}
