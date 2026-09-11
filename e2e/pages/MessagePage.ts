import { expect } from '@playwright/test';
import { BasePage } from './BasePage.ts';

/**
 * 消息中心页面对象（WebSocket 实时收发）。
 *
 * 注意：输入框的 placeholder 会随连接状态变化
 * （已连接：「输入消息，商讨物品细节或约定见面地点…」；
 *   连接中：「正在连接实时服务器…」），因此发送前需等待已连接态。
 */
export class MessagePage extends BasePage {
  async open(): Promise<void> {
    await this.goto('/messages');
  }

  /** 会话列表面板标题（含数量）。 */
  get conversationListHeader() {
    return this.page.getByText(/会话列表/);
  }

  /** 已连接状态下的消息输入框。 */
  get messageInput() {
    return this.page.getByPlaceholder(/输入消息，商讨物品细节/);
  }

  /** 等待 WebSocket 连接就绪（输入框变为可输入态）。 */
  async waitUntilConnected(): Promise<void> {
    await expect(this.messageInput).toBeVisible({ timeout: 20_000 });
    await expect(this.messageInput).toBeEditable();
  }

  /**
   * 打开会话列表中的第一个会话。
   *
   * 用 ``data-testid="conversation-item"`` 定位（见 MessageCenter.tsx）：
   * 列表项展示的是对方昵称与商品标题，随数据变化，不适合作为选择器；
   * 而"与 X 的会话"是**选中后**才在右侧面板出现的标题，
   * 用它去过滤左侧列表按钮必然匹配不到。
   */
  async openFirstConversation(): Promise<void> {
    await this.page.getByTestId('conversation-item').first().click();
    await this.waitUntilConnected();
  }

  /** 发送一条消息。 */
  async send(content: string): Promise<void> {
    await this.messageInput.fill(content);
    await this.page.locator('form').filter({ has: this.messageInput }).locator('button[type="submit"]').click();
  }

  /** 断言消息已出现在会话中（实时回显或落库后回读）。 */
  async expectMessage(content: string): Promise<void> {
    await expect(this.page.getByText(content).first()).toBeVisible({ timeout: 15_000 });
  }
}
