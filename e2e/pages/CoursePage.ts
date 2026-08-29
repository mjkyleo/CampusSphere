import { expect } from '@playwright/test';
import { BasePage } from './BasePage.ts';

/**
 * 课程页面对象：搜索课程 → 查看详情 → 发表评价。
 */
export class CoursePage extends BasePage {
  get searchInput() {
    return this.page.getByPlaceholder(/课程|搜索/).first();
  }

  async open(): Promise<void> {
    await this.goto('/courses');
  }

  /** 按关键词搜索课程。 */
  async search(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await this.searchInput.press('Enter');
  }

  /** 打开搜索结果中的第一条课程。 */
  async openFirstResult(): Promise<void> {
    await this.page.locator('a, button').filter({ hasText: /详情|查看/ }).first().click();
  }

  /** 发表一条课程评价（星级 + 内容）。 */
  async addReview(content: string): Promise<void> {
    const contentBox = this.page.getByPlaceholder(/评价|说点什么|感受/).first();
    await contentBox.fill(content);
    await this.page.getByRole('button', { name: /提交|发表|发布/ }).last().click();
  }

  /** 断言评价内容已出现在详情列表中。 */
  async expectReview(content: string): Promise<void> {
    await expect(this.page.getByText(content).first()).toBeVisible();
  }

  /** 断言搜索无结果时的空态提示。 */
  async expectEmptyState(): Promise<void> {
    await expect(this.page.getByText(/暂无|没有找到|无结果/).first()).toBeVisible();
  }
}
