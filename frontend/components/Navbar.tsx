import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home, ShoppingBag, BookOpen, Utensils, Users, Share2,
  Briefcase, MessageSquare, LayoutDashboard, User, ShieldCheck, LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext.tsx';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, admin, isAuthenticated, isAdminAuthenticated, unreadCount, logout, adminLogout } = useAuth();

  const navItems = [
    { path: '/', icon: Home, label: '首页' },
    { path: '/market', icon: ShoppingBag, label: '二手' },
    { path: '/courses', icon: BookOpen, label: '课程' },
    { path: '/canteens', icon: Utensils, label: '食堂' },
    { path: '/teammates', icon: Users, label: '搭子' },
    { path: '/share', icon: Share2, label: '分享' },
    { path: '/jobs', icon: Briefcase, label: '兼职' },
    { path: '/messages', icon: MessageSquare, label: '消息', badge: unreadCount }
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 lg:top-0 lg:bottom-auto bg-white/95 backdrop-blur-md border-t lg:border-t-0 lg:border-b border-slate-200 px-4 py-2.5 flex justify-between items-center z-50 transition-all shadow-sm">
      {/* Brand logo */}
      <div className="hidden lg:flex items-center gap-3 mr-6">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 bg-gradient-to-tr from-indigo-600 to-indigo-700 rounded-xl flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-200 group-hover:scale-105 transition-transform">
            C
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-lg tracking-tight text-slate-900 leading-tight">
              CampusSphere
            </span>
            <span className="text-[10px] font-semibold text-indigo-600 uppercase tracking-wider">
              校园生活一站式平台
            </span>
          </div>
        </Link>
      </div>

      {/* Nav links */}
      <div className="flex flex-1 justify-around lg:justify-start lg:gap-1.5 overflow-x-auto no-scrollbar py-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`relative flex flex-col lg:flex-row items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs lg:text-sm font-semibold transition-all ${
                isActive
                  ? 'text-indigo-600 bg-indigo-50 lg:bg-indigo-50/80 shadow-xs'
                  : 'text-slate-600 hover:text-indigo-600 hover:bg-slate-50'
              }`}
            >
              <div className="relative">
                <item.icon className="w-5 h-5 lg:w-4.5 lg:h-4.5" />
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="absolute -top-1.5 -right-2 px-1.5 py-0.2 bg-rose-500 text-white text-[10px] font-bold rounded-full border border-white">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Right controls */}
      <div className="hidden lg:flex items-center gap-3 ml-4">
        {isAdminAuthenticated ? (
          <>
            <Link
              to="/admin"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                location.pathname === '/admin'
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
              }`}
              title="管理控制台"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>管理后台</span>
            </Link>
            <button
              onClick={adminLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 transition-all"
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
              className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-2xl hover:bg-slate-50 border border-slate-200 transition-colors"
            >
              <div className="w-7 h-7 rounded-full overflow-hidden bg-slate-100 border border-slate-300 shrink-0">
                <img
                  src={user.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80'}
                  alt="Avatar"
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-xs font-bold text-slate-700 max-w-[90px] truncate">
                {user.nickname || user.username}
              </span>
            </Link>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 transition-all"
              title="退出登录"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>退出</span>
            </button>
          </>
        ) : (
          <Link
            to="/login"
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm shadow-indigo-200"
          >
            <User className="w-3.5 h-3.5" />
            <span>登录 / 注册</span>
          </Link>
        )}
      </div>
    </nav>
  );
};
