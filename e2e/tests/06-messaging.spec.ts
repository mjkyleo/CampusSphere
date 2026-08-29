import { expect, test } from '@playwright/test';
import { MessagePage } from '../pages/MessagePage.ts';
import { createItem, createUser, injectUserSession } from '../utils/auth-helpers.ts';

/**
 * 场景 6：即时消息（WebSocket）。
 *
 * 需求对应：「WebSocket 连接 → 发送消息 → 对方在线时实时接收」。
 *
 * 说明：完整的"双浏览器上下文实时互收"需要两个独立页面上下文且都保持
 * WS 长连接，在此仅验证**单端可连接、可发送、消息可见**这一主链路；
 * 广播与落库由后端集成测试
 * （tests/integration/test_messaging/test_ws_messaging.py）深入覆盖。
 */
test.describe('即时消息', () => {
  test('建立议价会话后可进入消息中心并发送消息', async ({ page }) => {
    const seller = await createUser();
    const buyer = await createUser();
    const itemId = await createItem(seller, `E2E消息物品_${Date.now().toString(36)}`);

    // 买家先发起议价，生成会话
    await injectUserSession(page, buyer);
    await page.goto(`/market/${itemId}`);
    await page.getByRole('button', { name: /发起交易与在线咨询/ }).click();
    await expect(page).toHaveURL(/\/messages/, { timeout: 20_000 });

    // 进入会话并发送消息
    const messages = new MessagePage(page);
    await messages.openFirstConversation();
    const content = `你好，这本书还在吗？-${Date.now().toString(36)}`;
    await messages.send(content);

    await messages.expectMessage(content);
  });

  test('未登录访问消息中心被重定向到登录页', async ({ page }) => {
    await page.goto('/messages');
    await expect(page).toHaveURL(/\/login/);
  });

  test('无会话时消息中心展示空态而非报错', async ({ page }) => {
    const user = await createUser();
    await injectUserSession(page, user);

    const messages = new MessagePage(page);
    await messages.open();
    await expect(messages.conversationListHeader).toBeVisible();
  });
});
