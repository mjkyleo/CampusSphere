import { expect } from '@playwright/test';
import { BasePage } from './BasePage.ts';

/**
 * 首页页面对象：对应需求「主页访问：前端渲染正常，公共列表能正常加载」。
 */
export class HomePage extends BasePage {
  /** 首页主标题（见 HomePage.tsx 的 h1）。 */
  get heroTitle() {
    return this.page.locator('h1').first();
  }

  /** 快捷入口卡片（食堂美食 / 二手市场 等）。 */
  entry(name: string | RegExp) {
    return this.page.getByText(name).first();
  }

  async open(): Promise<void> {
    await this.goto('/');
    await this.expectLoaded();
  }

  /** 首页渲染完成：主标题可见。 */
  async expectLoaded(): Promise<void> {
    await expect(this.heroTitle).toBeVisible();
  }

  /** 公共列表区块可见（最新二手闲置）。 */
  async expectPublicSections(): Promise<void> {
    await expect(this.page.getByText('最新二手闲置')).toBeVisible();
  }

  /** 点击顶部导航进入二手市场列表。 */
  async gotoMarket(): Promise<void> {
    await this.page.goto('/market');
  }
}
