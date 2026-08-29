/**
 * E2E 测试数据与环境常量。
 *
 * 数据策略
 * --------
 * E2E 需要"动态创建并清理"。这里采用**环境级隔离**而非逐用例清理：
 * - 后端在 E2E 中指向独立的 ``e2e_test.db``（见 playwright.config.ts）；
 * - 每次跑之前可用 ``npm run reset-db`` 删除该文件，后端启动时重建表并重新播种管理员。
 *
 * 相比"每个用例跑完再调接口删数据"，这样做的好处是：
 * 用例失败时也不会残留脏数据影响下一次运行，且清理成本为零。
 */

/** 允许的注册邮箱域名，需与 config/school.yaml 的 auth.email_register.domains 一致。 */
export const ALLOWED_EMAIL_DOMAIN = 'example.edu.cn';

/** 管理员登录所需的网关密钥（后端 ADMIN_GATEWAY_KEY，E2E 环境由 playwright.config.ts 注入）。 */
export const ADMIN_GATEWAY_KEY = process.env.ADMIN_GATEWAY_KEY || 'e2e-gateway-key';

/** 引导管理员账号（后端 school.yaml / 环境变量，见 config.admin.bootstrap）。 */
export const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'siteadmin';
export const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'E2EAdminPass123456';

/** 生成全局唯一的邮箱，避免重复注册冲突（可重复运行）。 */
export function uniqueEmail(prefix = 'e2e'): string {
  const stamp = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}_${stamp}_${rand}@${ALLOWED_EMAIL_DOMAIN}`;
}

/** 生成全局唯一的用户名。 */
export function uniqueName(prefix = 'e2e'): string {
  const stamp = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}_${stamp}_${rand}`;
}

/** 测试用统一密码（满足后端 ≥6 位要求）。 */
export const TEST_PASSWORD = 'E2eTest@12345';
