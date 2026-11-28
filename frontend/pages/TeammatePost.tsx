import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Plus, Tag } from 'lucide-react';
import { api } from '../services/api.ts';
import { TeamOut, TeamStatus } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

// 兜底分类：后端不可达时使用（真实值由 /api/teams/categories 下发）
const FALLBACK_CATEGORIES = ['学术竞赛', '考研考公', '运动健身', '游戏开黑', '旅行逛街', '期末自习', '其他'];

const TeammatePost: React.FC = () => {
  const navigate = useNavigate();
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

  const inputCls =
    'w-full px-3.5 py-2.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft focus:ring-2 focus:ring-ink/10 outline-none transition-colors';

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="mono-label text-zone-teammate tracking-mono mb-1">TEAM · 组队协作</div>
          <h1 className="text-heading-1 text-ink tracking-tight">找搭子 & 竞赛组队</h1>
          <p className="text-body-2 text-steel mt-0.5">
            寻找同频队友，覆盖数模国赛、考研自习、球类运动、兴趣探索
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors active:scale-95 shrink-0"
        >
          <Plus className="w-4 h-4" />
          发布招募帖
        </button>
      </div>

      {/* Category Pills */}
      <div className="bg-surface p-3 rounded-lg border border-hairline shadow-surface flex gap-2 overflow-x-auto no-scrollbar">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCat(cat)}
            className={`whitespace-nowrap px-3.5 py-1.5 mono-label uppercase tracking-mono rounded-lg transition-colors ${
              selectedCat === cat
                ? 'bg-zone-teammate text-surface'
                : 'bg-panel text-steel hover:text-ink'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Teams Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div key={n} className="soft-card animate-pulse space-y-4">
              <div className="h-5 bg-panel rounded w-3/4"></div>
              <div className="h-16 bg-panel rounded"></div>
            </div>
          ))}
        </div>
      ) : teams.length === 0 ? (
        <div className="bg-surface rounded-lg p-16 text-center border border-hairline space-y-4">
          <Users className="w-12 h-12 text-steel mx-auto" />
          <h3 className="text-heading-3 text-ink">暂无该类别的搭子招募</h3>
          <p className="text-body-2 text-steel">做第一个发起组队邀请的队长吧！</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-primary text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono hover:bg-primary-hover transition-colors"
          >
            立即发布招募
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {teams.map((team) => {
            const isOwner = user?.id === team.creator_id;
            const isOpen = team.status === TeamStatus.Open || team.status === undefined;
            return (
              <div
                key={team.id}
                role="link"
                tabIndex={0}
                onClick={() => navigate(`/teammates/${team.id}`)}
                onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/teammates/${team.id}`); }}
                className="group soft-card hover:border-zone-teammate hover:shadow-md-4 cursor-pointer transition-all flex flex-col justify-between space-y-5"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="px-2 py-0.5 bg-zone-teammate/10 text-zone-teammate text-xs font-mono font-bold rounded-lg tracking-mono">
                      {team.category || '组队招募'}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded-lg tracking-mono ${
                        isOpen ? 'bg-zone-teammate/10 text-zone-teammate' : 'bg-panel text-steel'
                      }`}
                    >
                      {isOpen ? '招募进行中' : '已招满/已结束'}
                    </span>
                  </div>

                  <h3 className="text-heading-3 text-ink leading-snug group-hover:text-zone-teammate transition-colors">
                    {team.title}
                  </h3>

                  <p className="text-body-2 text-steel leading-relaxed bg-panel/40 p-3.5 rounded-lg border border-hairline">
                    {team.description}
                  </p>

                  <div className="space-y-1.5 pt-1 text-body-2 text-steel">
                    <div className="flex items-center gap-1.5">
                      <Tag className="w-3.5 h-3.5 text-zone-teammate shrink-0" />
                      <span>需求角色：<strong className="text-slate">{team.required_roles}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-steel shrink-0" />
                      <span>目标人数：{team.current_members || 1} / {team.max_members || 3} 人</span>
                    </div>
                    {team.contact_info && (
                      <div className="text-caption text-zone-teammate bg-zone-teammate/5 px-2.5 py-1 rounded-lg border border-zone-teammate/20 font-mono">
                        队长联系方式: {team.contact_info}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-hairline flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-panel flex items-center justify-center text-xs font-bold text-zone-teammate">
                      {team.creator_nickname?.charAt(0) || '队'}
                    </div>
                    <span className="text-body-2 font-bold text-ink">{team.creator_nickname || '队长'}</span>
                  </div>

                  {isOwner ? (
                    <div className="flex gap-1.5">
                      {isOpen && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCloseRecruit(team.id); }}
                          className="px-3 py-1.5 bg-panel hover:bg-primary-hover/10 text-slate text-body-2 font-bold rounded-lg mono-label uppercase tracking-mono transition-colors"
                        >
                          结束招募
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); setApplyingTeamId(team.id); }}
                      disabled={!isOpen}
                      className="px-4 py-2 bg-primary hover:bg-primary-hover disabled:bg-panel disabled:text-steel text-surface rounded-lg mono-label uppercase tracking-mono transition-colors active:scale-95"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate/70">
          <div className="bg-surface rounded-lg max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-elevate border border-hairline max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-heading-3 text-ink">发布搭子与组队招募</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-steel hover:text-ink text-xl font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">招募标题 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 2026全国大学生数学建模竞赛 3缺1 (求论文手/代码手)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block mono-label text-steel tracking-mono">分类标签 *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className={inputCls}
                  >
                    {categories.filter((c) => c !== '全部').map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="block mono-label text-steel tracking-mono">队伍目标总人数</label>
                  <input
                    type="number"
                    min="2"
                    max="10"
                    value={maxMembers}
                    onChange={(e) => setMaxMembers(Number(e.target.value))}
                    className={inputCls + ' font-mono'}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">需求技能 / 角色要求 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 擅长 LaTeX 排版 / Python 机器学习建模 / 考研政治背诵打卡"
                  value={requiredRoles}
                  onChange={(e) => setRequiredRoles(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">详细招募介绍 *</label>
                <textarea
                  rows={4}
                  required
                  placeholder="说明目前进度、预期目标、时间投入要求以及对队友的期望..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-3.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft outline-none transition-colors"
                />
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">队长联系方式 (微信/QQ/邮箱)</label>
                <input
                  type="text"
                  placeholder="例如: WeChat: study_partner_99"
                  value={contactInfo}
                  onChange={(e) => setContactInfo(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 border border-hairline text-steel rounded-lg text-body-2 font-semibold mono-label uppercase tracking-mono hover:bg-panel transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-3 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg text-body-2 font-bold mono-label uppercase tracking-mono disabled:opacity-50 transition-colors"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate/70">
          <div className="bg-surface rounded-lg max-w-md w-full p-6 space-y-4 shadow-elevate border border-hairline">
            <h3 className="text-heading-3 text-ink">向队长申请入队</h3>
            <p className="text-body-2 text-steel">简要介绍自己的特长、相关经验或时间安排：</p>
            <textarea
              rows={4}
              required
              placeholder="例如：我是软件工程大三学生，熟练掌握 Python 和数据清洗，有美赛打比赛经验，本学期时间充裕！"
              value={applyMessage}
              onChange={(e) => setApplyMessage(e.target.value)}
              className="w-full p-3.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft outline-none transition-colors"
            />
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setApplyingTeamId(null)}
                className="flex-1 py-2.5 border border-hairline text-steel rounded-lg text-body-2 font-semibold mono-label uppercase tracking-mono hover:bg-panel transition-colors"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => handleApply(applyingTeamId)}
                className="flex-1 py-2.5 bg-primary text-surface shadow-soft rounded-lg text-body-2 font-bold mono-label uppercase tracking-mono hover:bg-primary-hover transition-colors"
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
