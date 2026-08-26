import React, { createContext, useContext, useState, useEffect, useRef, ReactNode, useCallback } from 'react';
import { api, getStoredAccessToken, setAuthTokens, clearAuthTokens } from '../services/api.ts';
import { wsClient } from '../services/websocket.ts';
import { UserProfileOut, BindingsOut, ReportTargetType } from '../types.ts';
import { useToast } from './ToastContext.tsx';

interface AuthContextType {
  user: UserProfileOut | null;
  bindings: BindingsOut | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  unreadCount: number;
  loading: boolean;
  login: (account: string, pass: string) => Promise<boolean>;
  phoneLogin: (target: string, code: string) => Promise<boolean>;
  emailRegister: (email: string, pass: string, code: string, nickname?: string) => Promise<boolean>;
  register: (params: { username: string; password: string; email?: string; phone?: string; nickname?: string }) => Promise<boolean>;
  adminLogin: (username: string, pass: string) => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (data: Partial<UserProfileOut>) => Promise<boolean>;
  refreshBindings: () => Promise<void>;
  refreshUnread: () => Promise<void>;
  toggleAdminMode: () => void;
  // Global Report Modal
  reportModal: {
    isOpen: boolean;
    targetType: ReportTargetType;
    targetId: string;
    targetTitle: string;
  };
  openReport: (type: ReportTargetType, id: string, title?: string) => void;
  closeReport: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfileOut | null>(null);
  const [bindings, setBindings] = useState<BindingsOut | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const { success, error, info } = useToast();

  // Report Modal state
  const [reportModal, setReportModal] = useState<{
    isOpen: boolean;
    targetType: ReportTargetType;
    targetId: string;
    targetTitle: string;
  }>({
    isOpen: false,
    targetType: 'item',
    targetId: '',
    targetTitle: ''
  });

  const openReport = (type: ReportTargetType, id: string, title = '') => {
    setReportModal({
      isOpen: true,
      targetType: type,
      targetId: id,
      targetTitle: title
    });
  };

  const closeReport = () => {
    setReportModal((prev) => ({ ...prev, isOpen: false }));
  };

  const loadUserData = useCallback(async () => {
    try {
      const res = await api.users.getMe();
      if (res.code === 0 && res.data) {
        setUser(res.data);
        setIsAuthenticated(true);
        // Establish WebSocket connection after successful auth
        const token = getStoredAccessToken();
        if (token) {
          wsClient.connect(token);
        }
      }
      const bRes = await api.auth.getBindings();
      if (bRes.code === 0 && bRes.data) {
        setBindings(bRes.data);
      }
      const uRes = await api.messages.unread();
      if (uRes.code === 0 && uRes.data) {
        setUnreadCount(uRes.data.unread_count);
      }
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (token) {
      loadUserData();
    } else {
      // 未登录：直接结束 loading，不做无谓请求
      setLoading(false);
    }
  }, [loadUserData]);

  // WebSocket: listen for incoming messages to update the unread badge.
  // Depends on `user` so the handler always has access to the current user ID.
  useEffect(() => {
    if (!user) return;
    const unsubscribe = wsClient.on('message:new', (data) => {
      // Only increment if the message is from someone else
      if (data && data.sender_id && data.sender_id !== user.id) {
        setUnreadCount((prev) => prev + 1);
      }
    });
    return unsubscribe;
  }, [user]);

  const login = async (account: string, pass: string): Promise<boolean> => {
    const res = await api.auth.login(account, pass);
    if (res.code === 0) {
      success('登录成功，欢迎回来！');
      await loadUserData();
      return true;
    } else {
      error(res.message || '登录失败，请核对账号与密码');
      return false;
    }
  };

  const phoneLogin = async (target: string, code: string): Promise<boolean> => {
    const res = await api.auth.phoneLogin(target, code);
    if (res.code === 0) {
      success('验证码登录成功！');
      await loadUserData();
      return true;
    } else {
      error(res.message || '验证码错误或已过期');
      return false;
    }
  };

  const emailRegister = async (email: string, pass: string, code: string, nickname?: string): Promise<boolean> => {
    const res = await api.auth.emailRegister(email, pass, code, nickname);
    if (res.code === 0) {
      success('校园邮箱注册成功，已自动登录！');
      await loadUserData();
      return true;
    } else {
      error(res.message || '邮箱注册失败，请检查验证码或邮箱域名');
      return false;
    }
  };

  const register = async (params: { username: string; password: string; email?: string; phone?: string; nickname?: string }): Promise<boolean> => {
    const res = await api.auth.register(params);
    if (res.code === 0) {
      success('账号注册成功，请登录！');
      return true;
    } else {
      error(res.message || '注册失败');
      return false;
    }
  };

  const adminLogin = async (username: string, pass: string): Promise<boolean> => {
    const res = await api.admin.login(username, pass);
    if (res.code === 0) {
      setIsAdmin(true);
      success('管理员认证成功！');
      await loadUserData();
      return true;
    } else {
      error(res.message || '管理员认证失败');
      return false;
    }
  };

  const logout = async () => {
    wsClient.disconnect();
    await api.auth.logout();
    clearAuthTokens();
    setUser(null);
    setIsAuthenticated(false);
    setIsAdmin(false);
    info('您已退出当前账号');
  };

  const updateProfile = async (data: Partial<UserProfileOut>): Promise<boolean> => {
    const res = await api.users.updateMe(data);
    if (res.code === 0 && res.data) {
      setUser(res.data);
      success('个人资料已保存更新');
      return true;
    } else {
      error(res.message || '更新失败');
      return false;
    }
  };

  const refreshBindings = async () => {
    const res = await api.auth.getBindings();
    if (res.code === 0 && res.data) {
      setBindings(res.data);
    }
  };

  const refreshUnread = async () => {
    const res = await api.messages.unread();
    if (res.code === 0 && res.data) {
      setUnreadCount(res.data.unread_count);
    }
  };

  // Keep a ref to refreshUnread so the WebSocket listener always calls
  // the latest version without re-subscribing on every render.
  const refreshUnreadRef = useRef(refreshUnread);
  refreshUnreadRef.current = refreshUnread;

  // Listen for incoming WebSocket messages to auto-update the unread badge.
  // This subscription persists for the lifetime of AuthProvider (one per tab).
  useEffect(() => {
    const unsub = wsClient.on('message:new', () => {
      refreshUnreadRef.current();
    });
    return () => unsub();
  }, []);

  const toggleAdminMode = () => {
    setIsAdmin((prev) => !prev);
    if (!isAdmin) {
      info('已切换至管理员模式');
    } else {
      info('已切换回普通用户模式');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        bindings,
        isAuthenticated,
        isAdmin,
        unreadCount,
        loading,
        login,
        phoneLogin,
        emailRegister,
        register,
        adminLogin,
        logout,
        updateProfile,
        refreshBindings,
        refreshUnread,
        toggleAdminMode,
        reportModal,
        openReport,
        closeReport
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
