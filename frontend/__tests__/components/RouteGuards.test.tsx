/**
 * 路由守卫测试：对应需求「未登录状态下各页面可浏览，
 * 但发布/评论/消息等操作重定向到登录页」。
 *
 * 这里直接对三个守卫组件做单元级验证（mock AuthContext），
 * 全链路跳转行为由 e2e/ 下的 Playwright 场景覆盖。
 */

import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ProtectedRoute } from '../../components/ProtectedRoute.tsx';
import { PublicOnlyRoute } from '../../components/PublicOnlyRoute.tsx';
import { AdminRoute } from '../../components/AdminRoute.tsx';
import { useAuth } from '../../context/AuthContext.tsx';

vi.mock('../../context/AuthContext.tsx', () => ({
  useAuth: vi.fn(),
}));

const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;

type AuthState = {
  isAuthenticated?: boolean;
  isAdminAuthenticated?: boolean;
  loading?: boolean;
  adminLoading?: boolean;
};

function setAuth(state: AuthState) {
  mockUseAuth.mockReturnValue({
    isAuthenticated: false,
    isAdminAuthenticated: false,
    loading: false,
    adminLoading: false,
    ...state,
  });
}

/** 在带路由的容器里渲染守卫；不同路径渲染不同标记文本，便于断言跳转结果。 */
function renderAt(route: string, element: ReactElement) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/" element={<div>首页</div>} />
        <Route path="/admin" element={<div>管理后台</div>} />
        <Route path="/login" element={<div>登录页</div>} />
        <Route path="/admin/login" element={<div>登录页</div>} />
        <Route path="/secret" element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute（需登录才能访问）', () => {
  beforeEach(() => vi.clearAllMocks());

  it('未登录时重定向到登录页', () => {
    setAuth({ isAuthenticated: false });
    renderAt(
      '/secret',
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>,
    );
    expect(screen.getByText('登录页')).toBeInTheDocument();
    expect(screen.queryByText('受保护内容')).not.toBeInTheDocument();
  });

  it('已登录时渲染子内容', () => {
    setAuth({ isAuthenticated: true });
    renderAt(
      '/secret',
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>,
    );
    expect(screen.getByText('受保护内容')).toBeInTheDocument();
  });

  it('鉴权状态加载中显示加载指示，且不误跳转', () => {
    setAuth({ loading: true });
    const { container } = renderAt(
      '/secret',
      <ProtectedRoute>
        <div>受保护内容</div>
      </ProtectedRoute>,
    );
    // 加载中不应把用户踢到登录页
    expect(screen.queryByText('登录页')).not.toBeInTheDocument();
    expect(screen.queryByText('受保护内容')).not.toBeInTheDocument();
    expect(container.querySelector('.animate-spin')).toBeTruthy();
  });
});

describe('PublicOnlyRoute（仅未登录可访问，如登录/注册页）', () => {
  beforeEach(() => vi.clearAllMocks());

  it('未登录时正常渲染登录表单', () => {
    setAuth({ isAuthenticated: false });
    renderAt(
      '/secret',
      <PublicOnlyRoute>
        <div>登录表单</div>
      </PublicOnlyRoute>,
    );
    expect(screen.getByText('登录表单')).toBeInTheDocument();
  });

  it('已登录用户访问登录页被送回首页', () => {
    setAuth({ isAuthenticated: true });
    renderAt(
      '/secret',
      <PublicOnlyRoute>
        <div>登录表单</div>
      </PublicOnlyRoute>,
    );
    expect(screen.getByText('首页')).toBeInTheDocument();
  });

  it('已登录的管理员访问登录页直接进入管理后台', () => {
    setAuth({ isAuthenticated: false, isAdminAuthenticated: true });
    renderAt(
      '/secret',
      <PublicOnlyRoute>
        <div>登录表单</div>
      </PublicOnlyRoute>,
    );
    expect(screen.getByText('管理后台')).toBeInTheDocument();
  });
});

describe('AdminRoute（仅管理员可访问）', () => {
  beforeEach(() => vi.clearAllMocks());

  it('非管理员重定向到管理员登录', () => {
    setAuth({ isAdminAuthenticated: false });
    renderAt(
      '/secret',
      <AdminRoute>
        <div>管理内容</div>
      </AdminRoute>,
    );
    // 未登录访问受保护管理端时重定向到独立的管理员登录页 /admin/login
    expect(screen.getByText('登录页')).toBeInTheDocument();
    expect(screen.queryByText('管理内容')).not.toBeInTheDocument();
  });

  it('管理员可访问管理内容', () => {
    setAuth({ isAdminAuthenticated: true });
    renderAt(
      '/secret',
      <AdminRoute>
        <div>管理内容</div>
      </AdminRoute>,
    );
    expect(screen.getByText('管理内容')).toBeInTheDocument();
  });

  it('管理员鉴权加载中显示加载指示', () => {
    setAuth({ adminLoading: true });
    const { container } = renderAt(
      '/secret',
      <AdminRoute>
        <div>管理内容</div>
      </AdminRoute>,
    );
    expect(screen.queryByText('管理内容')).not.toBeInTheDocument();
    expect(container.querySelector('.animate-spin')).toBeTruthy();
  });
});
