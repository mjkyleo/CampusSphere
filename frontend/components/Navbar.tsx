import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home, ShoppingBag, BookOpen, Utensils, Users, Share2,
  Briefcase, MessageSquare, LayoutDashboard, User, ShieldCheck, LogOut, MoreHorizontal
} from 'lucide-react';
import { useAuth } from '../context/AuthContext.tsx';
import { ImagePlaceholder } from './ui';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, admin, isAuthenticated, isAdminAuthenticated, unreadCount, loading, logout, adminLogout } = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);

  // 路由变化时关闭「更多」抽屉
  useEffect(() => {
    setMoreOpen(false);
  }, [location.pathname]);

  const active = (path: string) =>
    location.pathname === path || (path !== '/' && location.pathname.startsWith(path));

  // 桌面横向导航（全部模块）
  const desktopNav = [
    { path: '/', icon: Home, label: '首页', zone: 'bg-zone-home' },
    { path: '/market', icon: ShoppingBag, label: '二手', zone: 'bg-zone-market' },
    { path: '/courses', icon: BookOpen, label: '课程', zone: 'bg-zone-course' },
    { path: '/canteens', icon: Utensils, label: '食堂', zone: 'bg-zone-canteen' },
    { path: '/teammates', icon: Users, label: '搭子', zone: 'bg-zone-teammate' },
    { path: '/share', icon: Share2, label: '分享', zone: 'bg-zone-share' },
    { path: '/jobs', icon: Briefcase, label: '兼职', zone: 'bg-zone-job' },
    { path: '/messages', icon: MessageSquare, label: '消息', zone: 'bg-zone-message', badge: unreadCount }
  ];

  // 移动端底部主项（4 项：首页 / 市集 / 消息 / 我的）
  const mobilePrimary = [
    { path: '/', icon: Home, label: '首页', zone: 'bg-zone-home' },
    { path: '/market', icon: ShoppingBag, label: '市集', zone: 'bg-zone-market' },
    { path: '/messages', icon: MessageSquare, label: '消息', zone: 'bg-zone-message', badge: unreadCount }
  ];

  // 「更多」抽屉：其余模块 + 管理后台 / 退出
  const moreModules = [
    { path: '/courses', icon: BookOpen, label: '课程', zone: 'bg-zone-course' },
    { path: '/canteens', icon: Utensils, label: '食堂', zone: 'bg-zone-canteen' },
    { path: '/teammates', icon: Users, label: '搭子', zone: 'bg-zone-teammate' },
    { path: '/share', icon: Share2, label: '分享', zone: 'bg-zone-share' },
    { path: '/jobs', icon: Briefcase, label: '兼职', zone: 'bg-zone-job' }
  ];

  const profileHref = isAdminAuthenticated ? '/admin' : isAuthenticated && user ? '/profile' : '/login';
  const profileLabel = loading ? '…' : isAdminAuthenticated ? '后台' : isAuthenticated && user ? (user.nickname || user.username) : '登录';
  const profileZone = isAdminAuthenticated ? 'bg-zone-message' : isAuthenticated && user ? 'bg-zone-home' : 'bg-zone-home';

  const NavLink = ({ item, onAppBar = false }: { item: (typeof desktopNav)[number]; onAppBar?: boolean }) => {
    const isActive = active(item.path);
    return (
      <Link
        to={item.path}
        aria-current={isActive ? 'page' : undefined}
        className={`relative flex flex-col lg:flex-row items-center justify-center gap-1.5 px-2 py-1.5 rounded-md mono-label transition-all duration-[250ms] ease-impeccable ${
          onAppBar
            ? isActive
              ? 'bg-white/20 text-white'
              : 'text-white/80 hover:bg-white/10 hover:text-white'
            : isActive
              ? `${item.zone} text-white`
              : 'text-steel hover:text-ink'
        }`}
      >
        <div className="relative">
          <item.icon className="w-5 h-5 lg:w-4 lg:h-4" strokeWidth={1.8} />
          {item.badge !== undefined && item.badge > 0 && (
            <span className="absolute -top-1.5 -right-2 px-1.5 py-0.5 bg-alert text-ink text-[11px] font-bold rounded-full">
              {item.badge}
            </span>
          )}
        </div>
        <span className="truncate text-[11px] lg:text-xs">{item.label}</span>
      </Link>
    );
  };

  const ProfileSlot = () => {
    const isActive = active(profileHref);
    if (loading) {
      // auth 未就绪：渲染中性骨架占位，避免误显示「登录」入口
      return (
        <div className="relative flex flex-col items-center justify-center gap-1.5 px-2 py-1.5 mono-label" aria-hidden="true">
          <div className="w-5 h-5 rounded-full bg-panel animate-pulse"></div>
          <div className="w-7 h-2 bg-panel animate-pulse rounded"></div>
        </div>
      );
    }
    return (
      <Link
        to={profileHref}
        aria-current={isActive ? 'page' : undefined}
        className={`relative flex flex-col items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg mono-label transition-colors ${
          isActive ? `${profileZone} text-surface` : 'text-steel hover:text-ink'
        }`}
      >
        <div className="relative">
          {isAuthenticated && user ? (
            <div className="w-5 h-5 rounded-full overflow-hidden bg-panel border border-hairline shrink-0">
              {user.avatar ? (
                <img src={user.avatar} alt="头像" className="w-full h-full object-cover" />
              ) : (
                <ImagePlaceholder variant="avatar" className="w-5 h-5" />
              )}
            </div>
          ) : (
            <User className="w-5 h-5" strokeWidth={1.8} />
          )}
        </div>
        <span className="truncate text-[11px] max-w-[52px]">{profileLabel}</span>
      </Link>
    );
  };

  return (
    <>
      {/* 桌面顶部导航 */}
      <nav className="hidden lg:flex fixed top-0 left-0 right-0 h-16 bg-primary px-4 items-center justify-between z-50 shadow-md-4">
        <div className="flex items-center gap-3 mr-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 bg-surface text-primary rounded-md flex items-center justify-center font-bold text-lg shadow-md-2 group-hover:shadow-md-4 transition-all duration-[250ms] ease-impeccable">
              C
            </div>
            <div className="flex flex-col">
              <span className="font-display font-medium text-lg tracking-tight text-white leading-tight">
                CampusSphere
              </span>
              <span className="mono-label text-white/70">校园生活一站式平台</span>
            </div>
          </Link>
        </div>

        <div className="flex flex-1 justify-start gap-1 overflow-x-auto no-scrollbar py-1">
          {desktopNav.map((item) => (
            <React.Fragment key={item.path}>
              <NavLink item={item} onAppBar />
            </React.Fragment>
          ))}
        </div>

        <div className="hidden lg:flex items-center gap-3 ml-4">
          {isAdminAuthenticated ? (
            <>
              <Link
                to="/admin"
                className={`mono-label flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
                  active('/admin') ? 'bg-white/20 text-white border-white/30' : 'bg-transparent text-white/80 border-white/30 hover:bg-white/10'
                }`}
                title="管理控制台"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>管理后台</span>
              </Link>
              <button
                onClick={adminLogout}
                className="mono-label flex items-center gap-1.5 px-3 py-1.5 rounded-md text-white/80 border border-white/30 hover:bg-white/10 transition-colors"
                title="退出管理后台"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>退出</span>
              </button>
            </>
          ) : isAuthenticated && user ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-md border border-white/30 hover:bg-white/10 transition-colors"
              >
                <div className="w-7 h-7 rounded-full overflow-hidden bg-panel border border-hairline shrink-0">
                  {user.avatar ? (
                    <img src={user.avatar} alt="头像" className="w-full h-full object-cover" />
                  ) : (
                    <ImagePlaceholder variant="avatar" className="w-7 h-7" />
                  )}
                </div>
                <span className="mono-label text-white max-w-[90px] truncate">
                  {user.nickname || user.username}
                </span>
              </Link>
              <button
                onClick={logout}
                className="mono-label flex items-center gap-1.5 px-3 py-1.5 rounded-md text-white/80 border border-white/30 hover:bg-white/10 transition-colors"
                title="退出登录"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>退出</span>
              </button>
            </>
          ) : loading ? (
            <div className="flex items-center gap-2.5 pl-2 pr-3 py-1.5" aria-hidden="true">
              <div className="w-7 h-7 rounded-full bg-white/20 animate-pulse shrink-0"></div>
              <div className="w-16 h-3 bg-white/20 animate-pulse rounded"></div>
            </div>
          ) : (
            <Link
              to="/login"
              className="mono-label flex items-center gap-1.5 px-4 py-2 rounded-md bg-white text-primary shadow-md-2 hover:bg-white/90 hover:shadow-md-4 transition-all duration-[250ms] ease-impeccable"
            >
              <User className="w-3.5 h-3.5" />
              <span>登录 / 注册</span>
            </Link>
          )}
        </div>
      </nav>

      {/* 移动端底部导航：4 主项 + 更多 */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-surface/90 backdrop-blur-xl z-50 shadow-[0_-4px_20px_rgba(99,102,241,0.10)]">
        {/* 更多抽屉 */}
        {moreOpen && (
          <div className="absolute bottom-full left-0 right-0 bg-surface/95 backdrop-blur-xl shadow-elevate rounded-t-xl">
            <div className="grid grid-cols-4 gap-1 p-3">
              {moreModules.map((m) => {
                const isActive = active(m.path);
                return (
                  <Link
                    key={m.path}
                    to={m.path}
                    className={`flex flex-col items-center gap-1.5 px-2 py-2.5 rounded-lg mono-label transition-colors ${
                      isActive ? `${m.zone} text-surface` : 'text-steel hover:text-ink'
                    }`}
                  >
                    <m.icon className="w-5 h-5" strokeWidth={1.8} />
                    <span className="text-[11px]">{m.label}</span>
                  </Link>
                );
              })}
              {isAdminAuthenticated && (
                <Link
                  to="/admin"
                  className="flex flex-col items-center gap-1.5 px-2 py-2.5 rounded-lg mono-label text-steel hover:text-ink"
                >
                  <ShieldCheck className="w-5 h-5" strokeWidth={1.8} />
                  <span className="text-[11px]">管理</span>
                </Link>
              )}
              {isAuthenticated && user && (
                <button
                  onClick={logout}
                  className="flex flex-col items-center gap-1.5 px-2 py-2.5 rounded-lg mono-label text-error hover:text-error"
                >
                  <LogOut className="w-5 h-5" strokeWidth={1.8} />
                  <span className="text-[11px]">退出</span>
                </button>
              )}
            </div>
            <div className="px-3 pb-2">
              <div className="mono-label text-steel text-center text-[11px] border-t border-hairline pt-2">
                CampusSphere · 全部功能区
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-5 items-center px-2 py-1.5">
          {mobilePrimary.map((item) => (
            <React.Fragment key={item.path}>
              <NavLink item={item} />
            </React.Fragment>
          ))}
          <ProfileSlot />
          <button
            onClick={() => setMoreOpen((v) => !v)}
            aria-expanded={moreOpen}
            aria-label={moreOpen ? '收起更多功能' : '展开更多功能'}
            className={`flex flex-col items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg mono-label transition-colors ${
              moreOpen ? 'text-ink' : 'text-steel hover:text-ink'
            }`}
          >
            <MoreHorizontal className="w-5 h-5" strokeWidth={1.8} />
            <span className="text-[11px]">更多</span>
          </button>
        </div>
      </nav>
    </>
  );
};
