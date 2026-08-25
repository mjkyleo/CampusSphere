import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Utensils, Star, MapPin, Clock, ChevronRight, Search, Sparkles, Coffee } from 'lucide-react';
import { api } from '../services/api.ts';
import { CanteenOut } from '../types.ts';

const CanteenList: React.FC = () => {
  const [canteens, setCanteens] = useState<CanteenOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchCanteens = async () => {
      setLoading(true);
      try {
        const res = await api.canteens.list();
        if (res.code === 0 && res.data) {
          setCanteens(res.data);
        }
      } catch {
        // Handled in mock engine
      } finally {
        setLoading(false);
      }
    };

    fetchCanteens();
  }, []);

  const filteredCanteens = canteens.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.location?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">校园食堂与美食档口</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            探索各大食堂招牌热销菜品、就餐人流、口味评分与卫生评价
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
          <input
            type="text"
            placeholder="搜索食堂名称、校区位置或热门美食..."
            className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none transition-all"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Canteen Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-6 border border-slate-200 animate-pulse space-y-4">
              <div className="h-6 bg-slate-200 rounded w-1/2"></div>
              <div className="h-4 bg-slate-200 rounded w-3/4"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredCanteens.map((canteen) => (
            <div
              key={canteen.id}
              className="group bg-white rounded-3xl overflow-hidden border border-slate-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all flex flex-col justify-between"
            >
              <div className="p-6 sm:p-8 space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 bg-rose-50 text-rose-700 text-xs font-bold rounded-md">
                        {canteen.opening_hours || '06:30 - 22:00'}
                      </span>
                    </div>
                    <h3 className="text-2xl font-black text-slate-900 mt-2 group-hover:text-indigo-600 transition-colors">
                      {canteen.name}
                    </h3>
                  </div>

                  <div className="p-3 bg-amber-50 rounded-2xl border border-amber-200/60 flex items-center gap-1.5 text-amber-700 text-sm font-black shrink-0">
                    <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                    <span>{canteen.rating ? Number(canteen.rating).toFixed(1) : '4.7'}</span>
                  </div>
                </div>

                <div className="space-y-2 text-xs text-slate-600">
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>{canteen.location || '主校区核心餐饮区'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Coffee className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>收录档口：{canteen.stalls?.length || 4} 个风味窗口</span>
                  </div>
                </div>

                {/* Popular Stalls preview */}
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">热门推荐档口</span>
                  <div className="flex flex-wrap gap-2">
                    {canteen.stalls?.map((stall) => (
                      <span
                        key={stall.id}
                        className="px-3 py-1 bg-slate-50 border border-slate-200 text-slate-700 rounded-xl text-xs font-medium"
                      >
                        {stall.name}
                      </span>
                    ))}
                  </div>
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
          ))}
        </div>
      )}
    </div>
  );
};

export default CanteenList;
