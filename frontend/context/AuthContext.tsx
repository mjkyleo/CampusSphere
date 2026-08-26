import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import {
  api,
  getStoredAccessToken,
  getStoredAdminAccessToken,
  setAuthTokens,
  clearAuthTokens,
  clearAdminAuthTokens
} from '../services/api.ts';
import { wsClient } from '../services/websocket.ts';
import { UserProfileOut, BindingsOut, ReportTargetType, AdminOut } from '../types.ts';
import { useToast } from './ToastContext.tsx';

interface AuthContextType {
  user: UserProfileOut | null;
  admin: AdminOut | null;
  bindings: BindingsOut | null;
  isAuthenticated: boolean;
  isAdminAuthenticated: boolean;
  unreadCount: number;
  loading: boolean;
  adminLoading: boolean;
  login: (account: string, pass: string) => Promise<boolean>;
  phoneLogin: (target: string, code: string) => Promise<boolean>;
  emailRegister: (email: string, pass: string, code: string, nickname?: string) => Promise<boolean>;
  register: (params: { username: string; password: string; email?: string; phone?: string; nickname?: string }) => Promise<boolean>;
  adminLogin: (username: string, pass: string) => Promise<boolean>;
  logout: () => Promise<void>;
  adminLogout: () => Promise<void>;
  updateProfile: (data: Partial<UserProfileOut>) => Promise<boolean>;
  refreshBindings: () => Promise<void>;
  refreshUnread: () => Promise<void>;
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
  const [admin, setAdmin] = useState<AdminOut | null>(null);
  const [bindings, setBindings] = useState<BindingsOut | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState<boolean>(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [adminLoading, setAdminLoading] = useState<boolean>(true);
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
        const token = getStoredAccessToken();
        if (token) {
          wsClient.connect(token);
        }
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
      // 非关键请求（绑定信息/未读数）失败时降级处理，不打断登录态
      const bRes = await api.auth.getBindings();
      setBindings(
        bRes.code === 0 && bRes.data
          ? bRes.data
          : { username: '', email: null, phone: null, wechat_bound: false, qq_bound: false, oauth: [] }
      );
      const uRes = await api.messages.unread();
      setUnreadCount(uRes.code === 0 && uRes.data ? uRes.data.unread_count : 0);
    } catch {
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAdminData = useCallback(async () => {
    try {
      const res = await api.admin.getMe();
      if (res.code === 0 && res.data) {
        setAdmin(res.data);
        setIsAdminAuthenticated(true);
      } else {
        setAdmin(null);
        setIsAdminAuthenticated(false);
      }
    } catch {
      setAdmin(null);
      setIsAdminAuthenticated(false);
    } finally {
      setAdminLoading(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const userToken = getStoredAccessToken();
    const adminToken = getStoredAdminAccessToken();
    if (userToken) {
      loadUserData();
    }
    if (adminToken) {
      loadAdminData();
    }
    if (!userToken && !adminToken) {
      setLoading(false);
      setAdminLoading(false);
    }
  }, [loadUserData, loadAdminData]);

  // WebSocket: listen for incoming messages to update the unread badge.
  useEffect(() => {
    if (!user) return;
    const unsubscribe = wsClient.on('message:new', (data) => {
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
      success('管理员认证成功！');
      await loadAdminData();
      return true;
    } else {
      error(res.message || '管理员认证失败');
      return false;
    }
  };

  const logout = async () => {
    wsClient.disconnect();
    try { await api.auth.logout(); } catch {}
    clearAuthTokens();
    setUser(null);
    setIsAuthenticated(false);
    setBindings(null);
    setUnreadCount(0);
    info('您已退出当前账号');
  };

  const adminLogout = async () => {
    clearAdminAuthTokens();
    setAdmin(null);
    setIsAdminAuthenticated(false);
    info('您已退出管理后台');
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

  // Listen for incoming WebSocket messages to auto-update the unread badge.
  useEffect(() => {
    const unsub = wsClient.on('message:new', () => {
      refreshUnread();
    });
    return () => unsub();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        admin,
        bindings,
        isAuthenticated,
        isAdminAuthenticated,
        unreadCount,
        loading,
        adminLoading,
        login,
        phoneLogin,
        emailRegister,
        register,
        adminLogin,
        logout,
        adminLogout,
        updateProfile,
        refreshBindings,
        refreshUnread,
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
