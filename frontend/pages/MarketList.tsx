import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Filter, Plus, Heart, MapPin, Tag, ArrowUpDown, RefreshCw } from 'lucide-react';
import { api, formatPrice } from '../services/api.ts';
import { ItemOut, ItemStatus } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { ImagePlaceholder } from '../components/ui';

// 兜底分类：后端 /api/items/categories 不可达时的默认值
const FALLBACK_CATEGORIES = ['全部', '电子产品', '书籍资料', '日用百货', '交通工具', '运动户外', '美妆服饰', '其他'];

const MarketList: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error } = useToast();

  const [search, setSearch] = useState(searchParams.get('keyword') || '');
  const [categories, setCategories] = useState<string[]>(FALLBACK_CATEGORIES);
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

  // 动态拉取后台配置的分类（含 school.yaml 兜底）
  useEffect(() => {
    api.items.categories()
      .then((res) => {
        if (res.code === 0 && res.data?.categories?.length) {
          setCategories(['全部', ...res.data.categories]);
        }
      })
      .catch(() => { /* 后端不可达时使用兜底分类 */ });
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchItems();
  };

  const getStatusBadge = (status: ItemStatus) => {
    switch (status) {
      case ItemStatus.OnSale:
        return <span className="px-1.5 py-0.5 bg-zone-market/10 text-zone-market mono-label tracking-mono rounded-lg">上架中</span>;
      case ItemStatus.OffSale:
        return <span className="px-1.5 py-0.5 bg-panel text-steel mono-label tracking-mono rounded-lg">已下架</span>;
      case ItemStatus.Sold:
        return <span className="px-1.5 py-0.5 bg-primary text-surface shadow-soft mono-label tracking-mono rounded-lg">已售出</span>;
      case ItemStatus.Reserved:
        return <span className="px-1.5 py-0.5 bg-panel text-steel mono-label tracking-mono rounded-lg">已预订</span>;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="mono-label text-zone-market tracking-mono mb-1">MARKET · 二手交易市集</div>
          <h1 className="text-heading-1 text-ink tracking-tight">二手交易市集</h1>
          <p className="text-body-2 text-steel mt-1">
            校内实名认证流转，支持发布、议价撮合、线下验机与安全交易
          </p>
        </div>

        <Link
          to="/market/publish"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors active:scale-95 shrink-0"
        >
          <Plus className="w-4 h-4" />
          发布闲置宝贝
        </Link>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-surface p-4 rounded-lg border border-hairline shadow-surface space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-steel w-4 h-4" />
            <input
              type="text"
              placeholder="搜索手机、平板、考研教材、电动车、生活日用品..."
              className="w-full pl-10 pr-4 py-2.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft focus:ring-2 focus:ring-ink/10 outline-none transition-colors"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors"
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
                className={`whitespace-nowrap px-3.5 py-1.5 mono-label uppercase tracking-mono rounded-lg transition-colors ${
                  isSelected
                    ? 'bg-zone-market text-surface'
                    : 'bg-panel text-steel hover:text-ink border border-transparent'
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>

        {/* Status Filter */}
        <div className="flex items-center justify-between pt-3 border-t border-hairline mono-label text-steel tracking-mono">
          <div className="flex items-center gap-2">
            <span>状态筛选:</span>
            {[
              { label: '全部状态', val: undefined },
              { label: '仅在售', val: ItemStatus.OnSale },
              { label: '已售出', val: ItemStatus.Sold }
            ].map((st) => (
              <button
                key={st.label}
                onClick={() => setSelectedStatus(st.val)}
                className={`px-2.5 py-1 rounded-lg uppercase tracking-mono transition-colors ${
                  selectedStatus === st.val
                    ? 'bg-panel text-ink font-semibold'
                    : 'text-steel hover:text-ink'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          <button
            onClick={fetchItems}
            className="flex items-center gap-1 text-steel hover:text-ink transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* Item Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="soft-card animate-pulse space-y-4">
              <div className="aspect-[4/3] bg-panel rounded-lg"></div>
              <div className="h-4 bg-panel rounded w-3/4"></div>
              <div className="h-3 bg-panel rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-surface rounded-lg p-16 text-center border border-hairline space-y-4">
          <div className="w-14 h-14 bg-panel rounded-lg flex items-center justify-center mx-auto text-steel">
            <Search className="w-6 h-6" />
          </div>
          <h2 className="text-heading-3 text-ink">暂未找到符合条件的闲置物品</h2>
          <p className="text-body-2 text-steel max-w-sm mx-auto">
            尝试更换搜索关键词或选择“全部”分类，或者做第一个发布该类闲置的同学！
          </p>
          <Link
            to="/market/publish"
            className="inline-block px-4 py-2 bg-primary text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono hover:bg-primary-hover transition-colors"
          >
            发布此类物品
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="group bg-surface rounded-lg overflow-hidden border border-hairline hover:border-ink transition-colors flex flex-col justify-between"
            >
              <div>
                <Link to={`/market/${item.id}`} className="relative block aspect-[4/3] overflow-hidden bg-panel">
                  {item.images?.[0]?.object_key ? (
                    <img
                      src={item.images[0].object_key}
                      alt={item.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <ImagePlaceholder className="w-full h-full rounded-none" />
                  )}
                  <div className="absolute top-2 left-2">
                    {getStatusBadge(item.status)}
                  </div>
                  <div className="absolute top-2 right-2 px-2 py-0.5 bg-primary/70 backdrop-blur-sm rounded-lg flex items-center gap-1 text-surface text-[11px] font-mono">
                    <Heart className="w-3 h-3 text-error fill-error" />
                    <span>{item.likes || 12}</span>
                  </div>
                </Link>

                <div className="p-4 space-y-2">
                  <div className="mono-label text-steel tracking-mono">
                    {item.category} · {item.owner_nickname || '校友发布'}
                  </div>
                  <Link to={`/market/${item.id}`} className="block">
                    <h2 className="text-heading-3 text-ink line-clamp-1 group-hover:text-zone-market transition-colors">
                      {item.title}
                    </h2>
                  </Link>

                  <p className="text-body-2 text-steel line-clamp-2 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>

              <div className="p-4 pt-0">
                <div className="flex items-center justify-between pt-3 border-t border-hairline">
                  <div className="flex items-baseline gap-0.5 text-zone-market">
                    <span className="text-xs font-mono font-bold">¥</span>
                    <span className="text-2xl font-black font-display tabular-nums">{formatPrice(item.price)}</span>
                  </div>
                  <Link
                    to={`/market/${item.id}`}
                    className="px-3 py-1.5 bg-panel hover:bg-primary text-ink hover:text-surface rounded-lg mono-label uppercase tracking-mono transition-colors"
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
