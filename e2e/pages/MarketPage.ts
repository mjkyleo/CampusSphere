import { expect } from '@playwright/test';
import { BasePage } from './BasePage.ts';

/**
 * 二手市场页面对象：发布 → 列表可见 → 详情 → 发起议价会话。
 *
 * 对应核心用户旅程「二手发布」与「创建议价会话」。
 */
export class MarketPage extends BasePage {
  // ---- 发布表单（frontend/pages/MarketPublish.tsx）----
  get publishEntry() {
    return this.page.getByText('发布闲置宝贝');
  }

  get titleInput() {
    return this.page.getByPlaceholder(/例如: 99新 iPad/);
  }

  get priceInput() {
    return this.page.getByPlaceholder('0.00');
  }

  get descriptionInput() {
    return this.page.getByPlaceholder(/详细描述物品的规格/);
  }

  async openPublish(): Promise<void> {
    await this.goto('/market/publish');
    await expect(this.titleInput).toBeVisible();
  }

  /** 填写并发布一件二手物品，返回标题（用于后续在列表中查找）。 */
  async publish(title: string, priceYuan: string, description: string): Promise<void> {
    await this.titleInput.fill(title);
    await this.priceInput.fill(priceYuan);
    await this.descriptionInput.fill(description);
    await this.page.getByRole('button', { name: /发布|立即发布/ }).last().click();
  }

  // ---- 列表 ----
  async openList(): Promise<void> {
    await this.goto('/market');
  }

  /** 列表中应能搜到指定标题的物品。 */
  async expectItemVisible(title: string): Promise<void> {
    await expect(this.page.getByText(title).first()).toBeVisible();
  }

  /** 打开指定标题物品的详情页。 */
  async openItemDetail(title: string): Promise<void> {
    await this.page.getByText(title).first().click();
  }

  // ---- 详情与议价 ----
  /** 买家视角的「发起交易与在线咨询」按钮。 */
  get startTradeButton() {
    return this.page.getByRole('button', { name: /发起交易与在线咨询|正在建立交易会话/ });
  }

  /** 发起议价：应跳转到消息中心或提示会话已建立。 */
  async startTrade(): Promise<void> {
    await this.startTradeButton.click();
  }
}
