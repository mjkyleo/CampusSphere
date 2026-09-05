import React, { useState, useEffect } from 'react';
import {
  Users, Plus, Search, MessageSquare, Send, CheckCircle2,
  Sparkles, Calendar, User, Tag, Lock, Trash2, ArrowRight
} from 'lucide-react';
import { api } from '../services/api.ts';
import { TeamOut, TeamStatus } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

// 兜底分类：后端不可达时使用（真实值由 /api/teams/categories 下发）
const FALLBACK_CATEGORIES = ['学术竞赛', '考研考公', '运动健身', '游戏开黑', '旅行逛街', '期末自习', '其他'];

const TeammatePost: React.FC = () => {
  const { user } = useAuth();
  const { success, error, info } = useToast();

  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [categories, setCategories] = useState<string[]>(['全部', ...FALLBACK_CATEGORIES]);
  const [selectedCat, setSelectedCat] = useState('全部');
  const [loading, setLoading] = useState(true);

  // New post modal / collapse
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState(FALLBACK_CATEGORIES[0]);
  const [description, setDescription] = useState('');
  const [requiredRoles, setRequiredRoles] = useState('');
  const [contactInfo, setContactInfo] = useState('');
  const [maxMembers, setMaxMembers] = useState(3);
  const [submitting, setSubmitting] = useState(false);

  // Apply dialog state
  const [applyingTeamId, setApplyingTeamId] = useState<string | null>(null);
  const [applyMessage, setApplyMessage] = useState('');

  // 动态拉取搭子分类（后台可配置，含 school.yaml 兜底）；失败则用前端兜底常量
  useEffect(() => {
    (async () => {
      try {
        const res = await api.teammates.categories();
        if (res.code === 0 && res.data?.categories?.length) {
          setCategories(['全部', ...res.data.categories]);
          setCategory(res.data.categories[0]);
        }
      } catch {
        // 保留兜底分类
      }
    })();
  }, []);

  const fetchTeams = async () => {
    setLoading(true);
    try {
      const res = await api.teammates.list({
        category: selectedCat === '全部' ? undefined : selectedCat,
        page: 1,
        page_size: 30,
      });
      if (res.code === 0 && res.data) {
        setTeams(res.data.items || []);
      }
    } catch {
      // Mock fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, [selectedCat]);

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim() || !requiredRoles.trim()) {
      error('请完整填写招募信息');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.teammates.create({
        title: title.trim(),
        category,
        description: description.trim(),
        required_roles: requiredRoles.trim(),
        contact_info: contactInfo.trim() || undefined,
        max_members: Number(maxMembers)
      });

      if (res.code === 0) {
        success('招募帖发布成功！');
        setShowCreateModal(false);
        setTitle('');
        setDescription('');
        setRequiredRoles('');
        setContactInfo('');
        fetchTeams();
      } else {
        error(res.message || '发布失败');
      }
    } catch {
      error('发布异常');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApply = async (teamId: string) => {
    if (!applyMessage.trim()) {
      error('请填写加入自荐理由或优势特长');
      return;
    }
    try {
      const res = await api.teammates.apply(teamId, applyMessage.trim());
      if (res.code === 0) {
        success('申请已发送给队长！请关注私信消息通知');
        setApplyingTeamId(null);
        setApplyMessage('');
      } else {
        error(res.message || '申请失败');
      }
    } catch {
      error('申请异常');
    }
  };

  const handleCloseRecruit = async (teamId: string) => {
    const res = await api.teammates.close(teamId);
    if (res.code === 0) {
      success('已结束招募');
      fetchTeams();
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">找搭子 & 竞赛组队</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            寻找同频队友，覆盖数模国赛、考研自习、球类运动、兴趣探索
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold shadow-lg shadow-emerald-200 transition-all active:scale-95 shrink-0"
        >
          <Plus className="w-5 h-5" />
          发布招募帖
        </button>
      </div>

      {/* Category Pills */}
      <div className="bg-white p-3 rounded-3xl border border-slate-200 shadow-xs flex gap-2 overflow-x-auto no-scrollbar">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCat(cat)}
            className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              selectedCat === cat
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Teams Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-6 border border-slate-200 animate-pulse space-y-4">
              <div className="h-5 bg-slate-200 rounded w-3/4"></div>
              <div className="h-16 bg-slate-100 rounded"></div>
            </div>
          ))}
        </div>
      ) : teams.length === 0 ? (
        <div className="bg-white rounded-3xl p-16 text-center border border-slate-200 space-y-4">
          <Users className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-bold text-slate-700">暂无该类别的搭子招募</h3>
          <p className="text-xs text-slate-400">做第一个发起组队邀请的队长吧！</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold"
          >
            立即发布招募
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams.map((team) => {
            const isOwner = user?.id === team.creator_id;
            const isOpen = team.status === TeamStatus.Open || team.status === undefined;
            return (
              <div
                key={team.id}
                className="group bg-white rounded-3xl p-6 border border-slate-200 hover:border-emerald-300 hover:shadow-xl hover:shadow-emerald-500/5 transition-all flex flex-col justify-between space-y-5"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="px-2.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-md">
                      {team.category || '组队招募'}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                        isOpen ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {isOpen ? '招募进行中' : '已招满/已结束'}
                    </span>
                  </div>

                  <h3 className="text-lg font-black text-slate-900 leading-snug group-hover:text-emerald-700 transition-colors">
                    {team.title}
                  </h3>

                  <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3.5 rounded-2xl border border-slate-100">
                    {team.description}
                  </p>

                  <div className="space-y-1.5 pt-1 text-xs text-slate-600">
                    <div className="flex items-center gap-1.5">
                      <Tag className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>需求角色：<strong>{team.required_roles}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>目标人数：{team.current_members || 1} / {team.max_members || 3} 人</span>
                    </div>
                    {team.contact_info && (
                      <div className="text-[11px] text-slate-500 bg-emerald-50/50 px-2.5 py-1 rounded-lg">
                        队长联系方式: {team.contact_info}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-700">
                      {team.creator_nickname?.charAt(0) || '队'}
                    </div>
                    <span className="text-xs font-bold text-slate-700">{team.creator_nickname || '队长'}</span>
                  </div>

                  {isOwner ? (
                    <div className="flex gap-1.5">
                      {isOpen && (
                        <button
                          onClick={() => handleCloseRecruit(team.id)}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-colors"
                        >
                          结束招募
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={() => setApplyingTeamId(team.id)}
                      disabled={!isOpen}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-100 transition-all active:scale-95"
                    >
                      申请加入
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Team Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-slate-900">发布搭子与组队招募</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600 text-xl font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">招募标题 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 2026全国大学生数学建模竞赛 3缺1 (求论文手/代码手)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">分类标签 *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
                  >
                    {categories.filter((c) => c !== '全部').map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">队伍目标总人数</label>
                  <input
                    type="number"
                    min="2"
                    max="10"
                    value={maxMembers}
                    onChange={(e) => setMaxMembers(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">需求技能 / 角色要求 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 擅长 LaTeX 排版 / Python 机器学习建模 / 考研政治背诵打卡"
                  value={requiredRoles}
                  onChange={(e) => setRequiredRoles(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">详细招募介绍 *</label>
                <textarea
                  rows={4}
                  required
                  placeholder="说明目前进度、预期目标、时间投入要求以及对队友的期望..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">队长联系方式 (微信/QQ/邮箱)</label>
                <input
                  type="text"
                  placeholder="例如: WeChat: study_partner_99"
                  value={contactInfo}
                  onChange={(e) => setContactInfo(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-bold shadow-md shadow-emerald-100 disabled:opacity-50"
                >
                  {submitting ? '发布中...' : '确认发布'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Apply Modal */}
      {applyingTeamId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-100">
            <h3 className="text-lg font-bold text-slate-900">向队长申请入队</h3>
            <p className="text-xs text-slate-500">简要介绍自己的特长、相关经验或时间安排：</p>
            <textarea
              rows={4}
              required
              placeholder="例如：我是软件工程大三学生，熟练掌握 Python 和数据清洗，有美赛打比赛经验，本学期时间充裕！"
              value={applyMessage}
              onChange={(e) => setApplyMessage(e.target.value)}
              className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-emerald-600 outline-none"
            />
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setApplyingTeamId(null)}
                className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => handleApply(applyingTeamId)}
                className="flex-1 py-2.5 bg-emerald-600 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-100"
              >
                发送入队申请
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeammatePost;
