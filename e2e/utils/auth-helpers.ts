import { request, type APIRequestContext, type Page } from '@playwright/test';
import { ADMIN_GATEWAY_KEY, ADMIN_PASSWORD, ADMIN_USERNAME, ALLOWED_EMAIL_DOMAIN, TEST_PASSWORD } from './test-data.ts';

/**
 * E2E 登录态准备工具。
 *
 * 为什么用 API 预置而不是每次走 UI 注册？
 * ----------------------------------------
 * 发布物品、发消息、管理后台等场景的**被测对象不是注册流程**，
 * 若每个用例都从 UI 注册一遍，会让用例变慢且把无关环节的失败
 * （如验证码）引入到本场景。因此这些场景通过 API 建立登录态，
 * 再把令牌注入 localStorage —— 浏览器端与真实登录完全等价
 * （前端就是从 ``cs_access_token`` 读取令牌的）。
 *
 * 注册流程本身由 ``tests/02-register.spec.ts`` 走完整 UI 覆盖。
 */

const API_BASE = process.env.E2E_API_BASE || 'http://127.0.0.1:8000';

export interface TestUser {
  username: string;
  email: string;
  password: string;
  userId: string;
  accessToken: string;
  refreshToken: string;
}

function api(): Promise<APIRequestContext> {
  return request.newContext({ baseURL: API_BASE });
}

async function readData(response: { json(): Promise<any> }) {
  const body = await response.json();
  if (body?.code !== 0) {
    throw new Error(`接口返回业务错误: code=${body?.code} message=${body?.message}`);
  }
  return body.data;
}

/** 通过接口注册一个全新用户并登录，返回其凭据与令牌。 */
export async function createUser(username = `e2e_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`): Promise<TestUser> {
  const ctx = await api();
  try {
    const email = `${username}@${ALLOWED_EMAIL_DOMAIN}`;
    const regData = await readData(
      await ctx.post('/api/auth/register', { data: { username, password: TEST_PASSWORD } }),
    );
    const tokenData = await readData(
      await ctx.post('/api/auth/login', { data: { username, password: TEST_PASSWORD } }),
    );
    return {
      username,
      email,
      password: TEST_PASSWORD,
      userId: regData.id,
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
    };
  } finally {
    await ctx.dispose();
  }
}

/** 把普通用户登录态注入浏览器（需在页面导航前调用）。 */
export async function injectUserSession(page: Page, user: TestUser): Promise<void> {
  await page.addInitScript(
    ({ access, refresh }) => {
      window.localStorage.setItem('cs_access_token', access);
      window.localStorage.setItem('cs_refresh_token', refresh);
    },
    { access: user.accessToken, refresh: user.refreshToken },
  );
}

/**
 * 准备管理员登录态：先用网关密钥换取网关令牌，再登录管理后台，
 * 最后把三枚令牌注入 localStorage（与前端 adminLogin 行为一致）。
 */
export async function injectAdminSession(page: Page): Promise<void> {
  const ctx = await api();
  try {
    const discover = await readData(
      await ctx.post('/api/admin/discover', { data: { gateway_key: ADMIN_GATEWAY_KEY } }),
    );
    const tokens = await readData(
      await ctx.post('/api/admin/login', {
        data: { username: ADMIN_USERNAME, password: ADMIN_PASSWORD },
      }),
    );
    await page.addInitScript(
      ({ gateway, access, refresh }) => {
        window.localStorage.setItem('cs_admin_gateway_token', gateway);
        window.localStorage.setItem('cs_admin_access_token', access);
        window.localStorage.setItem('cs_admin_refresh_token', refresh);
      },
      {
        gateway: discover.gateway_token,
        access: tokens.access_token,
        refresh: tokens.refresh_token,
      },
    );
  } finally {
    await ctx.dispose();
  }
}

/** 直接调用后端接口发布一件二手物品（用于给"买家"场景准备数据）。 */
export async function createItem(user: TestUser, title: string, price = 8800): Promise<string> {
  const ctx = await api();
  try {
    const data = await readData(
      await ctx.post('/api/items', {
        data: { title, description: 'E2E 预置物品', price, category: '书籍资料', images: [] },
        headers: { Authorization: `Bearer ${user.accessToken}` },
      }),
    );
    return data.id as string;
  } finally {
    await ctx.dispose();
  }
}
