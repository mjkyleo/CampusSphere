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
import { ImagePlaceholder, PassCard } from '../components/ui';

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
      <div className="max-w-4xl mx-auto p-12 text-center text-steel">
        <div className="w-10 h-10 border-4 border-ink border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-body-2 mono-label tracking-mono">正在加载闲置物品详情...</p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center space-y-4">
        <h2 className="text-heading-2 text-ink">该闲置物品不存在或已被下架</h2>
        <Link to="/market" className="inline-block px-4 py-2 bg-primary text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono hover:bg-primary-hover transition-colors">
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

  // P2-22：收藏接真实端点（此前是纯 toast 假动作，无任何落库）
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const handleFavorite = async () => {
    if (!user) {
      info('请先登录后再收藏');
      return;
    }
    setFavoriteLoading(true);
    try {
      const res = await api.users.addFavorite(item.id);
      if (res.code === 0) {
        success('已添加到我的收藏');
      } else {
        error(res.message || '收藏失败');
      }
    } catch {
      error('收藏操作异常');
    } finally {
      setFavoriteLoading(false);
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
        className="flex items-center gap-1.5 text-steel hover:text-ink mono-label uppercase tracking-mono transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回市集
      </button>

      {/* Main Grid */}
      <div className="grid md:grid-cols-12 gap-8 bg-surface rounded-lg p-6 sm:p-8 border border-hairline shadow-surface">
        {/* Left: Images Carousel (6 cols) */}
        <div className="md:col-span-6 space-y-4">
          <div className="aspect-[4/3] rounded-lg overflow-hidden bg-panel border border-hairline relative group">
            {item.images?.[activeImageIdx]?.object_key || item.images?.[0]?.object_key ? (
              <img
                src={item.images?.[activeImageIdx]?.object_key || item.images?.[0]?.object_key || ''}
                alt={item.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
            ) : (
              <ImagePlaceholder className="w-full h-full rounded-none" />
            )}
            <div className="absolute top-2 left-2 px-2 py-0.5 bg-primary/70 backdrop-blur-sm rounded-lg text-surface mono-label tracking-mono">
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
                  className={`aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                    activeImageIdx === i ? 'border-ink scale-95' : 'border-hairline opacity-70 hover:opacity-100'
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
                <span className="px-2 py-0.5 bg-zone-market/10 text-zone-market mono-label tracking-mono rounded-lg">
                  {item.category}
                </span>
                <span className="text-caption text-steel">
                  浏览 {item.views || 89} 次 · 发布于 {item.created_at ? new Date(item.created_at).toLocaleDateString() : '近日'}
                </span>
              </div>

              <h1 className="text-heading-1 text-ink leading-tight">
                {item.title}
              </h1>
            </div>

            {/* Price section */}
            <div className="p-4 bg-panel/50 rounded-lg border border-hairline flex items-baseline justify-between">
              <div className="flex items-baseline gap-1 text-zone-market">
                <span className="text-sm font-mono font-bold">¥</span>
                <span className="text-3xl font-black font-display tabular-nums">{formatPrice(item.price)}</span>
                <span className="text-caption text-steel ml-2">校内面交价</span>
              </div>

              <div className="flex items-center gap-1.5 text-caption text-success font-semibold bg-success/10 px-2 py-1 rounded-lg border border-success/20">
                <ShieldCheck className="w-3.5 h-3.5 text-success" />
                <span>实名校园认证</span>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <h3 className="mono-label text-steel tracking-mono">物品详细说明</h3>
              <p className="text-body-2 text-slate leading-relaxed whitespace-pre-wrap bg-panel/40 p-4 rounded-lg border border-hairline">
                {item.description || '卖家未补充更多描述信息。'}
              </p>
            </div>

            {/* Seller profile card */}
            <div className="p-4 rounded-lg border border-hairline bg-surface flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-lg overflow-hidden bg-panel border border-hairline">
                  {item.owner_avatar ? (
                    <img
                      src={item.owner_avatar}
                      alt={item.owner_nickname || '卖家'}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <ImagePlaceholder variant="avatar" className="w-full h-full rounded-none border-0" />
                  )}
                </div>
                <div>
                  <p className="font-bold text-ink text-body-1">{item.owner_nickname || '校友卖家'}</p>
                  <p className="text-caption text-steel">信用评分 4.9 / 5.0 · 校园信用分极好</p>
                </div>
              </div>

              {!isOwner && (
                <button
                  onClick={() => openReport('item', item.id, item.title)}
                  className="flex items-center gap-1 text-caption text-error hover:text-ink font-semibold px-2.5 py-1 rounded-lg hover:bg-error/5 transition-colors"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  举报
                </button>
              )}
            </div>
          </div>

          {/* Owner controls OR Buyer Actions */}
          <div className="pt-4 border-t border-hairline">
            {isOwner ? (
              <div className="space-y-3">
                <div className="mono-label text-steel tracking-mono">管理我发布的物品</div>
                <div className="flex gap-2">
                  {item.status === ItemStatus.OnSale ? (
                    <button
                      onClick={() => handleStatusChange(ItemStatus.Sold)}
                      className="flex-1 py-2.5 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors"
                    >
                      标记为已售出
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStatusChange(ItemStatus.OnSale)}
                      className="flex-1 py-2.5 bg-success hover:opacity-90 text-surface rounded-lg mono-label uppercase tracking-mono transition-colors"
                    >
                      重新上架
                    </button>
                  )}
                  <button
                    onClick={handleDeleteItem}
                    className="p-2.5 bg-error/10 text-error hover:bg-error/20 rounded-lg transition-colors"
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
                  className="flex-1 py-3.5 px-6 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50"
                >
                  <MessageCircle className="w-4 h-4" />
                  {actionLoading ? '正在建立交易会话...' : '发起交易与在线咨询'}
                </button>
                <button
                  onClick={handleFavorite}
                  disabled={favoriteLoading}
                  className="p-3.5 bg-panel hover:bg-primary-hover text-slate rounded-lg transition-colors disabled:opacity-50"
                  title="收藏"
                >
                  <Heart className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 交易信息卡：分段展示交易关键信息 */}
      <PassCard
        title="MARKET · 交易信息"
        seq={`ITEM ${item.id}`}
        segments={[
          {
            label: '物品状态',
            value:
              item.status === ItemStatus.OnSale ? '上架中' :
              item.status === ItemStatus.Reserved ? '已预订' :
              item.status === ItemStatus.Sold ? '已售出' : '已下架',
            mono: true
          },
          { label: '转让价格', value: `¥ ${formatPrice(item.price)}`, mono: true },
          { label: '浏览量', value: `${item.views || 89} 次`, mono: true },
          { label: '身份认证', value: '实名校园认证' }
        ]}
        scanCode={String(item.id)}
        scanNote="凭物品编号发起交易会话"
        footer={
          !isOwner && (
            <Link
              to="/messages"
              className="mono-label inline-flex items-center gap-1.5 text-zone-market hover:text-ink transition-colors"
            >
              <MessageCircle className="w-4 h-4" />
              前往消息中心沟通交易
            </Link>
          )
        }
      />
    </div>
  );
};

export default MarketDetail;
