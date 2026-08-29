import { expect, test } from '@playwright/test';
import { MarketPage } from '../pages/MarketPage.ts';
import { createItem, createUser, injectUserSession } from '../utils/auth-helpers.ts';

/**
 * 场景 5：二手发布 → 列表可见 → 详情可查看 → 创建议价会话。
 *
 * 需求对应（核心业务功能之一）：
 * 「填写表单 → 提交 → 列表可见 → 详情可查看 → 创建议价会话」。
 */
test.describe('二手发布与议价', () => {
  test('登录后发布物品，可在列表与详情中看到', async ({ page }) => {
    const seller = await createUser();
    await injectUserSession(page, seller);

    const market = new MarketPage(page);
    const title = `E2E闲置物品_${Date.now().toString(36)}`;

    await market.openPublish();
    await market.publish(title, '128.50', 'E2E 自动化发布的测试物品，九成新，校内面交。');

    // 发布成功后应能看到该物品（列表或详情）
    await expect(page.getByText(title).first()).toBeVisible({ timeout: 20_000 });
  });

  test('买家可在商品详情发起议价，生成会话', async ({ page }) => {
    const seller = await createUser();
    const buyer = await createUser();
    const itemTitle = `E2E议价物品_${Date.now().toString(36)}`;
    const itemId = await createItem(seller, itemTitle);

    // 以买家身份打开商品详情
    await injectUserSession(page, buyer);
    await page.goto(`/market/${itemId}`);

    const market = new MarketPage(page);
    await expect(market.startTradeButton).toBeVisible();
    await market.startTrade();

    // 发起后应进入消息会话（跳转 /messages）或给出成功反馈
    await expect(page).toHaveURL(/\/messages/, { timeout: 20_000 });
  });

  test('卖家在自己商品详情看不到"发起交易"按钮', async ({ page }) => {
    const seller = await createUser();
    const itemId = await createItem(seller, `E2E自持物品_${Date.now().toString(36)}`);

    await injectUserSession(page, seller);
    await page.goto(`/market/${itemId}`);

    const market = new MarketPage(page);
    // 卖家视角显示的是下架/售出等操作，而非发起交易
    await expect(market.startTradeButton).toHaveCount(0);
  });
});
