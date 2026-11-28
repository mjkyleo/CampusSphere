import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, MapPin, CalendarDays, Users, ExternalLink, Loader2, MessageCircle, ShieldAlert } from 'lucide-react';
import { api, formatPrice } from '../services/api.ts';
import { Spinner, Alert, Button, Badge, Card, CardContent } from '../components/ui';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

/**
 * 通用详情页：组队 / 共享资源 / 兼职三模块共用。
 * 数据来自真实 API：/api/teams/{id}、/api/shares/{id}、/api/jobs/{id}。
 */
type Kind = 'team' | 'share' | 'job';

const CONFIG: Record<Kind, { title: string; back: string; fetch: (id: string) => Promise<any> }> = {
  team: { title: '组队详情', back: '/teammates', fetch: (id) => api.teammates.get(id) },
  share: { title: '资源详情', back: '/share', fetch: (id) => api.shares.get(id) },
  job: { title: '岗位详情', back: '/jobs', fetch: (id) => api.jobs.get(id) },
};

const ModuleDetail: React.FC<{ kind: Kind }> = ({ kind }) => {
  const { id } = useParams<{ id: string }>();
  const cfg = CONFIG[kind];
  const [item, setItem] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const { isAuthenticated, openReport } = useAuth();
  const { success, error: toastError } = useToast();

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError('');
    cfg.fetch(id).then((res) => {
      if (res.code === 0 && res.data) setItem(res.data);
      else setError(res.message || '加载失败');
    }).catch((e) => setError(e?.message || '网络异常')).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, kind]);

  const requireLogin = (fn: () => void) => {
    if (!isAuthenticated) { toastError('请先登录'); return; }
    fn();
  };

  const handleApply = async () => {
    if (!item) return;
    setBusy(true);
    try {
      const res = kind === 'job'
        ? await api.jobs.apply(item.id, '我想应聘这个岗位')
        : await api.teammates.apply(item.id, '我想加入队伍，请多关照');
      if (res.code === 0) success(kind === 'job' ? '投递意向已发送' : '加入申请已发送');
      else toastError(res.message || '操作失败');
    } catch { toastError('网络异常'); }
    finally { setBusy(false); }
  };

  const handleAccess = async () => {
    if (!item) return;
    setBusy(true);
    try {
      // 外链资源直接打开用户提供的链接；平台自存文件才走签名下载。
      let url = item.file_url || item.download_url || '';
      if (!url) {
        const res = await api.shares.download(item.id);
        url = res.data?.download_url || '';
      }
      if (!/^https?:\/\//i.test(url)) {
        toastError('该资源暂无可用的外部链接');
        return;
      }
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch { toastError('打开资源失败'); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="py-20 flex justify-center"><Spinner size="lg" label="加载详情" /></div>;
  if (error || !item) return <Alert variant="destructive" title="加载失败">{error || '内容不存在'}</Alert>;

  const isTeam = kind === 'team';
  const isShare = kind === 'share';
  const title = item.title || item.name || '';
  const desc = item.description || '';
  const category = item.category || '';
  const owner = item.owner || item.creator || item.poster || item;
  const ownerName = owner.nickname || owner.username || item.owner_nickname
    || item.creator_nickname || item.creator_name || item.poster_name || '匿名发布者';
  const salaryUnits = ['小时', '天', '月', '次'];
  const salaryText = item.salary_cents != null
    ? `¥${formatPrice(item.salary_cents)} / ${salaryUnits[Number(item.salary_type ?? 1)] || '天'}`
    : '';

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <Link to={cfg.back} className="inline-flex items-center gap-1.5 text-body-2 text-steel hover:text-primary">
        <ArrowLeft className="h-4 w-4" /> 返回{cfg.title.replace('详情', '列表')}
      </Link>

      <Card>
        <CardContent className="space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="default">{category || cfg.title}</Badge>
                {isShare && item.likes != null && <Badge variant="muted">♥ {item.likes}</Badge>}
                {isShare && item.downloads != null && <Badge variant="muted">访问 {item.downloads}</Badge>}
              </div>
              <h1 className="font-display text-heading-1 text-ink">{title}</h1>
              <p className="text-body-2 text-steel">由 {ownerName} 发布</p>
            </div>
            <button
              onClick={() => requireLogin(() => openReport(kind === 'share' ? 'share' : isTeam ? 'user' : 'item', item.id, title))}
              className="p-2 rounded-md text-steel hover:bg-panel hover:text-error"
              aria-label="举报"
              title="举报"
            >
              <ShieldAlert className="h-5 w-5" />
            </button>
          </div>

          <div className="whitespace-pre-wrap text-body-1 text-slate leading-relaxed">
            {desc || '发布者未填写详细说明'}
          </div>

          {/* 模块化信息区 */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
            {isTeam && (
              <>
                <InfoCell icon={<Users className="h-4 w-4" />} label="当前成员" value={`${item.current_members ?? item.member_count ?? 1} / ${item.max_members ?? '不限'}`} />
                {item.required_roles && <InfoCell icon={<BadgeCheck />} label="需要角色" value={item.required_roles} />}
                {item.contact_info && <InfoCell icon={<MessageCircle className="h-4 w-4" />} label="队长联系方式" value={item.contact_info} />}
                {item.status !== undefined && <InfoCell icon={<CalendarDays className="h-4 w-4" />} label="状态" value={item.status === 0 ? '招募中' : '已结束'} />}
              </>
            )}
            {isShare && (
              <>
                <InfoCell icon={<BadgeCheck />} label="资源分类" value={category || '学习资料'} />
                <InfoCell icon={<ExternalLink className="h-4 w-4" />} label="访问次数" value={String(item.downloads ?? 0)} />
                <InfoCell icon={<MessageCircle className="h-4 w-4" />} label="资源来源" value="用户提供的外部链接" />
              </>
            )}
            {!isTeam && !isShare && (
              <>
                {salaryText && <InfoCell icon={<BadgeCheck />} label="薪资" value={salaryText} />}
                {item.company && <InfoCell icon={<BadgeCheck />} label="用工方" value={item.company} />}
                {item.location && <InfoCell icon={<MapPin className="h-4 w-4" />} label="工作地点" value={item.location} />}
                {item.contact && <InfoCell icon={<MessageCircle className="h-4 w-4" />} label="联系方式" value={item.contact} />}
                {item.requirements && <InfoCell icon={<BadgeCheck />} label="任职要求" value={item.requirements} />}
              </>
            )}
          </div>

          {isShare && Array.isArray(item.tags) && item.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {item.tags.map((tag: string) => <Badge key={tag} variant="muted">#{tag}</Badge>)}
            </div>
          )}

          {/* 主操作 */}
          <div className="flex flex-wrap gap-3 pt-2">
            {isShare ? (
              <Button onClick={() => requireLogin(handleAccess)} disabled={busy} className="flex-1 sm:flex-none">
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                <ExternalLink className="h-4 w-4" /> 访问资源链接
              </Button>
            ) : (
              <Button onClick={() => requireLogin(handleApply)} disabled={busy} className="flex-1 sm:flex-none">
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                {isTeam ? '申请加入' : '投递意向'}
              </Button>
            )}
          </div>

          {isShare && (
            <p className="text-caption text-steel">
              资源由用户自行提供外部链接，平台不托管文件，请自行甄别内容有效性。
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

function InfoCell({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="p-3 rounded-md bg-ground border border-hairline space-y-1">
      <div className="flex items-center gap-1.5 text-steel text-caption">{icon}{label}</div>
      <div className="text-body-2 font-medium text-ink break-words">{value || '—'}</div>
    </div>
  );
}

function BadgeCheck() {
  return <Badge variant="muted" className="px-1 py-0">信</Badge>;
}

export const TeamDetail = () => <ModuleDetail kind="team" />;
export const ShareDetail = () => <ModuleDetail kind="share" />;
export const JobDetail = () => <ModuleDetail kind="job" />;
