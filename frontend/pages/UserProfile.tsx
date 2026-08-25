import React, { useState, useEffect } from 'react';
import {
  User, Shield, Mail, Phone, Lock, Edit3, MessageCircle,
  MessageSquare, ShoppingBag, Heart, CheckCircle2, AlertCircle,
  LogOut, Sparkles, Building, Bookmark, KeyRound, Link as LinkIcon
} from 'lucide-react';
import { api, formatPrice } from '../services/api.ts';
import { UserProfileOut, BindingsOut, ItemOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { Link, useNavigate } from 'react-router-dom';

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

  // My items & favorites
  const [myItems, setMyItems] = useState<ItemOut[]>([]);
  const [favorites, setFavorites] = useState<ItemOut[]>([]);

  useEffect(() => {
    if (user) {
      setNickname(user.nickname || '');
      setAvatar(user.avatar || '');
      setBio(user.bio || '');
      setCampus(user.campus || '主校区');
      setMajor(user.major || '计算机科学与技术');
      setGrade(user.grade || '2023级');
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

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const ok = await updateProfile({
      nickname: nickname.trim(),
      avatar: avatar.trim(),
      bio: bio.trim(),
      campus: campus.trim(),
      major: major.trim(),
      grade: grade.trim(),
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
                <label className="block text-xs font-bold text-slate-700">入学年级</label>
                <input
                  type="text"
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                  placeholder="例如: 2023级 本科"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
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
    </div>
  );
};

export default UserProfile;
