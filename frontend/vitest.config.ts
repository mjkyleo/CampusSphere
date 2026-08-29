import path from 'path';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

/**
 * Vitest 配置（与生产构建配置 vite.config.ts 分离，避免测试设置影响打包产物）。
 *
 * 工具选型说明
 * ------------
 * 需求文档建议 Jest + React Testing Library，但本项目是 **Vite + ESM + TSX**，
 * 用 Jest 需要额外接 ts-jest/babel 处理 ESM 与 JSX，配置脆弱且与 Vite 的
 * alias/插件链不一致（`@/` 别名要配两遍）。
 * 因此采用 **Vitest** —— API 与 Jest 高度兼容（describe/it/expect/vi.fn/
 * beforeEach 完全一致），但复用 Vite 的解析与插件，零额外转译配置。
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
  test: {
    // 组件测试需要 DOM
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./__tests__/setup.ts'],
    include: ['__tests__/**/*.{test,spec}.{ts,tsx}'],
    // 组件测试不应受真实定时/网络影响
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['components/**/*.tsx', 'pages/**/*.tsx', 'services/**/*.ts', 'hooks/**/*.ts', 'context/**/*.tsx'],
      exclude: [
        '**/*.{test,spec}.{ts,tsx}',
        '**/__tests__/**',
        'server.ts',
        'index.tsx',
        'vite.config.ts',
        'vitest.config.ts',
      ],
    },
  },
});
