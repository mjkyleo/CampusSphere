import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Sparkles, TrendingUp, Zap, Clock, ChevronRight,
  BookOpen, ShoppingBag, Utensils, Users, MessageSquare,
  Briefcase, Share2, Search, ArrowRight, ShieldCheck, Tag
} from 'lucide-react';
import { getSmartCampusInsights } from '../services/geminiService.ts';
import { api, formatPrice } from '../services/api.ts';
import { ItemOut, CourseOut, TeamOut, JobOut, ShareOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';

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
        // 先检查 AI 功能是否可用
        const statusRes = await api.ai.status();
        if (statusRes.code === 0 && statusRes.data?.available) {
          setAiAvailable(true);
          const randomTopic = topics[Math.floor(Math.random() * topics.length)];
          const res = await api.ai.getInsights(randomTopic);
          if (res.code === 0 && res.data?.text) {
            setInsight(res.data.text);
          }
        }
      } catch (error) {
        console.warn('AI insights fetch failed:', error);
      } finally {
        setAiLoading(false);
      }
    };
    fetchInsight();

    // Fetch dashboard previews from API
    const loadPreviewData = async () => {
      try {
        const itemRes = await api.items.list({ page: 1, page_size: 4 });
        if (itemRes.code === 0 && itemRes.data) {
          setItems(itemRes.data.items || []);
        }
        const crsRes = await api.courses.list('', 1, 3);
        if (crsRes.code === 0 && crsRes.data) {
          setCourses(crsRes.data.items || []);
        }
        const tmRes = await api.teammates.list(1, 3);
        if (tmRes.code === 0 && tmRes.data) {
          setTeams(tmRes.data.items || []);
        }
        const jobRes = await api.jobs.list({ page: 1, page_size: 3 });
        if (jobRes.code === 0 && jobRes.data) {
          setJobs(jobRes.data.items || []);
        }
        const shareRes = await api.shares.list({ page: 1, page_size: 3 });
        if (shareRes.code === 0 && shareRes.data) {
          setShares(shareRes.data.items || []);
        }
      } catch {
        // Fallbacks in mock engine
      }
    };

    loadPreviewData();
  }, []);

  // 校园热搜榜：基于各模块真实数据动态生成
  const trendingTags = useMemo(() => {
    const tags: { tag: string; path: string }[] = [];

    const topItems = [...items]
      .sort((a, b) => (b.views || 0) - (a.views || 0))
      .slice(0, 2);
    topItems.forEach((item) => tags.push({ tag: item.title.slice(0, 18), path: `/market/${item.id}` }));

    const topCourses = [...courses]
      .sort((a, b) => (b.reviews_count || 0) - (a.reviews_count || 0))
      .slice(0, 2);
    topCourses.forEach((course) => tags.push({ tag: `${course.name} ${course.teacher || ''}`.trim().slice(0, 18), path: `/courses/${course.id}` }));

    teams.slice(0, 1).forEach((team) => tags.push({ tag: team.title.slice(0, 18), path: `/teammates/${team.id}` }));

    const topShares = [...shares]
      .sort((a, b) => (b.downloads || 0) - (a.downloads || 0))
      .slice(0, 1);
    topShares.forEach((share) => tags.push({ tag: share.title.slice(0, 18), path: `/share/${share.id}` }));

    jobs.slice(0, 1).forEach((job) => tags.push({ tag: job.title.slice(0, 18), path: `/jobs/${job.id}` }));

    // Fallback presets if backend returns empty
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
    { label: '闲置市集', icon: ShoppingBag, color: 'bg-amber-50 text-amber-600 border-amber-100', path: '/market', desc: '真实面交 信用保障' },
    { label: '评课社区', icon: BookOpen, color: 'bg-blue-50 text-blue-600 border-blue-100', path: '/courses', desc: '选课避坑 综合评分' },
    { label: '食堂美食', icon: Utensils, color: 'bg-rose-50 text-rose-600 border-rose-100', path: '/canteens', desc: '档口菜品 口碑点评' },
    { label: '搭子招募', icon: Users, color: 'bg-emerald-50 text-emerald-600 border-emerald-100', path: '/teammates', desc: '竞赛运动 自习同伴' },
    { label: '资源共享', icon: Share2, color: 'bg-indigo-50 text-indigo-600 border-indigo-100', path: '/share', desc: '考研资料 历年期末' },
    { label: '兼职校招', icon: Briefcase, color: 'bg-violet-50 text-violet-600 border-violet-100', path: '/jobs', desc: '家教助理 勤工助学' }
  ];

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    navigate(`/market?keyword=${encodeURIComponent(searchQuery.trim())}`);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-10 animate-in fade-in duration-500 pb-16">
      {/* Hero Banner with Personalized Greeting and Gemini Smart Insights */}
      <section className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-8 md:p-12 shadow-2xl border border-indigo-900/40">
        <div className="relative z-10 space-y-4 max-w-2xl">
          {!aiLoading && aiAvailable && (
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-xs font-semibold text-indigo-200 border border-white/10">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>AI 校园智能助手</span>
            </div>
          )}

          <h1 className="text-3xl md:text-5xl font-black tracking-tight leading-tight">
            你好，{user?.nickname || '同学'} <span className="inline-block animate-pulse">👋</span>
          </h1>

          {aiLoading ? (
            <p className="text-base md:text-lg text-slate-300 leading-relaxed font-normal bg-white/5 p-4 rounded-2xl border border-white/10 backdrop-blur-xs">
              <span className="animate-pulse">正在加载校园智能洞察...</span>
            </p>
          ) : aiAvailable && insight ? (
            <p className="text-base md:text-lg text-slate-300 leading-relaxed font-normal bg-white/5 p-4 rounded-2xl border border-white/10 backdrop-blur-xs">
              {insight}
            </p>
          ) : (
            <p className="text-base md:text-lg text-slate-300 leading-relaxed font-normal bg-white/5 p-4 rounded-2xl border border-white/10 backdrop-blur-xs">
              欢迎使用校园生活平台，这里可以买卖二手物品、寻找学习搭子、查看食堂美食、分享校园动态。
            </p>
          )}

          {/* Unified Global Search Bar */}
          <form onSubmit={handleSearchSubmit} className="pt-2 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索闲置数码、复习资料、竞赛队友或选课评价..."
                className="w-full pl-12 pr-4 py-3.5 bg-white/95 text-slate-900 placeholder:text-slate-400 rounded-2xl text-sm font-medium focus:bg-white focus:ring-4 focus:ring-indigo-500/30 outline-none transition-all"
              />
            </div>
            <button
              type="submit"
              className="px-6 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold text-sm shadow-lg shadow-indigo-500/30 transition-all shrink-0 active:scale-95"
            >
              全站搜索
            </button>
          </form>
        </div>

        {/* Ambient glows */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
        <div className="absolute bottom-0 right-1/3 w-64 h-64 bg-violet-500/20 rounded-full blur-3xl pointer-events-none"></div>
      </section>

      {/* Quick Services Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-600" />
            核心功能矩阵
          </h2>
          <span className="text-xs text-slate-400 font-medium">涵盖校园日常全周期场景</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {quickLinks.map((link) => (
            <Link
              key={link.label}
              to={link.path}
              className="group p-4 bg-white rounded-3xl border border-slate-200/80 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all flex flex-col items-center text-center space-y-2"
            >
              <div className={`p-3.5 rounded-2xl border transition-all group-hover:scale-110 group-active:scale-95 ${link.color}`}>
                <link.icon className="w-6 h-6" />
              </div>
              <div>
                <span className="font-bold text-slate-800 text-sm block group-hover:text-indigo-600 transition-colors">
                  {link.label}
                </span>
                <span className="text-[11px] text-slate-400 font-normal line-clamp-1">
                  {link.desc}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Main Content Sections: Second-hand Market + Teammates & Courses */}
      <div className="grid lg:grid-cols-12 gap-8">
        {/* Left Column: Recent Items (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-amber-500" />
              最新二手闲置
            </h2>
            <Link to="/market" className="text-indigo-600 text-xs font-bold hover:underline flex items-center gap-1">
              查看全部 <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {items.map((item) => (
              <Link
                key={item.id}
                to={`/market/${item.id}`}
                className="group bg-white rounded-3xl overflow-hidden border border-slate-200/80 hover:border-indigo-200 hover:shadow-lg transition-all flex flex-col"
              >
                <div className="relative aspect-[16/10] overflow-hidden bg-slate-100">
                  <img
                    src={item.images?.[0]?.object_key || 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600'}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute top-2.5 right-2.5 px-2 py-0.5 bg-black/60 backdrop-blur-md rounded-lg text-[10px] text-white font-medium">
                    {item.category}
                  </div>
                </div>

                <div className="p-4 space-y-2 flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm line-clamp-1 group-hover:text-indigo-600 transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">
                      {item.description}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <div className="flex items-baseline gap-0.5 text-indigo-600">
                      <span className="text-xs font-bold">¥</span>
                      <span className="text-xl font-black">{formatPrice(item.price)}</span>
                    </div>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      {item.owner_nickname || '校友发布'}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Banner Promo for Community Sharing */}
          <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-3xl p-6 text-white flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl shadow-indigo-100">
            <div className="space-y-1 text-center sm:text-left">
              <h3 className="text-lg font-bold">有闲置书本或数码想转给学弟学妹？</h3>
              <p className="text-xs text-indigo-100">支持一键拍照上传、发布自动分类与即时私信撮合。</p>
            </div>
            <Link
              to="/market/publish"
              className="px-5 py-2.5 bg-white text-indigo-700 hover:bg-slate-50 rounded-xl text-xs font-bold shadow-sm transition-transform active:scale-95 shrink-0"
            >
              免费发布物品
            </Link>
          </div>
        </div>

        {/* Right Column: Hot Teams & Top Rated Courses (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Active Teams */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Users className="w-4.5 h-4.5 text-emerald-600" />
                热门搭子招募
              </h2>
              <Link to="/teammates" className="text-indigo-600 text-xs font-bold hover:underline">
                更多
              </Link>
            </div>

            <div className="space-y-3">
              {teams.map((t) => (
                <div
                  key={t.id}
                  className="p-4 bg-white rounded-2xl border border-slate-200/80 hover:border-emerald-200 transition-all space-y-2"
                >
                  <div className="flex justify-between items-start gap-2">
                    <h4 className="font-bold text-slate-800 text-xs line-clamp-1">{t.title}</h4>
                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded shrink-0">
                      {t.category || '招募中'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                    {t.description}
                  </p>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                    <span>需求: {t.required_roles}</span>
                    <Link to="/teammates" className="text-emerald-600 font-bold hover:underline">
                      加入 &rarr;
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Hot Topic Tags */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 px-1">
              <TrendingUp className="w-4.5 h-4.5 text-indigo-600" />
              校园热搜榜
            </h2>
            <div className="bg-white p-5 rounded-3xl border border-slate-200/80 flex flex-wrap gap-2 shadow-xs">
              {trendingTags.map((item) => (
                <Link
                  key={item.tag}
                  to={item.path}
                  className="px-3 py-1.5 bg-slate-50 hover:bg-indigo-50 hover:text-indigo-600 text-slate-600 text-xs font-semibold rounded-xl border border-slate-100 hover:border-indigo-200 transition-colors"
                >
                  #{item.tag}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
