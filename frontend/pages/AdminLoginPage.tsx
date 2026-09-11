import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { KeyRound, User, Lock, Loader2, ShieldAlert } from 'lucide-react';

/**
 * 独立的管理员登录页（/admin/login）。
 * - 网关密钥 + 管理员账号 + 密码 三个必填项，提交前做字段级校验；
 * - 登录失败（网关密钥错误 / 账号密码错误 / 后台未开放）以内联红框提示具体原因；
 * - 成功后携带来源地址跳转到 /admin（受 AdminRoute 保护的管理后台）。
 */
const AdminLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { adminLogin } = useAuth();

  const [gatewayKey, setGatewayKey] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{
    gatewayKey?: string;
    username?: string;
    password?: string;
  }>({});

  // AdminRoute 跳转时通过 state.from 记录来源地址，登录成功后回到原页面
  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/admin';

  const validate = (): boolean => {
    const next: typeof fieldErrors = {};
    if (!gatewayKey.trim()) next.gatewayKey = '请输入网关密钥';
    if (!username.trim()) next.username = '请输入管理员账号';
    if (!password) next.password = '请输入登录密码';
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!validate()) return;

    setLoading(true);
    const res = await adminLogin(gatewayKey.trim(), username.trim(), password);
    setLoading(false);

    if (res.ok) {
      navigate(from, { replace: true });
    } else {
      setFormError(res.message || '管理员认证失败，请核对网关密钥与账号密码');
    }
  };

  const clearFieldError = (key: keyof typeof fieldErrors) =>
    setFieldErrors((prev) => ({ ...prev, [key]: undefined }));

  const fieldClass = (hasError?: string) =>
    `w-full pl-11 pr-4 py-3 bg-slate-900 border rounded-2xl text-sm text-white placeholder:text-slate-600 focus:ring-2 outline-none transition-all ${
      hasError
        ? 'border-rose-500 focus:border-rose-500 focus:ring-rose-900'
        : 'border-slate-700 focus:border-indigo-500 focus:ring-indigo-900'
    }`;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4 sm:p-6 lg:p-8">
      <div className="max-w-md w-full bg-slate-800 rounded-3xl shadow-2xl p-6 sm:p-10 space-y-6 border border-slate-700">
        <div className="text-center space-y-2">
          <div className="w-16 h-16 bg-slate-700 rounded-3xl mx-auto flex items-center justify-center text-white mb-3">
            <KeyRound className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white">系统管理后台</h1>
          <p className="text-slate-400 text-sm">需网关密钥 + 管理员账号双重认证</p>
        </div>

        {/* 登录失败提示：覆盖网关密钥错误 / 账号密码错误 / 后台未开放等场景 */}
        {formError && (
          <div className="flex items-start gap-2.5 rounded-2xl border border-rose-500/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5 text-rose-400" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
              网关密钥
            </label>
            <div className="relative">
              <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="password"
                value={gatewayKey}
                onChange={(e) => {
                  setGatewayKey(e.target.value);
                  clearFieldError('gatewayKey');
                }}
                placeholder="ADMIN_GATEWAY_KEY"
                className={fieldClass(fieldErrors.gatewayKey)}
              />
            </div>
            {fieldErrors.gatewayKey && (
              <p className="text-xs text-rose-400">{fieldErrors.gatewayKey}</p>
            )}
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
              管理员账号
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  clearFieldError('username');
                }}
                placeholder="siteadmin"
                className={fieldClass(fieldErrors.username)}
              />
            </div>
            {fieldErrors.username && (
              <p className="text-xs text-rose-400">{fieldErrors.username}</p>
            )}
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
              登录密码
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  clearFieldError('password');
                }}
                placeholder="请输入管理员密码"
                className={fieldClass(fieldErrors.password)}
              />
            </div>
            {fieldErrors.password && (
              <p className="text-xs text-rose-400">{fieldErrors.password}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-indigo-600 text-white text-sm font-bold rounded-2xl hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            进入管理后台
          </button>
        </form>

        <div className="text-center">
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="text-xs text-slate-400 hover:text-slate-200 underline underline-offset-4"
          >
            返回普通用户登录
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminLoginPage;
