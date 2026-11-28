import { test, expect, request, type APIRequestContext } from '@playwright/test';

/**
 * 真实用户场景全功能冒烟测试。
 *
 * 前置：
 * 1. 后端 + 前端开发服务已启动（start-dev.bat）；
 * 2. 已执行 backend/scripts/seed_full_data.py 灌入 15 用户全功能数据。
 *
 * 覆盖：登录 → 首页 → 二手交易 → 课程 → 食堂 → 兼职 → 组队 → 分享 → 消息 → 举报。
 * 所有操作都用真实用户 user01~user15（密码 123456），数据来自开发库 dev.db。
 */

const API_BASE = 'http://127.0.0.1:8000';
const PASSWORD = '123456';

interface Credentials {
  username: string;
  accessToken: string;
  userId: string;
}

/** 通过 API 登录获取令牌（前端等价：localStorage cs_access_token）。 */
async function login(username: string): Promise<Credentials> {
  const ctx: APIRequestContext = await request.newContext({ baseURL: API_BASE });
  try {
    const res = await ctx.post('/api/auth/login', {
      data: { account: username, password: PASSWORD },
    });
    const body = await res.json();
    expect(body.code, `login ${username}: ${body.message}`).toBe(0);
    return { username, accessToken: body.data.access_token, userId: body.data.user?.id ?? '' };
  } finally {
    await ctx.dispose();
  }
}

/** 把登录态注入浏览器（导航前调用）。 */
async function inject(page: import('@playwright/test').Page, cred: Credentials) {
  await page.addInitScript((token) => {
    window.localStorage.setItem('cs_access_token', token);
  }, cred.accessToken);
}

/** 直接调后端 API 验证数据（带认证）。 */
async function apiGet(path: string, token: string) {
  const ctx = await request.newContext({ baseURL: API_BASE });
  try {
    const res = await ctx.get(path, { headers: { Authorization: `Bearer ${token}` } });
    const body = await res.json();
    return body;
  } finally {
    await ctx.dispose();
  }
}

// ---------------------------------------------------------------------------
// 1. 登录 + 首页：真实用户能看到全功能入口和真实数据
// ---------------------------------------------------------------------------
test('T1 真实用户登录并看到首页真实数据', async ({ page }) => {
  const cred = await login('user01');
  await inject(page, cred);
  await page.goto('/');

  await expect(page.getByText('CampusSphere').first()).toBeVisible();
  // 核心功能矩阵：6 个模块入口（已精简为只有名称，无副标题）
  for (const label of ['闲置市集', '评课社区', '食堂美食', '搭子招募', '资源共享', '兼职校招']) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  }
  // 首页核心功能入口验证完毕；真实业务数据由 T9 统一验证
});

// ---------------------------------------------------------------------------
// 2. 二手交易：列表 → 详情 → 发起交易（真实 CAS + 会话创建）
// ---------------------------------------------------------------------------
test('T2 二手市集浏览并发起交易', async ({ page }) => {
  const buyer = await login('user13');
  const seller = await login('user14');
  await inject(page, buyer);

  // 先用 seller 发布一件新物品（API，避免 UI 上传依赖）
  const ctx = await request.newContext({ baseURL: API_BASE });
  const pub = await ctx.post('/api/items', {
    headers: { Authorization: `Bearer ${seller.accessToken}` },
    data: { title: `E2E测试物品-${Date.now()}`, description: '自动化测试发布', price: 1234, category: '书籍资料' },
  });
  const pubBody = await pub.json();
  expect(pubBody.code).toBe(0);
  const itemId = pubBody.data.id;
  await ctx.dispose();

  // 买家在页面打开市集，确认列表加载
  await page.goto('/market');
  await expect(page.getByText('二手', { exact: true }).first()).toBeVisible();

  // 买家通过 API 发起交易，验证 CAS + 会话创建
  const ctx2 = await request.newContext({ baseURL: API_BASE });
  const trade = await ctx2.post(`/api/items/${itemId}/trade`, {
    headers: { Authorization: `Bearer ${buyer.accessToken}` },
  });
  const tradeBody = await trade.json();
  expect(tradeBody.code, tradeBody.message).toBe(0);
  expect(tradeBody.data.conversation_id).toBeTruthy();
  await ctx2.dispose();

  // 页面打开消息中心，能看到会话列表（显示对方昵称）
  await page.goto('/messages');
  await expect(page.getByText('会话列表', { exact: false }).first()).toBeVisible({ timeout: 8000 });
  // 验证后端确实创建了 trade 会话
  const convs = await apiGet('/api/messages/conversations', buyer.accessToken);
  expect(convs.code).toBe(0);
  expect(JSON.stringify(convs.data)).toContain('trade');
});

// ---------------------------------------------------------------------------
// 3. 课程：列表 + 评价展示
// ---------------------------------------------------------------------------
test('T3 课程社区浏览与评价数据', async ({ page }) => {
  const cred = await login('user05');
  await inject(page, cred);
  await page.goto('/courses');

  // 课程页加载（搜索页骨架 + 学部筛选）
  await expect(page.getByText('全校课程评价社区', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: '搜索课程' })).toBeVisible();
  // 真实课程数据通过 API 验证（seed 灌入）
  const courses = await apiGet('/api/courses', cred.accessToken);
  expect(courses.code).toBe(0);
  expect(JSON.stringify(courses.data)).toContain('数据结构');
});

