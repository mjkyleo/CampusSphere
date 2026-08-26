import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { api } from '../services/api.ts';
import type { EmailRegisterConfig } from '../types.ts';
import {
  MessageSquare, MessageCircle, Mail, Phone, Lock,
  User, Sparkles, ArrowRight, ShieldCheck, CheckCircle2, KeyRound
} from 'lucide-react';

interface LoginPageProps {
  onLogin?: () => void;
}

type TabMode = 'password_login' | 'phone_login' | 'email_register' | 'standard_register';

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, phoneLogin, emailRegister, register, adminLogin } = useAuth();
  const { success, error, info } = useToast();

  const [mode, setMode] = useState<TabMode>('password_login');
  const [loading, setLoading] = useState(false);

  // Form states
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');

  const [phoneTarget, setPhoneTarget] = useState('');
  const [phoneCode, setPhoneCode] = useState('');

  const [emailTarget, setEmailTarget] = useState('');
  const [emailPassword, setEmailPassword] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [emailNickname, setEmailNickname] = useState('');

  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regNickname, setRegNickname] = useState('');

  // Admin login form（正式入口，不使用硬编码账号）
  const [showAdminForm, setShowAdminForm] = useState(searchParams.get('admin') === '1');
  const [adminGatewayKey, setAdminGatewayKey] = useState('');
  const [adminUsername, setAdminUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  // 邮箱注册规则（由后端公开接口动态提供）
  const [emailConfig, setEmailConfig] = useState<EmailRegisterConfig | null>(null);

  // Countdown timer for verification code
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    api.auth.emailConfig()
      .then((res) => {
        if (res.code === 0 && res.data) setEmailConfig(res.data);
      })
      .catch(() => { /* 后端不可达时保持默认提示 */ });
  }, []);

  // 会话过期被重定向到登录页时给出明确提示
  useEffect(() => {
    if (searchParams.get('reason') === 'session_expired') {
      info('登录状态已失效，请重新登录');
    }
  }, [searchParams, info]);

  const startCountdown = () => {
    setCountdown(60);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSendCode = async (target: string, purpose: 'login' | 'register') => {
    if (!target) {
      error('请先输入手机号或校园邮箱');
      return;
    }
    try {
      const res = await api.auth.sendCode(target, purpose);
      if (res.code === 0) {
        const debugCode = res.data?.debug_code;
        if (debugCode) {
          // 开发/测试模式：验证码随响应返回，自动填入便于联调
          if (target.includes('@')) setEmailCode(debugCode);
          else setPhoneCode(debugCode);
          success(`验证码已发送至 ${target}，测试模式已自动填入`);
        } else {
          success(`验证码已发送至 ${target}，请查收邮件/短信（生产环境需配置发送服务）`);
        }
        startCountdown();
      } else {
        error(res.message || '发送验证码失败');
      }
    } catch {
      error('发送验证码异常，请确认后端服务已启动');
    }
  };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const ok = await login(account, password);
    setLoading(false);
    if (ok) {
      if (onLogin) onLogin();
      navigate('/');
    }
  };

  const handlePhoneLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phoneCode) {
      error('请输入收到的短信验证码');
      return;
    }
    setLoading(true);
    const ok = await phoneLogin(phoneTarget, phoneCode);
    setLoading(false);
    if (ok) {
      if (onLogin) onLogin();
      navigate('/');
    }
  };

  const handleEmailRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailCode) {
      error('请输入收到的邮箱验证码');
      return;
    }
    setLoading(true);
    const ok = await emailRegister(emailTarget, emailPassword, emailCode, emailNickname);
    setLoading(false);
    if (ok) {
      if (onLogin) onLogin();
      navigate('/');
    }
  };

  const handleStandardRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const ok = await register({
      username: regUsername,
      password: regPassword,
      email: regEmail || undefined,
      nickname: regNickname || undefined
    });
    setLoading(false);
    if (ok) {
      setMode('password_login');
      setAccount(regUsername);
      setPassword(regPassword);
    }
  };

  const handleOAuthLogin = (provider: 'wechat' | 'qq') => {
    info(`${provider === 'wechat' ? '微信' : 'QQ'}授权登录需在后台配置应用凭据（AppID/Secret）后开放，当前尚未接入。`);
  };

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminGatewayKey || !adminUsername || !adminPassword) {
      error('请填写网关密钥、管理员账号与密码');
      return;
    }
    setLoading(true);
    const ok = await adminLogin(adminGatewayKey, adminUsername, adminPassword);
    setLoading(false);
    if (ok) {
      if (onLogin) onLogin();
      navigate('/admin');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-xl w-full bg-white rounded-3xl shadow-2xl p-6 sm:p-10 space-y-8 border border-slate-200 relative overflow-hidden">
        {/* Decorative ambient background glows */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-violet-500/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Brand Header */}
        <div className="text-center space-y-2 relative z-10">
          <div className="w-16 h-16 bg-gradient-to-tr from-indigo-600 to-indigo-700 rounded-3xl mx-auto flex items-center justify-center text-white text-3xl font-black mb-3 shadow-xl shadow-indigo-200">
            C
          </div>
          <h1 className="text-3xl font-black tracking-tight text-slate-900">
            CampusSphere
          </h1>
          <p className="text-slate-500 text-sm font-medium">
            校园生活综合服务枢纽
          </p>
        </div>

        {/* Auth Mode Tabs */}
        <div className="grid grid-cols-4 p-1.5 bg-slate-100 rounded-2xl text-xs font-bold relative z-10">
          <button
            onClick={() => setMode('password_login')}
            className={`py-2 rounded-xl transition-all ${
              mode === 'password_login' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            账号登录
          </button>
          <button
            onClick={() => setMode('phone_login')}
            className={`py-2 rounded-xl transition-all ${
              mode === 'phone_login' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            短信登录
          </button>
          <button
            onClick={() => setMode('email_register')}
            className={`py-2 rounded-xl transition-all ${
              mode === 'email_register' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            邮箱注册
          </button>
          <button
            onClick={() => setMode('standard_register')}
            className={`py-2 rounded-xl transition-all ${
              mode === 'standard_register' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            新户注册
          </button>
        </div>

        {/* 1. Password Login Form (Supports Username / Email / Phone) */}
        {mode === 'password_login' && (
          <form onSubmit={handlePasswordLogin} className="space-y-4 relative z-10">
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                统一登录账号 (用户名 / 邮箱 / 手机号)
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  required
                  autoComplete="username"
                  value={account}
                  onChange={(e) => setAccount(e.target.value)}
                  placeholder="用户名 / 邮箱 / 手机号"
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                登录密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入登录密码"
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-base shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 active:scale-[0.99]"
            >
              {loading ? '正在验证身份...' : '立即登录系统'}
              <ArrowRight className="w-5 h-5" />
            </button>
          </form>
        )}

        {/* 2. Phone SMS Login */}
        {mode === 'phone_login' && (
          <form onSubmit={handlePhoneLogin} className="space-y-4 relative z-10">
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                手机号码
              </label>
              <div className="relative">
                <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="tel"
                  required
                  value={phoneTarget}
                  onChange={(e) => setPhoneTarget(e.target.value)}
                  placeholder="11位手机号码"
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                短信验证码
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={phoneCode}
                    onChange={(e) => setPhoneCode(e.target.value)}
                    placeholder="6位数字验证码"
                    className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>
                <button
                  type="button"
                  disabled={countdown > 0}
                  onClick={() => handleSendCode(phoneTarget, 'login')}
                  className="px-4 py-3 bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold rounded-2xl hover:bg-indigo-100 disabled:opacity-50 transition-colors whitespace-nowrap"
                >
                  {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-base shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 active:scale-[0.99]"
            >
              {loading ? '正在验证...' : '手机验证码一键登录'}
              <ArrowRight className="w-5 h-5" />
            </button>
          </form>
        )}

        {/* 3. Email Code Registration */}
        {mode === 'email_register' && (
          <form onSubmit={handleEmailRegister} className="space-y-4 relative z-10">
            <div className="p-3 bg-indigo-50/60 rounded-2xl border border-indigo-100 text-xs text-indigo-800 flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <span>
                {emailConfig && emailConfig.enabled
                  ? `使用白名单校园邮箱注册（${(emailConfig.domains ?? []).join(' / ') || '按后台规则'}），验证码由系统发送至邮箱。`
                  : '邮箱注册暂未开放，请联系管理员在后台「校园配置」中开启。'}
              </span>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                校园教育邮箱
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={emailTarget}
                  onChange={(e) => setEmailTarget(e.target.value)}
                  placeholder="student@example.edu.cn"
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                  设置登录密码
                </label>
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={emailPassword}
                  onChange={(e) => setEmailPassword(e.target.value)}
                  placeholder="不少于6位"
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                  校园昵称
                </label>
                <input
                  type="text"
                  value={emailNickname}
                  onChange={(e) => setEmailNickname(e.target.value)}
                  placeholder="例如: 阳光学长"
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                邮箱验证码
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  required
                  value={emailCode}
                  onChange={(e) => setEmailCode(e.target.value)}
                  placeholder="6位邮件验证码"
                  className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
                <button
                  type="button"
                  disabled={countdown > 0}
                  onClick={() => handleSendCode(emailTarget, 'register')}
                  className="px-4 py-3 bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold rounded-2xl hover:bg-indigo-100 disabled:opacity-50 transition-colors whitespace-nowrap"
                >
                  {countdown > 0 ? `${countdown}s 后重发` : '获取邮箱验证码'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-base shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 active:scale-[0.99]"
            >
              {loading ? '正在注册...' : '完成邮箱认证并进入'}
              <CheckCircle2 className="w-5 h-5" />
            </button>
          </form>
        )}

        {/* 4. Standard Registration Form */}
        {mode === 'standard_register' && (
          <form onSubmit={handleStandardRegister} className="space-y-3.5 relative z-10">
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                用户名 (登录主账号) *
              </label>
              <input
                type="text"
                required
                autoComplete="username"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                placeholder="3-32位字母数字"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                密码 *
              </label>
              <input
                type="password"
                required
                autoComplete="new-password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="不少于6位字符"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                  个性昵称
                </label>
                <input
                  type="text"
                  value={regNickname}
                  onChange={(e) => setRegNickname(e.target.value)}
                  placeholder="展示昵称"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
                  电子邮箱 (可选)
                </label>
                <input
                  type="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="用于找回密码"
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-base shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2"
            >
              {loading ? '正在注册...' : '提交注册'}
            </button>
          </form>
        )}

        {/* Third-Party OAuth & Admin Fast Access */}
        <div className="space-y-4 pt-2 border-t border-slate-100 relative z-10">
          <div className="flex items-center gap-3 justify-center text-xs text-slate-400 font-semibold uppercase tracking-wider">
            <span>或使用第三方快捷授权</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleOAuthLogin('wechat')}
              className="flex items-center justify-center gap-2.5 py-3 px-4 bg-[#07C160]/10 text-[#07C160] hover:bg-[#07C160]/20 border border-[#07C160]/30 rounded-2xl font-bold text-sm transition-all"
            >
              <MessageSquare className="w-5 h-5 fill-[#07C160]" />
              微信授权登录
            </button>

            <button
              type="button"
              onClick={() => handleOAuthLogin('qq')}
              className="flex items-center justify-center gap-2.5 py-3 px-4 bg-[#12B7F5]/10 text-[#12B7F5] hover:bg-[#12B7F5]/20 border border-[#12B7F5]/30 rounded-2xl font-bold text-sm transition-all"
            >
              <MessageCircle className="w-5 h-5 fill-[#12B7F5]" />
              QQ授权登录
            </button>
          </div>

          {/* Admin Dashboard Entry */}
          {!showAdminForm ? (
            <div className="bg-slate-50 p-3 rounded-2xl border border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <ShieldCheck className="w-4 h-4 text-amber-600" />
                <span className="font-semibold">系统管理后台入口</span>
              </div>
              <button
                type="button"
                onClick={() => setShowAdminForm(true)}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold shadow-sm transition-colors"
              >
                管理员登录
              </button>
            </div>
          ) : (
            <form onSubmit={handleAdminLogin} className="bg-slate-50 p-3 rounded-2xl border border-slate-200 space-y-2.5">
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <ShieldCheck className="w-4 h-4 text-amber-600" />
                <span className="font-semibold">管理员登录</span>
                <span className="text-slate-400">（需网关密钥 + 账号密码，均通过部署配置下发）</span>
              </div>
              <input
                type="password"
                required
                value={adminGatewayKey}
                onChange={(e) => setAdminGatewayKey(e.target.value)}
                placeholder="管理后台网关密钥"
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:border-amber-500 outline-none"
              />
              <input
                type="text"
                required
                autoComplete="username"
                value={adminUsername}
                onChange={(e) => setAdminUsername(e.target.value)}
                placeholder="管理员账号"
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:border-amber-500 outline-none"
              />
              <input
                type="password"
                required
                autoComplete="current-password"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="管理员密码"
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:border-amber-500 outline-none"
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold shadow-sm transition-colors"
                >
                  {loading ? '正在验证...' : '进入管理后台'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAdminForm(false)}
                  className="px-3 py-2 bg-white border border-slate-200 text-slate-500 rounded-xl text-xs font-bold hover:bg-slate-100 transition-colors"
                >
                  取消
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer info */}
        <div className="text-center text-xs text-slate-400 leading-relaxed relative z-10">
          登录即代表您已阅读并同意 <a href="/terms" className="text-indigo-600 font-medium hover:underline">校园社区守则</a> 与{' '}
          <a href="/privacy" className="text-indigo-600 font-medium hover:underline">隐私保护协议</a>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
