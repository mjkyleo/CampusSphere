import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ChevronLeft, Heart, MessageCircle, Share2, MapPin, User,
  ShieldCheck, Tag, Trash2, Edit3, ShieldAlert, ArrowRight, CheckCircle2
} from 'lucide-react';
import { api, formatPrice } from '../services/api.ts';
import { ItemOut, ItemStatus } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

const MarketDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, openReport } = useAuth();
  const { success, error, info } = useToast();

  const [item, setItem] = useState<ItemOut | null>(null);
  const [activeImageIdx, setActiveImageIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchDetail = async () => {
      setLoading(true);
      try {
        const res = await api.items.get(id);
        if (res.code === 0 && res.data) {
          setItem(res.data);
        }
      } catch {
        // Mock fallback
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center text-slate-400">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-sm">正在加载闲置物品详情...</p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-700">该闲置物品不存在或已被下架</h2>
        <Link to="/market" className="inline-block px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold">
          返回市集列表
        </Link>
      </div>
    );
  }

  const isOwner = user?.id === item.owner_id;

  // Handle Trade Session / Direct Inquiry
  const handleStartTrade = async () => {
    setActionLoading(true);
    try {
      const res = await api.items.trade(item.id);
      if (res.code === 0 && res.data) {
        success('已与卖家发起交易会话！正在跳转至沟通窗口...');
        setTimeout(() => {
          navigate('/messages');
        }, 500);
      } else {
        error(res.message || '发起交易失败');
      }
    } catch {
      error('网络异常，请重试');
    } finally {
      setActionLoading(false);
    }
  };

  // Owner: Change status
  const handleStatusChange = async (newStatus: ItemStatus) => {
    const res = await api.items.update(item.id, { status: newStatus });
    if (res.code === 0) {
      setItem((prev) => (prev ? { ...prev, status: newStatus } : null));
      success('物品状态更新成功！');
    } else {
      error('更新失败');
    }
  };

  // Owner: Delete
  const handleDeleteItem = async () => {
    if (!window.confirm('确定要删除这条闲置发布吗？操作不可恢复。')) return;
    const res = await api.items.delete(item.id);
    if (res.code === 0) {
      success('已成功删除物品');
      navigate('/market');
    } else {
      error('删除失败');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-28">
      {/* Top back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-slate-500 hover:text-indigo-600 font-semibold text-sm transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回市集
      </button>

      {/* Main Grid */}
      <div className="grid md:grid-cols-12 gap-8 bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm">
        {/* Left: Images Carousel (6 cols) */}
        <div className="md:col-span-6 space-y-4">
          <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-slate-100 border border-slate-200 relative group">
            <img
              src={item.images?.[activeImageIdx]?.object_key || item.images?.[0]?.object_key || 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=800'}
              alt={item.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
            <div className="absolute top-3 left-3 px-3 py-1 bg-black/60 backdrop-blur-md rounded-xl text-white text-xs font-bold">
              {item.category}
            </div>
          </div>

          {/* Thumbnails */}
          {item.images && item.images.length > 1 && (
            <div className="grid grid-cols-4 gap-3">
              {item.images.map((img, i) => (
                <button
                  key={i}
                  onClick={() => setActiveImageIdx(i)}
                  className={`aspect-square rounded-xl overflow-hidden border-2 transition-all ${
                    activeImageIdx === i ? 'border-indigo-600 scale-95 shadow-sm' : 'border-slate-200 opacity-70 hover:opacity-100'
                  }`}
                >
                  <img src={img.object_key} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Info & Actions (6 cols) */}
        <div className="md:col-span-6 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-md">
                  {item.category}
                </span>
                <span className="text-xs text-slate-400">
                  浏览 {item.views || 89} 次 • 发布于 {item.created_at ? new Date(item.created_at).toLocaleDateString() : '近日'}
                </span>
              </div>

              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 leading-tight">
                {item.title}
              </h1>
            </div>

            {/* Price section */}
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-baseline justify-between">
              <div className="flex items-baseline gap-1 text-indigo-600">
                <span className="text-sm font-bold">¥</span>
                <span className="text-3xl font-black">{formatPrice(item.price)}</span>
                <span className="text-xs text-slate-400 ml-2">校内面交价</span>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-bold bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200/60">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>实名校园认证</span>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">物品详细说明</h3>
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap bg-slate-50/50 p-4 rounded-2xl border border-slate-100">
                {item.description || '卖家未补充更多描述信息。'}
              </p>
            </div>

            {/* Seller profile card */}
            <div className="p-4 rounded-2xl border border-slate-200 bg-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl overflow-hidden bg-slate-100 border border-slate-200">
                  <img
                    src={item.owner_avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}
                    alt="Seller"
                    className="w-full h-full object-cover"
                  />
                </div>
                <div>
                  <p className="font-bold text-slate-900 text-sm">{item.owner_nickname || '校友卖家'}</p>
                  <p className="text-[11px] text-slate-400">信用评分 4.9 / 5.0 • 芝麻校园分极好</p>
                </div>
              </div>

              {!isOwner && (
                <button
                  onClick={() => openReport('item', item.id, item.title)}
                  className="flex items-center gap-1 text-xs text-rose-500 hover:text-rose-700 font-semibold px-2.5 py-1 rounded-lg hover:bg-rose-50 transition-colors"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  举报
                </button>
              )}
            </div>
          </div>

          {/* Owner controls OR Buyer Actions */}
          <div className="pt-4 border-t border-slate-100">
            {isOwner ? (
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-400 uppercase">管理我发布的物品</div>
                <div className="flex gap-2">
                  {item.status === ItemStatus.OnSale ? (
                    <button
                      onClick={() => handleStatusChange(ItemStatus.Sold)}
                      className="flex-1 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition-colors"
                    >
                      标记为已售出
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStatusChange(ItemStatus.OnSale)}
                      className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors"
                    >
                      重新上架
                    </button>
                  )}
                  <button
                    onClick={handleDeleteItem}
                    className="p-2.5 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-xl transition-colors"
                    title="删除物品"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-3">
                <button
                  onClick={handleStartTrade}
                  disabled={actionLoading}
                  className="flex-1 py-3.5 px-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-sm shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50"
                >
                  <MessageCircle className="w-5 h-5" />
                  {actionLoading ? '正在建立交易会话...' : '发起交易与在线咨询'}
                </button>
                <button
                  onClick={() => info('已添加到我的收藏')}
                  className="p-3.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-2xl transition-colors"
                  title="收藏"
                >
                  <Heart className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketDetail;
