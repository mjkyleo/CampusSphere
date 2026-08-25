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
      <div className="max-w-5xl mx-auto p-12 text-center text-slate-400">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-sm">正在加载食堂档口与菜品...</p>
      </div>
    );
  }

  if (!canteen) {
    return (
      <div className="max-w-5xl mx-auto p-12 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-700">未找到该食堂</h2>
        <Link to="/canteens" className="inline-block px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold">
          返回食堂列表
        </Link>
      </div>
    );
  }

  const selectedStall = canteen.stalls?.find((s) => s.id === selectedStallId);

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-20">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-slate-500 hover:text-indigo-600 font-semibold text-sm transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回食堂列表
      </button>

      {/* Canteen Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-rose-50 text-rose-700 text-xs font-bold rounded-xl">
              {canteen.opening_hours || '06:30 - 22:00'}
            </span>
            <span className="text-xs text-slate-400">{canteen.location}</span>
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">{canteen.name}</h1>
          <p className="text-xs text-slate-500">{canteen.description || '提供南北风味小吃、特色面点与健康轻食'}</p>
        </div>

        <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200/60 flex items-center gap-2 text-amber-700 shrink-0">
          <Star className="w-6 h-6 fill-amber-400 text-amber-400" />
          <div>
            <span className="text-2xl font-black">{canteen.rating ? Number(canteen.rating).toFixed(1) : '4.7'}</span>
            <span className="text-[10px] text-amber-800 block font-bold">食堂口碑均分</span>
          </div>
        </div>
      </div>

      {/* Stall Tabs */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Utensils className="w-5 h-5 text-indigo-600" />
          选择风味档口
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {canteen.stalls?.map((stall) => {
            const isSelected = selectedStallId === stall.id;
            return (
              <button
                key={stall.id}
                onClick={() => handleSelectStall(stall.id)}
                className={`p-4 rounded-2xl border text-left transition-all ${
                  isSelected
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-200'
                    : 'bg-white text-slate-800 border-slate-200 hover:border-indigo-300'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-sm truncate">{stall.name}</span>
                  <div className={`flex items-center gap-0.5 text-xs font-bold ${isSelected ? 'text-amber-300' : 'text-amber-600'}`}>
                    <Star className="w-3 h-3 fill-current" />
                    <span>{stall.rating ? Number(stall.rating).toFixed(1) : '4.8'}</span>
                  </div>
                </div>
                <p className={`text-[11px] truncate ${isSelected ? 'text-indigo-100' : 'text-slate-400'}`}>
                  {stall.description || '招牌特色风味'}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Stall Menu & Recommended Dishes */}
      {selectedStall && (
        <div className="bg-white rounded-3xl p-6 border border-slate-200 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <span>{selectedStall.name} - 招牌菜单</span>
            </h3>
            <span className="text-xs text-slate-400">平均消费 ¥12 - ¥22</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {selectedStall.dishes?.map((dish, i) => (
              <div
                key={i}
                className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-between"
              >
                <span className="text-xs font-bold text-slate-800">{dish}</span>
                <span className="text-xs font-bold text-indigo-600">口碑力推</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Section */}
      <div className="grid md:grid-cols-12 gap-8">
        {/* Left: Add Review Form (5 cols) */}
        <div className="md:col-span-5 space-y-4">
          <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Plus className="w-4 h-4 text-indigo-600" />
              点评这家档口
            </h3>

            <form onSubmit={handleAddReview} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-600">菜品名称 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 招牌红烧牛肉面"
                  value={dishName}
                  onChange={(e) => setDishName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-600">消费金额 (元)</label>
                  <input
                    type="number"
                    step="0.5"
                    placeholder="15.0"
                    value={priceYuan}
                    onChange={(e) => setPriceYuan(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-600">打分</label>
                  <div className="flex gap-1 pt-1.5">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <button
                        type="button"
                        key={s}
                        onClick={() => setRating(s)}
                        className="hover:scale-110 transition-transform"
                      >
                        <Star className={`w-5 h-5 ${s <= rating ? 'fill-amber-400 text-amber-400' : 'text-slate-300'}`} />
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-600">味道与卫生点评 *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="分量足不足？汤底浓不浓？出餐快不快？..."
                  value={reviewContent}
                  onChange={(e) => setReviewContent(e.target.value)}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                {submitting ? '提交中...' : '提交美食点评'}
              </button>
            </form>
          </div>
        </div>

        {/* Right: Review List (7 cols) */}
        <div className="md:col-span-7 space-y-4">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-indigo-600" />
            学生食客评价 ({reviews.length})
          </h3>

          <div className="space-y-3">
            {reviews.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-3xl border border-slate-200 text-slate-400 text-xs">
                该档口暂无评价，快来抢先留下第一条美食点评吧！
              </div>
            ) : (
              reviews.map((rev) => (
                <div
                  key={rev.id}
                  className="p-5 bg-white rounded-3xl border border-slate-200 space-y-3 hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-700 border border-slate-200">
                        {rev.user_nickname?.charAt(0) || '食'}
                      </div>
                      <div>
                        <span className="font-bold text-slate-800 text-xs block">{rev.user_nickname || '校友食客'}</span>
                        <span className="text-[10px] text-slate-400">
                          {rev.created_at ? new Date(rev.created_at).toLocaleDateString() : '近日'}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                        {rev.dish_name}
                      </span>
                      <div className="flex items-center text-xs text-amber-600 font-bold">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                        <span>{rev.rating}分</span>
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">{rev.content}</p>

                  <div className="flex justify-between items-center text-[11px] text-slate-400 pt-1 border-t border-slate-100">
                    <span>
                      {rev.price_cents ? `消费：¥${formatPrice(rev.price_cents)}` : '实惠好味'}
                    </span>
                    <button
                      onClick={() => openReport('comment', rev.id, `食堂评价: ${rev.dish_name}`)}
                      className="text-slate-400 hover:text-rose-500 flex items-center gap-1"
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
