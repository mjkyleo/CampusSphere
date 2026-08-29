/**
 * 组件测试全局初始化。
 *
 * - 引入 jest-dom 匹配器（toBeInTheDocument / toHaveAttribute ...）
 * - 每个用例后自动卸载 React 树，避免 DOM 残留导致用例互相污染
 * - 统一 mock 掉 jsdom 未实现的浏览器 API，防止组件里调用时报错
 */

import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
});

// jsdom 未实现 Pointer Capture：组件里用了可选调用（?.），
// 但显式提供空实现能让"是否调用"可被断言，也更贴近浏览器行为。
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = vi.fn();
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = vi.fn();
}

// jsdom 未实现 matchMedia（部分响应式组件会用到）
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}
