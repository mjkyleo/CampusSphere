import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ChevronLeft, Star, Utensils, MessageSquare, Plus,
  MapPin, Clock, DollarSign, Send, ShieldAlert, Heart
} from 'lucide-react';
import { api, formatPrice, toCents } from '../services/api.ts';
import { CanteenOut, CanteenStallOut, CanteenReviewOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

const CanteenStall: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, openReport } = useAuth();
  const { success, error } = useToast();

  const [canteen, setCanteen] = useState<CanteenOut | null>(null);
  const [selectedStallId, setSelectedStallId] = useState<string>('');
  const [reviews, setReviews] = useState<CanteenReviewOut[]>([]);
  const [loading, setLoading] = useState(true);

  // New review form
  const [dishName, setDishName] = useState('');
  const [priceYuan, setPriceYuan] = useState('');
  const [rating, setRating] = useState(5);
  const [reviewContent, setReviewContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchCanteen = async () => {
      setLoading(true);
      try {
        const cRes = await api.canteens.get(id);
        if (cRes.code === 0 && cRes.data) {
          setCanteen(cRes.data);
          const firstStall = cRes.data.stalls?.[0]?.id || '';
          setSelectedStallId(firstStall);

          const rRes = await api.canteens.getReviews(id, firstStall || undefined);
          if (rRes.code === 0 && rRes.data) {
            setReviews(rRes.data.items || []);
          }
        }
      } catch {
        // Handled in mock engine
      } finally {
        setLoading(false);
      }
    };

    fetchCanteen();
  }, [id]);

  const handleSelectStall = async (stallId: string) => {
    if (!id) return;
    setSelectedStallId(stallId);
    try {
      const rRes = await api.canteens.getReviews(id, stallId);
      if (rRes.code === 0 && rRes.data) {
        setReviews(rRes.data.items || []);
      }
    } catch {
      // Handled
    }
  };

  const handleAddReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !selectedStallId) {
      error('请先选择对应档口');
      return;
    }
    if (!dishName.trim()) {
      error('请填写菜品名称');
      return;
    }
    if (!reviewContent.trim()) {
      error('请填写评价内容');
      return;
    }

    setSubmitting(true);
    try {
      const priceCents = priceYuan ? toCents(parseFloat(priceYuan)) : undefined;
      const res = await api.canteens.addReview({
        canteen_id: id,
        stall_id: selectedStallId,
        dish_name: dishName.trim(),
        rating,
        content: reviewContent.trim(),
        price_cents: priceCents
      });

      if (res.code === 0 && res.data) {
        success('美食点评发布成功！');
        setReviews((prev) => [res.data, ...prev]);
        setDishName('');
        setPriceYuan('');
        setReviewContent('');
      } else {
        error(res.message || '发布点评失败');
      }
    } catch {
      error('提交点评异常');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-12 text-center text-steel">
        <div className="w-10 h-10 border-4 border-ink border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-body-2 mono-label tracking-mono">正在加载食堂档口与菜品...</p>
      </div>
    );
  }

  if (!canteen) {
    return (
      <div className="max-w-5xl mx-auto p-12 text-center space-y-4">
        <h2 className="text-heading-2 text-ink">未找到该食堂</h2>
        <Link to="/canteens" className="inline-block px-4 py-2 bg-ink text-surface rounded-sm mono-label uppercase tracking-mono hover:bg-slate transition-colors">
          返回食堂列表
        </Link>
      </div>
    );
  }

  const selectedStall = canteen.stalls?.find((s) => s.id === selectedStallId);

  const inputCls =
    'w-full px-3.5 py-2.5 bg-surface border border-hairline rounded-sm text-body-1 text-ink placeholder:text-steel focus:bg-white focus:border-ink focus:ring-2 focus:ring-ink/10 outline-none transition-colors';

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-20">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-steel hover:text-ink mono-label uppercase tracking-mono transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回食堂列表
      </button>

      {/* Canteen Header */}
      <div className="bg-surface rounded-md p-6 sm:p-8 border border-hairline shadow-surface flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="px-2.5 py-0.5 bg-zone-canteen/10 text-zone-canteen font-mono font-bold text-xs rounded-sm tracking-mono">
              {canteen.opening_hours || '06:30 - 22:00'}
            </span>
            {canteen.canteen_type && (
              <span className="px-2.5 py-0.5 bg-panel text-slate font-mono font-bold text-xs rounded-sm tracking-mono">
                {canteen.canteen_type}
              </span>
            )}
            {canteen.floor && (
              <span className="px-2.5 py-0.5 bg-panel text-slate font-mono font-bold text-xs rounded-sm tracking-mono">
                {canteen.floor}
              </span>
            )}
            {canteen.semester && (
              <span className="px-2.5 py-0.5 bg-success/10 text-success font-mono font-bold text-xs rounded-sm tracking-mono">
                {canteen.semester}
              </span>
            )}
          </div>
          <h1 className="text-heading-1 text-ink tracking-tight">{canteen.name}</h1>
          {(canteen.campus || canteen.zone) && (
            <p className="text-caption text-steel flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {[canteen.campus, canteen.zone].filter(Boolean).join(' · ')} · {canteen.location || '主校区'},
            </p>
          )}
          <p className="text-body-2 text-steel">{canteen.description || '提供南北风味小吃、特色面点与健康轻食'}</p>
          {canteen.features && canteen.features.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {canteen.features.map((f) => (
                <span key={f} className="px-2 py-0.5 bg-success/10 text-success text-[11px] font-mono font-bold rounded-sm tracking-mono">
                  {f}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 bg-zone-canteen/10 rounded-sm border border-zone-canteen/20 flex items-center gap-2 text-zone-canteen shrink-0">
          <Star className="w-6 h-6 fill-zone-canteen text-zone-canteen" />
          <div>
            <span className="text-2xl font-black font-display tabular-nums">{canteen.rating ? Number(canteen.rating).toFixed(1) : '4.7'}</span>
            <span className="mono-label text-zone-canteen block tracking-mono">食堂口碑均分</span>
          </div>
        </div>
      </div>

      {/* 招牌菜展示 */}
      {canteen.popular_dishes && canteen.popular_dishes.length > 0 && (
        <div className="bg-surface rounded-md p-6 border border-hairline shadow-surface space-y-3">
          <h3 className="text-heading-3 text-ink flex items-center gap-2">
            <Utensils className="w-5 h-5 text-zone-canteen" />
            招牌美食
          </h3>
          <div className="flex flex-wrap gap-2">
            {canteen.popular_dishes.map((d) => (
              <span key={d} className="px-3 py-1.5 bg-panel border border-hairline text-slate rounded-sm text-body-2 font-medium mono-label tracking-mono">
                {d}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Stall Tabs */}
      <div className="space-y-3">
        <h2 className="text-heading-2 text-ink flex items-center gap-2">
          <Utensils className="w-5 h-5 text-zone-canteen" />
          选择风味档口
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {canteen.stalls?.map((stall) => {
            const isSelected = selectedStallId === stall.id;
            return (
              <button
                key={stall.id}
                onClick={() => handleSelectStall(stall.id)}
                className={`p-4 rounded-sm border text-left transition-colors ${
                  isSelected
                    ? 'bg-zone-canteen text-surface border-zone-canteen'
                    : 'bg-surface text-slate border-hairline hover:border-zone-canteen'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-body-1 truncate">{stall.name}</span>
                  <div className={`flex items-center gap-0.5 text-xs font-bold font-mono ${isSelected ? 'text-surface' : 'text-zone-canteen'}`}>
                    <Star className="w-3 h-3 fill-current" />
                    <span>{stall.rating ? Number(stall.rating).toFixed(1) : '4.8'}</span>
                  </div>
                </div>
                <p className={`text-caption truncate ${isSelected ? 'text-surface/80' : 'text-steel'}`}>
                  {stall.description || '招牌特色风味'}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Stall Menu & Recommended Dishes */}
      {selectedStall && (
        <div className="bg-surface rounded-md p-6 border border-hairline shadow-surface space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-heading-3 text-ink flex items-center gap-2">
              <span>{selectedStall.name} - 招牌菜单</span>
            </h3>
            <span className="text-caption text-steel font-mono">平均消费 ¥12 - ¥22</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {selectedStall.dishes?.map((dish, i) => (
              <div
                key={i}
                className="p-3.5 bg-panel/40 rounded-sm border border-hairline flex items-center justify-between"
              >
                <span className="text-body-2 font-semibold text-ink">{dish}</span>
                <span className="text-caption font-bold text-zone-canteen mono-label tracking-mono">档口招牌</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Section */}
      <div className="grid md:grid-cols-12 gap-8">
        {/* Left: Add Review Form (5 cols) */}
        <div className="md:col-span-5 space-y-4">
          <div className="bg-surface rounded-md p-6 border border-hairline shadow-surface space-y-4">
            <h3 className="text-heading-3 text-ink flex items-center gap-2">
              <Plus className="w-4 h-4 text-zone-canteen" />
              点评这家档口
            </h3>

            <form onSubmit={handleAddReview} className="space-y-4">
              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">菜品名称 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 招牌红烧牛肉面"
                  value={dishName}
                  onChange={(e) => setDishName(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block mono-label text-steel tracking-mono">消费金额 (元)</label>
                  <input
                    type="number"
                    step="0.5"
                    placeholder="15.0"
                    value={priceYuan}
                    onChange={(e) => setPriceYuan(e.target.value)}
                    className={inputCls + ' font-mono text-zone-canteen tabular-nums'}
                  />
                </div>

                <div className="space-y-1">
                  <label className="block mono-label text-steel tracking-mono">打分</label>
                  <div className="flex gap-1 pt-1.5">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <button
                        type="button"
                        key={s}
                        onClick={() => setRating(s)}
                        className="hover:scale-110 transition-transform"
                      >
                        <Star className={`w-5 h-5 ${s <= rating ? 'fill-zone-canteen text-zone-canteen' : 'text-steel'}`} />
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">味道与卫生点评 *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="分量足不足？汤底浓不浓？出餐快不快？..."
                  value={reviewContent}
                  onChange={(e) => setReviewContent(e.target.value)}
                  className="w-full p-3 bg-surface border border-hairline rounded-sm text-body-1 text-ink placeholder:text-steel focus:bg-white focus:border-ink outline-none transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-ink hover:bg-slate text-surface rounded-sm mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                {submitting ? '提交中...' : '提交美食点评'}
              </button>
            </form>
          </div>
        </div>

        {/* Right: Review List (7 cols) */}
        <div className="md:col-span-7 space-y-4">
          <h3 className="text-heading-3 text-ink flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-zone-canteen" />
            学生食客评价 ({reviews.length})
          </h3>

          <div className="space-y-3">
            {reviews.length === 0 ? (
              <div className="p-8 text-center bg-surface rounded-md border border-hairline text-steel text-body-2">
                该档口暂无评价，快来抢先留下第一条美食点评吧！
              </div>
            ) : (
              reviews.map((rev) => (
                <div
                  key={rev.id}
                  className="p-5 bg-surface rounded-md border border-hairline space-y-3 hover:border-zone-canteen transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-sm bg-panel flex items-center justify-center text-xs font-bold text-zone-canteen border border-hairline">
                        {rev.user_nickname?.charAt(0) || '食'}
                      </div>
                      <div>
                        <span className="font-bold text-ink text-body-1 block">{rev.user_nickname || '校友食客'}</span>
                        <span className="text-caption text-steel font-mono">
                          {rev.created_at ? new Date(rev.created_at).toLocaleDateString() : '近日'}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-caption font-bold text-zone-canteen bg-zone-canteen/10 px-2 py-0.5 rounded-sm mono-label tracking-mono">
                        {rev.dish_name}
                      </span>
                      <div className="flex items-center text-xs text-zone-canteen font-bold font-mono">
                        <Star className="w-3 h-3 fill-zone-canteen text-zone-canteen" />
                        <span>{rev.rating}分</span>
                      </div>
                    </div>
                  </div>

                  <p className="text-body-2 text-slate leading-relaxed">{rev.content}</p>

                  <div className="flex justify-between items-center text-caption text-steel pt-1 border-t border-hairline font-mono">
                    <span>
                      {rev.price_cents ? `消费：¥${formatPrice(rev.price_cents)}` : '实惠好味'}
                    </span>
                    <button
                      onClick={() => openReport('comment', rev.id, `食堂评价: ${rev.dish_name}`)}
                      className="text-steel hover:text-error flex items-center gap-1 transition-colors"
                    >
                      <ShieldAlert className="w-3 h-3" />
                      举报
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CanteenStall;