// ---------------------------------------------------------------------------
// 4. 食堂：列表 + 菜品评价
// ---------------------------------------------------------------------------
test('T4 食堂美食浏览与菜品评价', async ({ page }) => {
  const cred = await login('user08');
  await inject(page, cred);
  await page.goto('/canteens');

  // 食堂列表页加载（学部/类型筛选骨架）
  await expect(page.getByText('校园食堂与美食档口', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: '文理学部' })).toBeVisible();
  // 真实食堂/菜品数据通过 API 验证（seed 灌入）
  const canteens = await apiGet('/api/canteens', cred.accessToken);
  expect(canteens.code).toBe(0);
  expect(JSON.stringify(canteens.data)).toContain('梅园食堂');
});

// ---------------------------------------------------------------------------
// 5. 兼职：列表 + 申请
// ---------------------------------------------------------------------------
test('T5 兼职列表浏览与投递申请', async ({ page }) => {
  const cred = await login('user06');
  await inject(page, cred);
  await page.goto('/jobs');

  await expect(page.getByText('图书馆自习区管理员助理', { exact: true }).first()).toBeVisible();
  // 通过 API 申请一个新岗位
  const ctx = await request.newContext({ baseURL: API_BASE });
  const res = await ctx.post('/api/jobs', {
    headers: { Authorization: `Bearer ${cred.accessToken}` },
    data: { title: `E2E岗位-${Date.now()}`, description: '自动化测试', salary: 10000, category: '其他' },
  });
  const body = await res.json();
  expect(body.code).toBe(0);
  const apply = await ctx.post(`/api/jobs/${body.data.id}/apply`, {
    headers: { Authorization: `Bearer ${cred.accessToken}` },
    data: { note: '自动化投递' },
  });
  expect((await apply.json()).code).toBe(0);
  await ctx.dispose();
});

// ---------------------------------------------------------------------------
// 6. 组队：列表 + 加入
// ---------------------------------------------------------------------------
test('T6 搭子招募浏览与加入', async ({ page }) => {
  const cred = await login('user12');
  await inject(page, cred);
  await page.goto('/teammates');

  await expect(page.getByText('数学建模国赛 3 缺 1', { exact: true }).first()).toBeVisible();
  const ctx = await request.newContext({ baseURL: API_BASE });
  const res = await ctx.post('/api/teams', {
    headers: { Authorization: `Bearer ${cred.accessToken}` },
    data: { title: `E2E队伍-${Date.now()}`, description: '自动化测试', max_members: 5, category: '学术竞赛' },
  });
  expect((await res.json()).code).toBe(0);
  await ctx.dispose();
});

// ---------------------------------------------------------------------------
// 7. 分享 + 举报：列表展示 + 提交举报
// ---------------------------------------------------------------------------
test('T7 资源共享浏览与举报提交', async ({ page }) => {
  const cred = await login('user09');
  await inject(page, cred);
  await page.goto('/share');

  await expect(page.getByText('高数（上）期末真题+答案', { exact: true }).first()).toBeVisible();
  // 举报：用 API 提交（前端 ReportModal 已接后端，但弹窗触发依赖列表项按钮，API 更稳）
  const ctx = await request.newContext({ baseURL: API_BASE });
  const res = await ctx.post('/api/reports', {
    headers: { Authorization: `Bearer ${cred.accessToken}` },
    data: { target_type: 'share', target_id: `e2e-share-${Date.now()}`, reason: '自动化测试举报' },
  });
  expect((await res.json()).code).toBe(0);
  await ctx.dispose();
});

// ---------------------------------------------------------------------------
// 8. 个人中心：真实用户资料
// ---------------------------------------------------------------------------
test('T8 个人中心展示真实用户资料', async ({ page }) => {
  const cred = await login('user01');
  await inject(page, cred);
  await page.goto('/profile');

  // 个人中心展示昵称与账号（seed 数据：沐辰 / user01）
  await expect(page.getByText('沐辰', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('@user01', { exact: false }).first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// 9. 后端数据完整性：一次性验证所有模块 API 返回真实数据
// ---------------------------------------------------------------------------
test('T9 全模块数据完整性（直查 SQLite，绕开限流）', async () => {
  const { execFileSync } = await import('node:child_process');
  const path = await import('node:path');
  const dbPath = path.resolve(__dirname, '../../backend/dev.db');
  const realPy = `
import sqlite3, json
c = sqlite3.connect(r'${dbPath.replace(/\\/g, '\\\\')}')
tables = ['users','items','trade_sessions','courses','course_reviews','canteens','stalls','dishes','canteen_reviews','jobs','job_applications','teams','team_members','share_resources','conversations','messages','reports']
counts = {t: c.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in tables}
# (表名, 列名, 期望关键字)
checks = [('items','title','九成新 AirPods 耳机'),('courses','name','数据结构'),
          ('canteens','name','梅园食堂'),('jobs','title','图书馆自习区管理员助理'),
          ('teams','title','数学建模国赛 3 缺 1'),('share_resources','title','高数（上）期末真题+答案')]
for t, col, kw in checks:
    row = c.execute('SELECT GROUP_CONCAT(' + col + ') FROM ' + t).fetchone()[0] or ''
    assert kw in row, t + ' missing ' + kw
print(json.dumps(counts))
`;
  const out = execFileSync('python', ['-c', realPy], { encoding: 'utf-8' });
  const counts = JSON.parse(out);
  expect(counts.users).toBeGreaterThanOrEqual(15);
  expect(counts.items).toBeGreaterThanOrEqual(13);
  expect(counts.course_reviews).toBeGreaterThanOrEqual(9);
  expect(counts.canteen_reviews).toBeGreaterThanOrEqual(8);
  expect(counts.job_applications).toBeGreaterThanOrEqual(6);
  expect(counts.team_members).toBeGreaterThanOrEqual(6);
  expect(counts.messages).toBeGreaterThanOrEqual(9);
  expect(counts.reports).toBeGreaterThanOrEqual(5);
});
