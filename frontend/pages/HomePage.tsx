import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Sparkles, TrendingUp, Zap, ChevronRight, ArrowRight,
  BookOpen, ShoppingBag, Utensils, Users, MessageSquare,
  Briefcase, Share2, Search, ShieldCheck, Tag
} from 'lucide-react';
import { getSmartCampusInsights, getAiStatus, isCapabilityAvailable } from '../services/aiService.ts';
import { api, formatPrice } from '../services/api.ts';
import { ItemOut, CourseOut, TeamOut, JobOut, ShareOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import AiGreetingCard from '../components/AiGreetingCard.tsx';
import { Board, BoardColumns, BoardRow, DataCell, TextCell, ActionCell } from '../components/ui/index.ts';

const HomePage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [insight, setInsight] = useState<string>('');
  const [aiAvailable, setAiAvailable] = useState(false);
  const [aiLoading, setAiLoading] = useState(true);
  const [items, setItems] = useState<ItemOut[]>([]);
  const [courses, setCourses] = useState<CourseOut[]>([]);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [shares, setShares] = useState<ShareOut[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const topics = ['考试周高效复习技巧', '一食堂今日招牌美食推荐', '大三找实习与竞赛组队策略', '二手闲置避坑与面交安全'];

  useEffect(() => {
    const fetchInsight = async () => {
      try {
        // 能力级 gating（未配置 Key / 能力关闭时不请求、不渲染）
        const status = await getAiStatus();
        const on = isCapabilityAvailable(status, 'insights');
        setAiAvailable(on);
        if (on) {
          const randomTopic = topics[Math.floor(Math.random() * topics.length)];
          const text = await getSmartCampusInsights(randomTopic);
          if (text) setInsight(text);
        }
      } catch (error) {
        console.warn('AI insights fetch failed:', error);
      } finally {
        setAiLoading(false);
      }
    };
    fetchInsight();

    const loadPreviewData = async () => {
      try {
        const itemRes = await api.items.list({ page: 1, page_size: 4 });
        if (itemRes.code === 0 && itemRes.data) setItems(itemRes.data.items || []);
        const crsRes = await api.courses.list('', 1, 3);
        if (crsRes.code === 0 && crsRes.data) setCourses(crsRes.data.items || []);
        const tmRes = await api.teammates.list({ page: 1, page_size: 3 });
        if (tmRes.code === 0 && tmRes.data) setTeams(tmRes.data.items || []);
        const jobRes = await api.jobs.list({ page: 1, page_size: 3 });
        if (jobRes.code === 0 && jobRes.data) setJobs(jobRes.data.items || []);
        const shareRes = await api.shares.list({ page: 1, page_size: 3 });
        if (shareRes.code === 0 && shareRes.data) setShares(shareRes.data.items || []);
      } catch {
        // Fallbacks in mock engine
      }
    };
    loadPreviewData();
  }, []);

  const trendingTags = useMemo(() => {
    const tags: { tag: string; path: string }[] = [];
    const topItems = [...items].sort((a, b) => (b.views || 0) - (a.views || 0)).slice(0, 2);
    topItems.forEach((item) => tags.push({ tag: item.title.slice(0, 18), path: `/market/${item.id}` }));
    const topCourses = [...courses].sort((a, b) => (b.reviews_count || 0) - (a.reviews_count || 0)).slice(0, 2);
    topCourses.forEach((course) => tags.push({ tag: `${course.name} ${course.teacher || ''}`.trim().slice(0, 18), path: `/courses/${course.id}` }));
    teams.slice(0, 1).forEach((team) => tags.push({ tag: team.title.slice(0, 18), path: `/teammates/${team.id}` }));
    const topShares = [...shares].sort((a, b) => (b.downloads || 0) - (a.downloads || 0)).slice(0, 1);
    topShares.forEach((share) => tags.push({ tag: share.title.slice(0, 18), path: `/share/${share.id}` }));
    jobs.slice(0, 1).forEach((job) => tags.push({ tag: job.title.slice(0, 18), path: `/jobs/${job.id}` }));
    if (tags.length === 0) {
      return [
        { tag: '考研数学高分资料', path: '/share' },
        { tag: '数据结构张伟老师', path: '/courses' },
        { tag: '一食堂招牌牛肉拉面', path: '/canteens' },
        { tag: '国赛数学建模3缺1', path: '/teammates' },
        { tag: '图书馆兼职助理', path: '/jobs' },
        { tag: '九号电动车转让', path: '/market' }
      ];
    }
    return tags;
  }, [items, courses, teams, shares, jobs]);

  const quickLinks = [
    { label: '闲置市集', icon: ShoppingBag, path: '/market', desc: '真实面交 · 信用保障' },
    { label: '评课社区', icon: BookOpen, path: '/courses', desc: '选课避坑 · 综合评分' },
    { label: '食堂美食', icon: Utensils, path: '/canteens', desc: '档口菜品 · 口碑点评' },
    { label: '搭子招募', icon: Users, path: '/teammates', desc: '竞赛运动 · 自习同伴' },
    { label: '资源共享', icon: Share2, path: '/share', desc: '考研资料 · 历年期末' },
    { label: '兼职校招', icon: Briefcase, path: '/jobs', desc: '家教助理 · 勤工助学' }
  ];

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    navigate(`/market?keyword=${encodeURIComponent(searchQuery.trim())}`);
  };

  const fmtTime = (s?: string | null) => (s ? s.slice(5, 16).replace('T', ' ') : '—');

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* 查询台 + 问候 + AI 洞察 */}
      <section className="bg-surface border border-hairline rounded-lg p-6 md:p-8">
        <div className="space-y-4 max-w-2xl">
          {!aiLoading && aiAvailable && (
            <span className="mono-label inline-flex items-center gap-2 px-3 py-1 bg-panel rounded">
              <Sparkles className="w-3.5 h-3.5" /> AI 校园智能助手
            </span>
          )}
          <h1 className="font-display text-display-gate font-bold tracking-tight leading-tight text-ink">
            你好，{user?.nickname || '同学'} <span className="inline-block">👋</span>
          </h1>

          {/* 每日问候 · 微采集（可降级到本地模板，主流程永不空白） */}
          <AiGreetingCard />

          <div className="bg-ground border border-hairline rounded-md p-4">
            {aiLoading ? (
              <p className="mono-data text-steel"><span className="animate-pulse">正在加载校园智能洞察...</span></p>
            ) : aiAvailable && insight ? (
              <p className="text-body-1 text-slate leading-relaxed">{insight}</p>
            ) : (
              <p className="text-body-1 text-slate leading-relaxed">欢迎使用校园生活平台，这里可以买卖二手物品、寻找学习搭子、查看食堂美食、分享校园动态。</p>
            )}
          </div>
          <form onSubmit={handleSearchSubmit} className="pt-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-steel w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索闲置数码、复习资料、竞赛队友或选课评价..."
                className="w-full pl-11 pr-4 py-3 bg-surface text-ink placeholder:text-steel rounded-md border border-hairline focus:border-ink focus:ring-2 focus:ring-ink/15 outline-none transition-colors text-body-1"
              />
            </div>
            <button type="submit" className="mono-label px-6 py-3 bg-ink text-surface hover:bg-slate rounded-md transition-colors active:scale-[0.98] shrink-0">
              全站搜索
            </button>
          </form>
        </div>
      </section>

      {/* 区域入口矩阵 */}
      <section className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2 className="font-display text-heading-2 text-ink flex items-center gap-2">
            <Zap className="w-4 h-4" /> 核心功能矩阵
          </h2>
          <span className="mono-label text-steel">涵盖校园日常全周期场景</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {quickLinks.map((link) => (
            <Link
              key={link.label}
              to={link.path}
              className="group bg-surface border border-hairline rounded-md p-4 hover:border-ink transition-colors flex flex-col items-center text-center space-y-2"
            >
              <div className="p-3 bg-panel rounded-md group-hover:bg-ink group-hover:text-surface transition-colors">
                <link.icon className="w-5 h-5" strokeWidth={1.8} />
              </div>
              <div>
                <span className="mono-label text-ink block">{link.label}</span>
                <span className="text-caption text-steel font-normal line-clamp-1">{link.desc}</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* 信息板总览 */}
      <div className="grid lg:grid-cols-12 gap-6">
        {/* 左列 */}
        <div className="lg:col-span-8 space-y-6">
          {/* 最新二手闲置 */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h2 className="font-display text-heading-2 text-ink flex items-center gap-2">
                <ShoppingBag className="w-4 h-4" /> 最新二手闲置
              </h2>
              <Link to="/market" className="mono-label text-slate hover:text-ink flex items-center gap-1">
                查看全部 <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            <Board>
              <BoardColumns cols="74px 1fr 84px 64px" labels={['时间', '物品', '价格', '动作']} />
              {items.map((item, i) => (
                <React.Fragment key={item.id}>
                <BoardRow cols="74px 1fr 84px 64px" changed={i === 0} onClick={() => { void navigate(`/market/${item.id}`); }}>
                  <DataCell>{fmtTime(item.created_at)}</DataCell>
                  <TextCell className="!text-ink !font-semibold">{item.title}</TextCell>
                  <DataCell strong>¥{formatPrice(item.price)}</DataCell>
                  <ActionCell>联系</ActionCell>
                </BoardRow>
                </React.Fragment>
              ))}
            </Board>
          </section>

          {/* 课程 */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h2 className="font-display text-heading-2 text-ink flex items-center gap-2">
                <BookOpen className="w-4 h-4" /> 高分课程
              </h2>
              <Link to="/courses" className="mono-label text-slate hover:text-ink flex items-center gap-1">
                查看全部 <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            <Board>
              <BoardColumns cols="1fr 88px 64px" labels={['课程', '评分', '评价']} />
              {courses.map((course) => (
                <React.Fragment key={course.id}>
                <BoardRow cols="1fr 88px 64px" onClick={() => { void navigate(`/courses/${course.id}`); }}>
                  <TextCell className="!text-ink !font-semibold">
                    {course.name} · {course.teacher}
                  </TextCell>
                  <DataCell strong>{course.rating != null ? course.rating.toFixed(1) : '—'}</DataCell>
                  <DataCell>{course.reviews_count ?? 0}</DataCell>
                </BoardRow>
                </React.Fragment>
              ))}
            </Board>
          </section>
        </div>

        {/* 右列 */}
        <div className="lg:col-span-4 space-y-6">
          {/* 热门搭子 */}
          <section className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h2 className="font-display text-heading-2 text-ink flex items-center gap-2">
                <Users className="w-4 h-4" /> 热门搭子招募
              </h2>
              <Link to="/teammates" className="mono-label text-slate hover:text-ink">更多</Link>
            </div>
            <Board>
              <BoardColumns cols="1fr 96px" labels={['招募', '动作']} />
              {teams.map((t) => (
                <React.Fragment key={t.id}>
                <BoardRow cols="1fr 96px" onClick={() => { void navigate(`/teammates/${t.id}`); }}>
                  <TextCell className="!text-ink !font-semibold">{t.title}</TextCell>
                  <ActionCell>加入</ActionCell>
                </BoardRow>
                </React.Fragment>
              ))}
            </Board>
          </section>

          {/* 校园热搜榜 */}
          <section className="space-y-3">
            <h2 className="font-display text-heading-2 text-ink flex items-center gap-2 px-1">
              <TrendingUp className="w-4 h-4" /> 校园热搜榜
            </h2>
            <div className="bg-surface border border-hairline rounded-lg p-4">
              <div className="flex flex-col gap-1.5">
                {trendingTags.map((item, i) => (
                  <Link
                    key={item.tag + i}
                    to={item.path}
                    className="flex items-center gap-3 py-1.5 px-1 rounded hover:bg-panel transition-colors"
                  >
                    <span className="mono-data !font-semibold text-steel w-5 text-right">{i + 1}</span>
                    <span className="text-body-2 text-slate truncate">{item.tag}</span>
                  </Link>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
