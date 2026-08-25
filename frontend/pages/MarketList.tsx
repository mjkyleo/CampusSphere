import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Filter, Plus, Heart, MapPin, Tag, ArrowUpDown, RefreshCw } from 'lucide-react';
import { api, formatPrice } from '../services/api.ts';
import { ItemOut, ItemStatus } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

const categories = ['全部', '电子产品', '书籍资料', '日用百货', '交通工具', '运动户外', '美妆服饰', '其他'];

const MarketList: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error } = useToast();

  const [search, setSearch] = useState(searchParams.get('keyword') || '');
  const [selectedCat, setSelectedCat] = useState(searchParams.get('category') || '全部');
  const [selectedStatus, setSelectedStatus] = useState<number | undefined>(ItemStatus.OnSale);
  const [items, setItems] = useState<ItemOut[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const res = await api.items.list({
        keyword: search.trim() || undefined,
        category: selectedCat === '全部' ? undefined : selectedCat,
        status: selectedStatus
      });
      if (res.code === 0 && res.data) {
        setItems(res.data.items || []);
      }
    } catch {
      // Handled in mock engine
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [selectedCat, selectedStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchItems();
  };

  const getStatusBadge = (status: ItemStatus) => {
    switch (status) {
      case ItemStatus.OnSale:
        return <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded">上架中</span>;
      case ItemStatus.OffSale:
        return <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded">已下架</span>;
      case ItemStatus.Sold:
        return <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-[10px] font-bold rounded">已售出</span>;
      case ItemStatus.Reserved:
        return <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded">已预订</span>;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">二手交易市集</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            校内实名认证流转，支持发布、议价撮合、线下验机与安全交易
          </p>
        </div>

        <Link
          to="/market/publish"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold shadow-lg shadow-indigo-200 transition-all active:scale-95 shrink-0"
        >
          <Plus className="w-5 h-5" />
          发布闲置宝贝
        </Link>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索手机、平板、考研教材、电动车、生活日用品..."
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl text-sm font-bold transition-colors"
          >
            搜索
          </button>
        </form>

        {/* Category Pill Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-1">
          {categories.map((cat) => {
            const isSelected = selectedCat === cat;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCat(cat)}
                className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>

        {/* Status Filter */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="font-semibold">状态筛选:</span>
            {[
              { label: '全部状态', val: undefined },
              { label: '仅在售', val: ItemStatus.OnSale },
              { label: '已售出', val: ItemStatus.Sold }
            ].map((st) => (
              <button
                key={st.label}
                onClick={() => setSelectedStatus(st.val)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                  selectedStatus === st.val
                    ? 'bg-indigo-50 text-indigo-700 font-bold'
                    : 'hover:bg-slate-100 text-slate-600'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          <button
            onClick={fetchItems}
            className="flex items-center gap-1 text-slate-400 hover:text-indigo-600 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* Item Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-4 border border-slate-200 animate-pulse space-y-4">
              <div className="aspect-[4/3] bg-slate-200 rounded-2xl"></div>
              <div className="h-4 bg-slate-200 rounded w-3/4"></div>
              <div className="h-3 bg-slate-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-3xl p-16 text-center border border-slate-200 space-y-4">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400">
            <Search className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-slate-700">暂未找到符合条件的闲置物品</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            尝试更换搜索关键词或选择“全部”分类，或者做第一个发布该类闲置的同学！
          </p>
          <Link
            to="/market/publish"
            className="inline-block px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100"
          >
            发布此类物品
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {items.map((item) => (
            <div
              key={item.id}
              className="group bg-white rounded-3xl overflow-hidden border border-slate-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all flex flex-col justify-between"
            >
              <div>
                <Link to={`/market/${item.id}`} className="relative block aspect-[4/3] overflow-hidden bg-slate-100">
                  <img
                    src={item.images?.[0]?.object_key || 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600'}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute top-3 left-3">
                    {getStatusBadge(item.status)}
                  </div>
                  <div className="absolute top-3 right-3 px-2 py-1 bg-black/60 backdrop-blur-md rounded-lg flex items-center gap-1 text-white text-[10px] font-bold">
                    <Heart className="w-3 h-3 text-rose-400 fill-rose-400" />
                    <span>{item.likes || 12}</span>
                  </div>
                </Link>

                <div className="p-4 space-y-2">
                  <Link to={`/market/${item.id}`} className="block">
                    <h3 className="font-bold text-slate-900 text-base line-clamp-1 group-hover:text-indigo-600 transition-colors">
                      {item.title}
                    </h3>
                  </Link>

                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                    {item.description}
                  </p>

                  <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-400">
                    <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-600 font-medium">
                      {item.category}
                    </span>
                    <span>•</span>
                    <span className="truncate">{item.owner_nickname || '校友发布'}</span>
                  </div>
                </div>
              </div>

              <div className="p-4 pt-0">
                <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                  <div className="flex items-baseline gap-0.5 text-indigo-600">
                    <span className="text-xs font-bold">¥</span>
                    <span className="text-2xl font-black">{formatPrice(item.price)}</span>
                  </div>
                  <Link
                    to={`/market/${item.id}`}
                    className="px-3.5 py-1.5 bg-indigo-50 hover:bg-indigo-600 text-indigo-600 hover:text-white rounded-xl text-xs font-bold transition-all"
                  >
                    查看详情
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MarketList;
