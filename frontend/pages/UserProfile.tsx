import React, { useState, useEffect } from 'react';
import {
  User, Shield, Mail, Phone, Lock, Edit3, MessageCircle,
  MessageSquare, ShoppingBag, Heart, CheckCircle2, AlertCircle,
  LogOut, Sparkles, Building, Bookmark, KeyRound, Link as LinkIcon
} from 'lucide-react';
import { api, formatPrice } from '../services/api.ts';
import { UserProfileOut, BindingsOut, ItemOut, CaptchaConfig } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { Link, useNavigate } from 'react-router-dom';
import SliderCaptcha from '../components/SliderCaptcha.tsx';
import GeetestCaptcha from '../components/GeetestCaptcha.tsx';

type Tab = 'profile' | 'security' | 'my_items' | 'favorites';

const UserProfile: React.FC = () => {
  const navigate = useNavigate();
  const { user, bindings, logout, updateProfile, refreshBindings } = useAuth();
  const { success, error, info } = useToast();

  const [activeTab, setActiveTab] = useState<Tab>('profile');

  // Edit form state
  const [nickname, setNickname] = useState('');
  const [avatar, setAvatar] = useState('');
  const [bio, setBio] = useState('');
  const [campus, setCampus] = useState('');
  const [major, setMajor] = useState('');
  const [grade, setGrade] = useState('');
  const [contactWx, setContactWx] = useState('');
  const [saving, setSaving] = useState(false);

  // Security password change state
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPass, setChangingPass] = useState(false);

  // Binding states
  const [bindPhoneNum, setBindPhoneNum] = useState('');
  const [bindPhoneCode, setBindPhoneCode] = useState('');
  const [bindEmailAddr, setBindEmailAddr] = useState('');
  const [bindEmailCode, setBindEmailCode] = useState('');

  // 绑定验证码发送状态：人机验证配置 / 弹层 / 倒计时（与 LoginPage 同一套后端闸门）
  const [captchaConfig, setCaptchaConfig] = useState<CaptchaConfig | null>(null);
  const [captchaOpen, setCaptchaOpen] = useState(false);
  const [pendingSend, setPendingSend] = useState<{ target: string; purpose: 'bind_email' | 'bind_phone' } | null>(null);
  const [sendingCode, setSendingCode] = useState(false);
  const [codeCooldown, setCodeCooldown] = useState<{ target: string; seconds: number }>({ target: '', seconds: 0 });

  // My items & favorites
  const [myItems, setMyItems] = useState<ItemOut[]>([]);
  const [favorites, setFavorites] = useState<ItemOut[]>([]);

  useEffect(() => {
    if (user) {
      setNickname(user.nickname || '');
      setAvatar(user.avatar || '');
      setBio(user.bio || '');
      setCampus(user.campus || '');
      setMajor(user.school_major || '');
      setGrade(user.grade ? String(user.grade) : '');
      setContactWx(user.contact_wx || '');
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      // Load user's published items and favorites
      api.users.getItems(user.id).then((res) => {
        if (res.code === 0 && res.data) setMyItems(res.data.items || []);
      });
      api.users.getFavorites(user.id).then((res) => {
        if (res.code === 0 && res.data) setFavorites(res.data.items || []);
      });
    }
  }, [user]);

  // 人机验证配置：发送验证码是否需要滑块/极验票据（后端可动态切换）
  useEffect(() => {
    api.auth.captchaConfig()
      .then((res) => {
        if (res.code === 0 && res.data) setCaptchaConfig(res.data);
      })
      .catch(() => { /* 拉取失败按关闭处理，沿用直接发送 */ });
  }, []);

  const startCooldown = (target: string) => {
    setCodeCooldown({ target, seconds: 60 });
    const interval = setInterval(() => {
      setCodeCooldown((prev) => {
        if (prev.seconds <= 1) {
          clearInterval(interval);
          return { target: '', seconds: 0 };
        }
        return { ...prev, seconds: prev.seconds - 1 };
      });
    }, 1000);
  };

  const doSendBindCode = async (target: string, purpose: 'bind_email' | 'bind_phone', ticket?: string) => {
    setSendingCode(true);
    try {
      const res = await api.auth.sendCode(target, purpose, ticket);
      if (res.code === 0) {
        const debugCode = res.data?.debug_code;
        if (debugCode) {
          // 开发/测试模式：验证码随响应返回，自动填入便于联调
          if (purpose === 'bind_email') setBindEmailCode(debugCode);
          else setBindPhoneCode(debugCode);
          success(`验证码已发送至 ${target}，测试模式已自动填入`);
        } else {
          success(`验证码已发送至 ${target}，请查收邮件/短信`);
        }
        startCooldown(target);
      } else {
        error(res.message || '发送验证码失败');
      }
    } catch {
      error('发送验证码异常，请确认后端服务已启动');
    } finally {
      setSendingCode(false);
    }
  };

  const handleSendBindCode = (target: string, purpose: 'bind_email' | 'bind_phone') => {
    if (!target) {
      error(purpose === 'bind_email' ? '请先输入要绑定的邮箱' : '请先输入要绑定的手机号');
      return;
    }
    if (purpose === 'bind_email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(target)) {
      error('邮箱格式不正确');
      return;
    }
    if (purpose === 'bind_phone' && !/^1[3-9]\d{9}$/.test(target)) {
      error('手机号格式不正确');
      return;
    }
    // 开启人机验证时先弹验证，拿到票据后再真正发送
    if (captchaConfig?.enabled) {
      setPendingSend({ target, purpose });
      setCaptchaOpen(true);
      return;
    }
    doSendBindCode(target, purpose);
  };

  const handleCaptchaPass = (ticket: string) => {
    setCaptchaOpen(false);
    if (pendingSend) {
      doSendBindCode(pendingSend.target, pendingSend.purpose, ticket);
      setPendingSend(null);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const ok = await updateProfile({
      nickname: nickname.trim(),
      avatar: avatar.trim(),
      bio: bio.trim(),
      campus: campus.trim(),
      school_major: major.trim(),
      grade: grade ? Number(grade) : undefined,
      contact_wx: contactWx.trim()
    });
    setSaving(false);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!oldPassword || !newPassword) {
      error('请填写完整新旧密码');
      return;
    }
    if (newPassword !== confirmPassword) {
      error('两次输入的新密码不一致');
      return;
    }

    setChangingPass(true);
    try {
      const res = await api.users.changePassword(oldPassword, newPassword);
      if (res.code === 0) {
        success('密码修改成功！请妥善保管新密码');
        setOldPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        error(res.message || '原密码错误，修改失败');
      }
    } catch {
      error('修改密码异常');
    } finally {
      setChangingPass(false);
    }
  };

  const handleBindPhone = async () => {
    if (!bindPhoneNum || !bindPhoneCode) {
      error('请填写手机号及验证码');
      return;
    }
    const res = await api.auth.bindPhone(bindPhoneNum, bindPhoneCode);
    if (res.code === 0) {
      success('手机号码绑定成功！');
      refreshBindings();
      setBindPhoneNum('');
      setBindPhoneCode('');
    } else {
      error(res.message || '绑定失败');
    }
  };

  const handleBindEmail = async () => {
    if (!bindEmailAddr || !bindEmailCode) {
      error('请填写邮箱及验证码');
      return;
    }
    const res = await api.auth.bindEmail(bindEmailAddr, bindEmailCode);
    if (res.code === 0) {
      success('教育邮箱绑定成功！');
      refreshBindings();
      setBindEmailAddr('');
      setBindEmailCode('');
    } else {
      error(res.message || '绑定失败');
    }
  };

  const handleOAuthToggle = async (provider: 'wechat' | 'qq', currentBound: boolean) => {
    if (currentBound) {
      const res = await api.auth.unbindOAuth(provider);
      if (res.code === 0) {
        success(`已解除 ${provider === 'wechat' ? '微信' : 'QQ'} 账号绑定`);
        refreshBindings();
      }
    } else {
      const res = await api.auth.bindOAuth(provider, 'auth_code_mock');
      if (res.code === 0) {
        success(`已成功绑定 ${provider === 'wechat' ? '微信' : 'QQ'} 账号！`);
        refreshBindings();
      }
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-24">
      {/* Profile Header Banner */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="relative">
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl overflow-hidden bg-slate-100 border-2 border-indigo-100 shadow-md">
              <img
                src={avatar || user?.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300'}
                alt="Avatar"
                className="w-full h-full object-cover"
              />
            </div>
            <span className="absolute -bottom-1 -right-1 p-1 bg-emerald-500 text-white rounded-full border-2 border-white">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </span>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-slate-900">{user?.nickname || '校园同学'}</h1>
              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-lg">
                {user?.role === 'admin' ? '系统管理员' : '已认证学生'}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              账号：@{user?.username || 'campus_student'} • 校区：{user?.campus || '主校区'}
            </p>
            <p className="text-xs text-slate-600 font-normal">
              {user?.bio || '勤学善思，积极探索校园美好生活。'}
            </p>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-slate-100 hover:bg-rose-50 hover:text-rose-600 text-slate-600 rounded-2xl text-xs font-bold transition-colors self-start sm:self-center"
        >
          <LogOut className="w-4 h-4" />
          退出当前登录
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1.5 bg-slate-100 rounded-2xl text-xs font-bold overflow-x-auto no-scrollbar">
        {[
          { id: 'profile', label: '基本资料修改', icon: Edit3 },
          { id: 'security', label: '账号安全与第三方绑定', icon: Shield },
          { id: 'my_items', label: `我发布的闲置 (${myItems.length})`, icon: ShoppingBag },
          { id: 'favorites', label: `我的收藏夹 (${favorites.length})`, icon: Heart }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as Tab)}
            className={`flex items-center gap-2 py-2.5 px-4 rounded-xl transition-all whitespace-nowrap ${
              activeTab === t.id
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <t.icon className="w-4 h-4" />
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Tab 1: Profile Edit */}
      {activeTab === 'profile' && (
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
          <div>
            <h3 className="text-lg font-bold text-slate-900">个人主页信息设置</h3>
            <p className="text-xs text-slate-500">完善个人资料有助于提升二手交易信用与搭子组队成功率</p>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">展示昵称 *</label>
                <input
                  type="text"
                  required
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">头像图片 URL</label>
                <input
                  type="url"
                  value={avatar}
                  onChange={(e) => setAvatar(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">所在校区</label>
                <input
                  type="text"
                  value={campus}
                  onChange={(e) => setCampus(e.target.value)}
                  placeholder="例如: 主校区 / 科学城校区"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">专业方向</label>
                <input
                  type="text"
                  value={major}
                  onChange={(e) => setMajor(e.target.value)}
                  placeholder="例如: 软件工程 / 金融学"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">入学年份</label>
                <select
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                >
                  <option value="">请选择入学年份</option>
                  {Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i).map((y) => (
                    <option key={y} value={y}>{y} 级</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-700">微信号 (可选，用于搭子/二手联系)</label>
              <input
                type="text"
                value={contactWx}
                onChange={(e) => setContactWx(e.target.value)}
                placeholder="例如: campus_partner_01"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-700">个性签名与简介</label>
              <textarea
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="介绍一下自己吧，例如你的兴趣爱好、自习常去地点等..."
                className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all disabled:opacity-50"
            >
              {saving ? '正在保存...' : '保存资料修改'}
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Security & Bindings */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          {/* Third-Party Bindings Box */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
            <h3 className="text-lg font-bold text-slate-900">多渠道认证与账号绑定</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* WeChat */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-[#07C160]/10 text-[#07C160] rounded-xl">
                    <MessageSquare className="w-5 h-5 fill-current" />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-800 text-sm">微信账号</h4>
                    <p className="text-[11px] text-slate-500">
                      {bindings?.wechat_bound ? '已完成绑定授权' : '未绑定'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleOAuthToggle('wechat', !!bindings?.wechat_bound)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                    bindings?.wechat_bound
                      ? 'bg-slate-200 text-slate-700 hover:bg-rose-50 hover:text-rose-600'
                      : 'bg-[#07C160] text-white hover:bg-[#06ad56]'
                  }`}
                >
                  {bindings?.wechat_bound ? '解除绑定' : '立即绑定'}
                </button>
              </div>

              {/* QQ */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-[#12B7F5]/10 text-[#12B7F5] rounded-xl">
                    <MessageCircle className="w-5 h-5 fill-current" />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-800 text-sm">QQ 账号</h4>
                    <p className="text-[11px] text-slate-500">
                      {bindings?.qq_bound ? '已完成绑定授权' : '未绑定'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleOAuthToggle('qq', !!bindings?.qq_bound)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                    bindings?.qq_bound
                      ? 'bg-slate-200 text-slate-700 hover:bg-rose-50 hover:text-rose-600'
                      : 'bg-[#12B7F5] text-white hover:bg-[#0ea5dc]'
                  }`}
                >
                  {bindings?.qq_bound ? '解除绑定' : '立即绑定'}
                </button>
              </div>
            </div>
          </div>

          {/* Email / Phone Binding：验证码获取入口 + 绑定提交。
              此前只有提交逻辑没有发送入口，绑定流程在界面上走不通。 */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
            <div>
              <h3 className="text-lg font-bold text-slate-900">邮箱与手机绑定</h3>
              <p className="text-xs text-slate-500">绑定后可使用邮箱 / 手机号 + 密码登录</p>
            </div>

            {/* 绑定邮箱 */}
            <form
              className="space-y-3 max-w-md"
              onSubmit={(e) => {
                e.preventDefault();
                handleBindEmail();
              }}
            >
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">
                  邮箱{bindings?.email ? <span className="ml-2 font-normal text-emerald-600">已绑定 {bindings.email}</span> : ''}
                </label>
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={bindEmailAddr}
                    onChange={(e) => setBindEmailAddr(e.target.value)}
                    placeholder="例如: student@whu.edu.cn"
                    className="flex-1 min-w-0 px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                  />
                  <button
                    type="button"
                    disabled={sendingCode || (codeCooldown.seconds > 0 && codeCooldown.target === bindEmailAddr)}
                    onClick={() => handleSendBindCode(bindEmailAddr, 'bind_email')}
                    className="px-3.5 py-2.5 whitespace-nowrap bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-xl text-xs font-bold hover:bg-indigo-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {codeCooldown.seconds > 0 && codeCooldown.target === bindEmailAddr ? `${codeCooldown.seconds}s 后重发` : '获取验证码'}
                  </button>
                </div>
              </div>
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">邮箱验证码</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={bindEmailCode}
                  onChange={(e) => setBindEmailCode(e.target.value)}
                  placeholder="6 位数字验证码"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm tracking-widest focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
              <button
                type="submit"
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all"
              >
                绑定邮箱
              </button>
            </form>

            {/* 绑定手机号 */}
            <form
              className="space-y-3 max-w-md"
              onSubmit={(e) => {
                e.preventDefault();
                handleBindPhone();
              }}
            >
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">
                  手机号{bindings?.phone ? <span className="ml-2 font-normal text-emerald-600">已绑定 {bindings.phone}</span> : ''}
                </label>
                <div className="flex gap-2">
                  <input
                    type="tel"
                    value={bindPhoneNum}
                    onChange={(e) => setBindPhoneNum(e.target.value)}
                    placeholder="11 位手机号"
                    className="flex-1 min-w-0 px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                  />
                  <button
                    type="button"
                    disabled={sendingCode || (codeCooldown.seconds > 0 && codeCooldown.target === bindPhoneNum)}
                    onClick={() => handleSendBindCode(bindPhoneNum, 'bind_phone')}
                    className="px-3.5 py-2.5 whitespace-nowrap bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-xl text-xs font-bold hover:bg-indigo-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {codeCooldown.seconds > 0 && codeCooldown.target === bindPhoneNum ? `${codeCooldown.seconds}s 后重发` : '获取验证码'}
                  </button>
                </div>
              </div>
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">短信验证码</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={bindPhoneCode}
                  onChange={(e) => setBindPhoneCode(e.target.value)}
                  placeholder="6 位数字验证码"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm tracking-widest focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>
              <button
                type="submit"
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all"
              >
                绑定手机号
              </button>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
            <h3 className="text-lg font-bold text-slate-900">修改登录密码</h3>
            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">当前原密码 *</label>
                <input
                  type="password"
                  required
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="请输入当前密码"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">新密码 *</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="至少6位新密码"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">确认新密码 *</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="再次输入新密码"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={changingPass}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all disabled:opacity-50"
              >
                {changingPass ? '正在更新...' : '更新密码'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab 3: My Published Items */}
      {activeTab === 'my_items' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">我发布的闲置宝贝 ({myItems.length})</h3>
            <Link
              to="/market/publish"
              className="px-4 py-2 bg-indigo-600 text-white text-xs font-bold rounded-xl"
            >
              + 发布新闲置
            </Link>
          </div>

          {myItems.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 text-slate-400 text-xs">
              您尚未发布任何二手闲置物品
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {myItems.map((item) => (
                <div
                  key={item.id}
                  className="p-4 bg-white rounded-3xl border border-slate-200 flex gap-3 items-center"
                >
                  <img
                    src={item.images?.[0]?.object_key || 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=150'}
                    alt="item"
                    className="w-16 h-16 rounded-xl object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-xs text-slate-900 truncate">{item.title}</h4>
                    <p className="text-xs font-bold text-indigo-600 mt-0.5">¥{formatPrice(item.price)}</p>
                    <Link
                      to={`/market/${item.id}`}
                      className="text-[11px] text-indigo-600 hover:underline font-semibold mt-1 inline-block"
                    >
                      管理 / 查看详情 &rarr;
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: My Favorites */}
      {activeTab === 'favorites' && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-slate-900">我的心愿与收藏 ({favorites.length})</h3>

          {favorites.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 text-slate-400 text-xs">
              您还没有收藏任何闲置物品
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {favorites.map((item) => (
                <Link
                  key={item.id}
                  to={`/market/${item.id}`}
                  className="p-4 bg-white rounded-3xl border border-slate-200 flex gap-3 items-center hover:border-indigo-300 transition-colors"
                >
                  <img
                    src={item.images?.[0]?.object_key || 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=150'}
                    alt="fav"
                    className="w-16 h-16 rounded-xl object-cover"
                  />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-xs text-slate-900 truncate">{item.title}</h4>
                    <p className="text-xs font-bold text-indigo-600 mt-0.5">¥{formatPrice(item.price)}</p>
                    <span className="text-[10px] text-slate-400">点击进入详情页</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 人机验证弹层：发送绑定验证码前的防刷闸门。
          用哪种由后端 captcha/config 下发决定，两种组件对上层暴露同一接口。 */}
      {captchaOpen && captchaConfig?.provider === 'geetest' && captchaConfig?.geetest_id && (
        <GeetestCaptcha
          captchaId={captchaConfig.geetest_id}
          onSuccess={handleCaptchaPass}
          onClose={() => {
            setCaptchaOpen(false);
            setPendingSend(null);
          }}
        />
      )}
      {captchaOpen && !(captchaConfig?.provider === 'geetest' && captchaConfig?.geetest_id) && (
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

export default UserProfile;
