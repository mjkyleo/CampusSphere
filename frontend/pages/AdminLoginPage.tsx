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
    `w-full pl-10 pr-4 py-2.5 bg-surface border rounded-lg text-body-1 text-ink placeholder:text-steel focus:bg-white focus:ring-2 outline-none transition-colors ${
      hasError
        ? 'border-error focus:border-error focus:ring-error/10'
        : 'border-hairline focus:shadow-soft focus:ring-ink/10'
    }`;

  return (
    <div className="min-h-screen bg-ground flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-md w-full bg-surface rounded-lg shadow-surface border border-hairline overflow-hidden">
        {/* 凭证顶条：管理调度认证 */}
        <div className="px-6 py-2.5 border-b border-hairline bg-panel/60 flex items-center gap-2">
          <KeyRound className="w-3.5 h-3.5 text-ink" />
          <span className="mono-label text-steel tracking-mono">ADMIN · 管理调度认证</span>
        </div>

        <div className="p-6 sm:p-8 space-y-6">
          <div className="space-y-1.5">
            <h1 className="text-heading-2 text-ink">系统管理后台</h1>
            <p className="mono-label text-steel tracking-mono">需网关密钥 + 管理员账号双重认证</p>
          </div>

          {/* 登录失败提示：覆盖网关密钥错误 / 账号密码错误 / 后台未开放等场景 */}
          {formError && (
            <div className="flex items-start gap-2.5 rounded-lg border border-error/60 bg-error/5 px-4 py-3 text-body-2 text-error">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="space-y-1">
              <label className="block mono-label text-steel tracking-mono">网关密钥</label>
              <div className="relative">
                <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                <input
                  type="password"
                  value={gatewayKey}
                  onChange={(e) => {
                    setGatewayKey(e.target.value);
                    clearFieldError('gatewayKey');
                  }}
                  placeholder="ADMIN_GATEWAY_KEY"
                  className={fieldClass(fieldErrors.gatewayKey) + ' font-mono tracking-widest'}
                />
              </div>
              {fieldErrors.gatewayKey && (
                <p className="text-xs text-error">{fieldErrors.gatewayKey}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="block mono-label text-steel tracking-mono">管理员账号</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    clearFieldError('username');
                  }}
                  placeholder="siteadmin"
                  className={fieldClass(fieldErrors.username) + ' font-mono'}
                />
              </div>
              {fieldErrors.username && (
                <p className="text-xs text-error">{fieldErrors.username}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="block mono-label text-steel tracking-mono">登录密码</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
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
                <p className="text-xs text-error">{fieldErrors.password}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-2 active:scale-[0.99]"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              进入管理后台
            </button>
          </form>

          <div className="text-center">
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="text-caption text-steel hover:text-ink underline underline-offset-4 transition-colors"
            >
              返回普通用户登录
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminLoginPage;
