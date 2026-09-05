import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Star, MapPin, Clock, ChevronRight, Search, Coffee, Building2, LayoutGrid } from 'lucide-react';
import { api } from '../services/api.ts';
import { CanteenOut, CanteenConfig } from '../types.ts';

// 兜底配置：后端不可达时使用（与 school.yaml canteen 段对齐）
const FALLBACK_CONFIG: CanteenConfig = {
  campuses: ['文理学部', '工学部', '信息学部', '医学部'],
  zones: {
    文理学部: ['梅园', '桂园', '枫园'],
    工学部: ['湖滨', '工学部', '田园'],
    信息学部: ['信息学部', '星园'],
    医学部: ['医学部'],
  },
  types: ['学生大伙食堂', '风味食堂', '教工食堂'],
  semesters: ['2026-2027-1', '2026-2027-2'],
  current_semester: '2026-2027-1',
};

const CanteenCard: React.FC<{ canteen: CanteenOut }> = ({ canteen }) => (
  <div className="group bg-white rounded-3xl overflow-hidden border border-slate-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all flex flex-col justify-between">
    <div className="p-6 sm:p-7 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="px-2.5 py-0.5 bg-rose-50 text-rose-700 text-xs font-bold rounded-md">
              {canteen.opening_hours || '06:30 - 22:00'}
            </span>
            {canteen.canteen_type && (
              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 text-[11px] font-bold rounded-md">
                {canteen.canteen_type}
              </span>
            )}
            {canteen.floor && (
              <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[11px] font-bold rounded-md">
                {canteen.floor}
              </span>
            )}
          </div>
          <h3 className="text-2xl font-black text-slate-900 mt-2 group-hover:text-indigo-600 transition-colors">
            {canteen.name}
          </h3>
          {(canteen.zone || canteen.campus) && (
            <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-400">
              {canteen.campus && <Building2 className="w-3.5 h-3.5" />}
              <span>{[canteen.campus, canteen.zone].filter(Boolean).join(' · ')}</span>
            </div>
          )}
        </div>
        <div className="p-3 bg-amber-50 rounded-2xl border border-amber-200/60 flex items-center gap-1.5 text-amber-700 text-sm font-black shrink-0">
          <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
          <span>{canteen.rating ? Number(canteen.rating).toFixed(1) : '4.7'}</span>
        </div>
      </div>

      {canteen.features && canteen.features.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {canteen.features.map((f) => (
            <span key={f} className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] font-bold rounded-md">
              {f}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-2 text-xs text-slate-600">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
          <span>{canteen.location || '主校区核心餐饮区'}</span>
        </div>
        <div className="flex items-center gap-2">
          <Coffee className="w-4 h-4 text-slate-400 shrink-0" />
          <span>收录档口：{canteen.stalls?.length || 0} 个风味窗口</span>
        </div>
        {canteen.popular_dishes && canteen.popular_dishes.length > 0 && (
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="truncate">招牌：{canteen.popular_dishes.join('、')}</span>
          </div>
        )}
      </div>
    </div>

    <div className="p-6 pt-0">
      <Link
        to={`/canteens/${canteen.id}`}
        className="w-full py-3.5 bg-indigo-50 hover:bg-indigo-600 text-indigo-600 hover:text-white rounded-2xl text-xs font-bold transition-all flex items-center justify-center gap-1.5"
      >
        进入食堂浏览档口与点评 <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  </div>
);

const CanteenList: React.FC = () => {
  const [config, setConfig] = useState<CanteenConfig>(FALLBACK_CONFIG);
  const [canteens, setCanteens] = useState<CanteenOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const [selectedCampus, setSelectedCampus] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedSemester, setSelectedSemester] = useState<string>('');

  // 配置（学部/餐饮区/类型/学期枚举）由后台下发
  useEffect(() => {
    (async () => {
      try {
        const res = await api.canteens.configs();
        if (res.code === 0 && res.data) {
          setConfig(res.data);
          if (res.data.current_semester) setSelectedSemester(res.data.current_semester);
        }
      } catch {
        // 保留兜底配置
      }
    })();
  }, []);

  const fetchCanteens = async () => {
    setLoading(true);
    try {
      const res = await api.canteens.list({
        campus: selectedCampus || undefined,
        canteen_type: selectedType || undefined,
        semester: selectedSemester || undefined,
      });
      if (res.code === 0 && res.data) setCanteens(res.data);
    } catch {
      // Handled in mock engine
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCanteens();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCampus, selectedType, selectedSemester]);

  const keyword = search.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      keyword
        ? canteens.filter(
            (c) =>
              c.name.toLowerCase().includes(keyword) ||
              (c.location || '').toLowerCase().includes(keyword) ||
              (c.popular_dishes || []).some((d) => d.toLowerCase().includes(keyword))
          )
        : canteens,
    [canteens, keyword]
  );

  // 按餐饮区分组（选中具体学部时，按该学部的餐饮区聚合）
  const zoneGroups = useMemo(() => {
    const zones = selectedCampus ? config.zones[selectedCampus] || [] : [];
    const map = new Map<string, CanteenOut[]>();
    zones.forEach((z) => map.set(z, []));
    const ungrouped: CanteenOut[] = [];
    filtered.forEach((c) => {
      const z = c.zone || '';
      if (map.has(z)) map.get(z)!.push(c);
      else ungrouped.push(c);
    });
    return {
      groups: Array.from(map.entries()).filter(([, v]) => v.length > 0),
      ungrouped,
    };
  }, [filtered, config, selectedCampus]);

  // 未选学部时按学部分组展示
  const campusGroups = useMemo(() => {
    if (selectedCampus) return [];
    const map = new Map<string, CanteenOut[]>();
    config.campuses.forEach((cp) => map.set(cp, []));
    const ungrouped: CanteenOut[] = [];
    filtered.forEach((c) => {
      const cp = c.campus || '';
      if (map.has(cp)) map.get(cp)!.push(c);
      else ungrouped.push(c);
    });
    return Array.from(map.entries()).filter(([, v]) => v.length > 0).concat(ungrouped.length ? [['其他', ungrouped]] : []);
  }, [filtered, config, selectedCampus]);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">校园食堂与美食档口</h1>
        <p className="text-slate-500 text-sm mt-0.5">
          按学部 · 餐饮区 · 类型多维度筛选，探索招牌热销菜品、口味评分与卫生评价
        </p>
      </div>

      {/* 学部 Tab */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        <CampusTab label="全部学部" active={selectedCampus === ''} onClick={() => setSelectedCampus('')} />
        {config.campuses.map((cp) => (
          <CampusTab key={cp} label={cp} active={selectedCampus === cp} onClick={() => setSelectedCampus(cp)} />
        ))}
      </div>

      {/* 类型 chips + 学期 + 搜索 */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-400 mr-1">类型</span>
          <FilterChip label="全部" active={selectedType === ''} onClick={() => setSelectedType('')} />
          {config.types.map((t) => (
            <FilterChip key={t} label={t} active={selectedType === t} onClick={() => setSelectedType(t)} />
          ))}
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索食堂名称、校区位置或热门美食..."
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {config.semesters.length > 0 && (
            <select
              value={selectedSemester}
              onChange={(e) => setSelectedSemester(e.target.value)}
              className="px-3.5 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
            >
              <option value="">全部学期</option>
              {config.semesters.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-6 border border-slate-200 animate-pulse space-y-4">
              <div className="h-6 bg-slate-200 rounded w-1/2"></div>
              <div className="h-4 bg-slate-200 rounded w-3/4"></div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <LayoutGrid className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p>该筛选条件下暂无食堂</p>
        </div>
      ) : (
        <div className="space-y-8">
          {selectedCampus
            ? zoneGroups.groups.map(([zone, list]) => (
                <section key={zone}>
                  <h2 className="text-lg font-black text-slate-800 mb-3 flex items-center gap-2">
                    <Coffee className="w-5 h-5 text-indigo-500" /> {zone}
                    <span className="text-xs font-normal text-slate-400">{list.length} 个食堂</span>
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {list.map((c) => <CanteenCard key={c.id} canteen={c} />)}
                  </div>
                </section>
              ))
            : campusGroups.map(([campus, list]) => (
                <section key={campus}>
                  <h2 className="text-lg font-black text-slate-800 mb-3 flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-indigo-500" /> {campus}
                    <span className="text-xs font-normal text-slate-400">{list.length} 个食堂</span>
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {list.map((c) => <CanteenCard key={c.id} canteen={c} />)}
                  </div>
                </section>
              ))}
          {selectedCampus && zoneGroups.ungrouped.length > 0 && (
            <section>
              <h2 className="text-lg font-black text-slate-800 mb-3">其他</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {zoneGroups.ungrouped.map((c) => <CanteenCard key={c.id} canteen={c} />)}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
};

const CampusTab: React.FC<{ label: string; active: boolean; onClick: () => void }> = ({ label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 rounded-full text-sm font-bold whitespace-nowrap transition-all ${
      active ? 'bg-indigo-600 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-600 hover:border-indigo-300'
    }`}
  >
    {label}
  </button>
);

const FilterChip: React.FC<{ label: string; active: boolean; onClick: () => void }> = ({ label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
      active ? 'bg-indigo-600 text-white' : 'bg-slate-50 border border-slate-200 text-slate-600 hover:border-indigo-300'
    }`}
  >
    {label}
  </button>
);

export default CanteenList;
