import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { api } from '../services/api.ts';
import SliderCaptcha from '../components/SliderCaptcha.tsx';
import GeetestCaptcha from '../components/GeetestCaptcha.tsx';
import type { CaptchaConfig, EmailRegisterConfig } from '../types.ts';
import {
  Mail, Phone, Lock, User, ArrowRight, CheckCircle2, KeyRound, Loader2
} from 'lucide-react';

interface LoginPageProps {
  onLogin?: () => void;
}

type AuthMode = 'login' | 'register';
type LoginTab = 'password' | 'phone';

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, phoneLogin, emailRegister, adminLogin } = useAuth();
  const { success, error, info } = useToast();

  const [mode, setMode] = useState<AuthMode>('login');
  const [loginTab, setLoginTab] = useState<LoginTab>('password');
  const [loading, setLoading] = useState(false);

  // Login form states
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [phoneTarget, setPhoneTarget] = useState('');
  const [phoneCode, setPhoneCode] = useState('');

  // Register form states (email verification required)
  const [emailTarget, setEmailTarget] = useState('');
  const [emailPassword, setEmailPassword] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [emailNickname, setEmailNickname] = useState('');

  // 邮箱注册规则（由后端公开接口动态提供）
  const [emailConfig, setEmailConfig] = useState<EmailRegisterConfig | null>(null);

  // Countdown timer for verification code
  const [countdown, setCountdown] = useState(0);
  const [sendingCode, setSendingCode] = useState(false);

  // 人机验证：开关与提供方均由后端配置下发，前端不自行判断该用哪种
  const [captchaConfig, setCaptchaConfig] = useState<CaptchaConfig | null>(null);
  const [captchaOpen, setCaptchaOpen] = useState(false);
  const [pendingSend, setPendingSend] = useState<{ target: string; purpose: 'login' | 'register' } | null>(null);
  const captchaEnabled = !!captchaConfig?.enabled;
  // 极验已配置 captcha_id 时用它，否则回退到服务端拼图滑块
  const useGeetest = captchaConfig?.provider === 'geetest' && !!captchaConfig?.geetest_id;

  useEffect(() => {
    api.auth.emailConfig()
      .then((res) => {
        if (res.code === 0 && res.data) setEmailConfig(res.data);
      })
      .catch(() => { /* 后端不可达时保持默认提示 */ });
  }, []);

  // 人机验证配置：开关 + 提供方（geetest / builtin），后端可动态切换
  useEffect(() => {
    api.auth.captchaConfig()
      .then((res) => {
        if (res.code === 0 && res.data) setCaptchaConfig(res.data);
      })
      .catch(() => { /* 后端不可达时保持关闭，沿用原有发送流程 */ });
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

  const doSendCode = async (target: string, purpose: 'login' | 'register', ticket?: string) => {
    setSendingCode(true);
    try {
      const res = await api.auth.sendCode(target, purpose, ticket);
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
    } finally {
      setSendingCode(false);
    }
  };

  const handleSendCode = async (target: string, purpose: 'login' | 'register') => {
    if (!target) {
      error(purpose === 'register' ? '请先输入受支持的邮箱' : '请先输入手机号');
      return;
    }
    if (purpose === 'register' && !isEmailValid) {
      error('该邮箱不在当前允许域名列表中');
      return;
    }
    // 开启滑块验证时先弹验证，拿到票据后再真正发送，
    // 避免脚本绕过滑块直接刷验证码。
    if (captchaEnabled) {
      setPendingSend({ target, purpose });
      setCaptchaOpen(true);
      return;
    }
    await doSendCode(target, purpose);
  };

  const handleCaptchaPass = (ticket: string) => {
    setCaptchaOpen(false);
    if (pendingSend) {
      doSendCode(pendingSend.target, pendingSend.purpose, ticket);
      setPendingSend(null);
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

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setLoading(false);
  };

  const isEmailValid = (() => {
    if (!emailTarget || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTarget)) return false;
    if (!emailConfig?.enabled) return true;
    const domain = emailTarget.split('@')[1].toLowerCase();
    const domains = (emailConfig.domains || []).map((d) => d.toLowerCase());
    if (domains.length && !domains.includes(domain)) return false;
    const pattern = emailConfig.pattern?.trim();
    if (pattern) {
      try {
        if (!new RegExp(pattern).test(emailTarget)) return false;
      } catch {
        // 非法正则由后端兜底，前端不阻断
      }
    }
    return true;
  })();

  const inputCls = (extra = '') =>
    `w-full pl-10 pr-4 py-2.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft focus:ring-2 focus:ring-ink/10 outline-none transition-colors ${extra}`;

  return (
    <div className="min-h-screen bg-ground flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md bg-surface rounded-lg shadow-surface overflow-hidden">
        <div className="p-6 sm:p-8">
          {/* Brand */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 bg-primary rounded-lg flex items-center justify-center text-surface font-black text-xl font-display shrink-0">
              C
            </div>
            <span className="font-display font-bold text-xl text-ink">CampusSphere</span>
          </div>

          {/* 模式切换：登录 / 注册 */}
          <div className="grid grid-cols-2 p-1 bg-ground rounded-lg mono-label mb-5">
            <button
              onClick={() => switchMode('login')}
              className={`py-2 rounded-lg transition-colors uppercase tracking-mono ${
                mode === 'login' ? 'bg-primary text-surface shadow-soft' : 'text-steel hover:text-ink'
              }`}
            >
              登录
            </button>
            <button
              onClick={() => switchMode('register')}
              className={`py-2 rounded-lg transition-colors uppercase tracking-mono ${
                mode === 'register' ? 'bg-primary text-surface shadow-soft' : 'text-steel hover:text-ink'
              }`}
            >
              注册
            </button>
          </div>

          {mode === 'login' && (
            <>
              {/* 登录方式：账号 / 短信 */}
              <div className="flex gap-2 mb-5">
                <button
                  type="button"
                  onClick={() => setLoginTab('password')}
                  className={`flex-1 py-2 mono-label uppercase tracking-mono rounded-lg border transition-colors ${
                    loginTab === 'password'
                      ? 'bg-panel border-ink text-ink'
                      : 'bg-transparent border-hairline text-steel hover:border-ink'
                  }`}
                >
                  密码登录
                </button>
                <button
                  type="button"
                  onClick={() => setLoginTab('phone')}
                  className={`flex-1 py-2 mono-label uppercase tracking-mono rounded-lg border transition-colors ${
                    loginTab === 'phone'
                      ? 'bg-panel border-ink text-ink'
                      : 'bg-transparent border-hairline text-steel hover:border-ink'
                  }`}
                >
                  验证码登录
                </button>
              </div>

              {loginTab === 'password' && (
                <form onSubmit={handlePasswordLogin} className="space-y-4">
                  <div>
                    <div className="relative">
                      <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                      <input
                        type="text"
                        required
                        autoComplete="username"
                        value={account}
                        onChange={(e) => setAccount(e.target.value)}
                        placeholder="用户名 / 邮箱 / 手机号"
                        className={inputCls()}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                      <input
                        type="password"
                        required
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="请输入登录密码"
                        className={inputCls()}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-2 active:scale-[0.99]"
                  >
                    {loading ? '请稍候' : '登录'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              )}

              {loginTab === 'phone' && (
                <form onSubmit={handlePhoneLogin} className="space-y-4">
                  <div>
                    <div className="relative">
                      <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                      <input
                        type="tel"
                        required
                        value={phoneTarget}
                        onChange={(e) => setPhoneTarget(e.target.value)}
                        placeholder="11位手机号码"
                        className={inputCls()}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                        <input
                          type="text"
                          required
                          value={phoneCode}
                          onChange={(e) => setPhoneCode(e.target.value)}
                          placeholder="6位数字验证码"
                          className={inputCls('font-mono tracking-[0.2em]')}
                        />
                      </div>
                      <button
                        type="button"
                        disabled={countdown > 0 || sendingCode}
                        onClick={() => handleSendCode(phoneTarget, 'login')}
                        className="px-3.5 py-2.5 bg-panel border border-hairline text-ink mono-label uppercase tracking-mono rounded-lg hover:border-ink disabled:opacity-50 transition-colors whitespace-nowrap"
                      >
                        {sendingCode ? (
                          <span className="flex items-center gap-1.5">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            发送中
                          </span>
                        ) : countdown > 0 ? (
                          `${countdown}s 后重发`
                        ) : (
                          '获取验证码'
                        )}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-2 active:scale-[0.99]"
                  >
                    {loading ? '请稍候' : '登录'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              )}
            </>
          )}

          {mode === 'register' && (
            <form onSubmit={handleEmailRegister} className="space-y-4">
              <div>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={emailTarget}
                    onChange={(e) => setEmailTarget(e.target.value)}
                    placeholder="student@example.edu.cn"
                    className={inputCls()}
                  />
                </div>
              </div>

              <div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    autoComplete="new-password"
                    value={emailPassword}
                    onChange={(e) => setEmailPassword(e.target.value)}
                    placeholder="不少于6位"
                    className={inputCls()}
                  />
                </div>
              </div>

              <div>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                  <input
                    type="text"
                    value={emailNickname}
                    onChange={(e) => setEmailNickname(e.target.value)}
                    placeholder="例如: 阳光学长"
                    className={inputCls()}
                  />
                </div>
              </div>

              <div>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-steel" />
                    <input
                      type="text"
                      required
                      value={emailCode}
                      onChange={(e) => setEmailCode(e.target.value)}
                      placeholder="6位邮件验证码"
                      className={inputCls('font-mono tracking-[0.2em]')}
                    />
                  </div>
                  <button
                    type="button"
                    disabled={countdown > 0 || !isEmailValid || sendingCode}
                    onClick={() => handleSendCode(emailTarget, 'register')}
                    className="px-3.5 py-2.5 bg-panel border border-hairline text-ink mono-label uppercase tracking-mono rounded-lg hover:border-ink disabled:opacity-50 transition-colors whitespace-nowrap"
                  >
                    {sendingCode ? (
                      <span className="flex items-center gap-1.5">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        发送中
                      </span>
                    ) : countdown > 0 ? (
                      `${countdown}s 后重发`
                    ) : (
                      '获取验证码'
                    )}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !emailCode}
                className="w-full py-3 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-2 active:scale-[0.99]"
              >
                {loading ? '请稍候' : '注册'}
                <CheckCircle2 className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Footer switch & agreements */}
          <div className="text-center space-y-2 mt-5">
            <button
              type="button"
              onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
              className="text-body-2 text-primary hover:underline"
            >
              {mode === 'login' ? '没有账号？注册' : '已有账号？登录'}
            </button>
            <p className="text-caption text-steel">
              继续即同意 <a href="/terms" className="text-steel underline">守则</a> ·{' '}
              <a href="/privacy" className="text-steel underline">隐私</a>
            </p>
          </div>
        </div>
      </div>

      {/* 人机验证弹层：发送验证码前的防刷闸门。
          用哪种由后端 captcha/config 下发决定，两种组件对上层暴露同一接口。 */}
      {captchaOpen && useGeetest && captchaConfig?.geetest_id && (
        <GeetestCaptcha
          captchaId={captchaConfig.geetest_id}
          onSuccess={handleCaptchaPass}
          onClose={() => {
            setCaptchaOpen(false);
            setPendingSend(null);
          }}
        />
      )}
      {captchaOpen && !useGeetest && (
        <SliderCaptcha
          onSuccess={handleCaptchaPass}
          onClose={() => {
            setCaptchaOpen(false);
            setPendingSend(null);
          }}
        />
      )}
    </div>
  );
};

export default LoginPage;
