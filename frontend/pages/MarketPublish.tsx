import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Sparkles, Upload, Loader2 } from 'lucide-react';
import { api, toCents } from '../services/api.ts';
import { ItemStatus } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { generateItemDescription } from '../services/geminiService.ts';

// 兜底分类：后端 /api/items/categories 不可达时的默认值
const FALLBACK_CATEGORIES = ['电子产品', '书籍资料', '日用百货', '交通工具', '运动户外', '美妆服饰', '其他'];

/**
 * Convert an image reference (either a full URL or an object_key) to a
 * displayable src. Preset images are full URLs; uploaded images return
 * object_keys that are served via the backend `/api/files/raw` endpoint
 * (local fallback mode) or as direct MinIO URLs (when the presign
 * response returns an `http` URL).
 */
const getImageSrc = (img: string): string => {
  if (img.startsWith('http')) return img;
  return `/api/files/raw?key=${encodeURIComponent(img)}`;
};

const MarketPublish: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error } = useToast();

  const [title, setTitle] = useState('');
  const [priceYuan, setPriceYuan] = useState('');
  const [categories, setCategories] = useState<string[]>(FALLBACK_CATEGORIES);
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [images, setImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);

  // 动态拉取后台配置的分类（含 school.yaml 兜底），加载完成后设置默认选中项
  useEffect(() => {
    api.items.categories()
      .then((res) => {
        const list = res.code === 0 && res.data?.categories?.length ? res.data.categories : FALLBACK_CATEGORIES;
        setCategories(list);
        setCategory((prev) => prev || list[0] || '');
      })
      .catch(() => {
        setCategories(FALLBACK_CATEGORIES);
        setCategory((prev) => prev || FALLBACK_CATEGORIES[0]);
      });
  }, []);

  const handleRemoveImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  /**
   * Handle real file upload via the presign flow:
   * 1. For each selected file, call `api.files.uploadImage(file, 'items')`
   *    which internally: presign → PUT to MinIO (or POST to local upload).
   * 2. The returned `object_key` is added to the `images` state array.
   * 3. At submit time, `images.map((img) => ({ object_key: img }))` sends
   *    the object_keys to the backend for item creation.
   */
  const handleFileUpload = async (files: FileList) => {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    setUploading(true);
    try {
      const uploadedKeys: string[] = [];
      for (const file of fileArray) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
          error(`${file.name} 不是图片文件，已跳过`);
          continue;
        }
        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
          error(`${file.name} 超过10MB限制，已跳过`);
          continue;
        }
        const objectKey = await api.files.uploadImage(file, 'items');
        uploadedKeys.push(objectKey);
      }
      if (uploadedKeys.length > 0) {
        setImages((prev) => [...prev, ...uploadedKeys]);
        success(`成功上传 ${uploadedKeys.length} 张图片`);
      }
    } catch (err) {
      error('图片上传失败，请检查网络后重试');
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateAIDescription = async () => {
    if (!title.trim()) {
      error('请先填写物品标题，以便 AI 精准生成描述与定价建议');
      return;
    }
    setAiGenerating(true);
    try {
      const generated = await generateItemDescription(title, category);
      if (generated) {
        setDescription(generated);
        success('AI 智能文案已生成并填充！');
      }
    } catch {
      error('AI 生成失败，请稍后重试');
    } finally {
      setAiGenerating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !priceYuan || !description.trim() || !category) {
      error('请填写完整的物品信息');
      return;
    }

    const priceNum = parseFloat(priceYuan);
    if (isNaN(priceNum) || priceNum <= 0) {
      error('请输入有效的价格（大于0）');
      return;
    }

    if (images.length === 0) {
      error('请至少上传或选择一张物品实拍图');
      return;
    }

    setLoading(true);
    try {
      const res = await api.items.create({
        title: title.trim(),
        price: toCents(priceNum),
        category,
        description: description.trim(),
        images: images.map((img) => ({ object_key: img }))
      });

      if (res.code === 0 && res.data) {
        if (res.data.status === ItemStatus.Pending) {
          // 后台开启发布审核时：进入"待审核"，仅本人可见
          success('提交成功！物品已进入待审核状态，请等待管理员审核通过后上架');
          navigate(`/market/${res.data.id}`);
        } else {
          success('闲置物品发布成功！已实时同步至市集列表');
          navigate(`/market/${res.data.id}`);
        }
      } else {
        error(res.message || '发布失败');
      }
    } catch {
      error('提交发布出现异常');
    } finally {
      setLoading(false);
    }
  };

  const inputCls =
    'w-full px-4 py-2.5 bg-surface border border-hairline rounded-sm text-body-1 text-ink placeholder:text-steel focus:bg-white focus:border-ink focus:ring-2 focus:ring-ink/10 outline-none transition-colors';

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-20">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-steel hover:text-ink mono-label uppercase tracking-mono transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        取消并返回
      </button>

      <div className="bg-surface rounded-md p-6 sm:p-10 border border-hairline shadow-surface space-y-8">
        <div>
          <div className="mono-label text-zone-market tracking-mono mb-1">MARKET · 发布登机口</div>
          <h1 className="text-heading-1 text-ink tracking-tight">发布闲置宝贝</h1>
          <p className="text-body-2 text-steel mt-1">
            转让二手书籍、电子设备、生活好物，支持 AI 一键润色商品介绍
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Title */}
          <div className="space-y-1.5">
            <label className="block mono-label text-steel tracking-mono">物品标题 <span className="text-error">*</span></label>
            <input
              type="text"
              required
              placeholder="例如: 99新 iPad Air 5 64G 蓝色 (带原装包装盒及笔)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className={inputCls}
            />
          </div>

          {/* Category & Price */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block mono-label text-steel tracking-mono">分类选择 <span className="text-error">*</span></label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-4 py-2.5 bg-surface border border-hairline rounded-sm text-body-1 text-ink focus:bg-white focus:border-ink outline-none"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block mono-label text-steel tracking-mono">转让价格 (元) <span className="text-error">*</span></label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-steel font-mono font-bold">¥</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.1"
                  required
                  placeholder="0.00"
                  value={priceYuan}
                  onChange={(e) => setPriceYuan(e.target.value)}
                  className={inputCls + ' pl-9 font-mono text-zone-market tabular-nums'}
                />
              </div>
            </div>
          </div>

          {/* Images */}
          <div className="space-y-2">
            <label className="block mono-label text-steel tracking-mono">物品图片 (已选 {images.length} 张) <span className="text-error">*</span></label>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {images.map((img, idx) => (
                <div key={idx} className="relative aspect-square rounded-sm overflow-hidden border border-hairline group">
                  <img src={getImageSrc(img)} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => handleRemoveImage(idx)}
                    className="absolute top-2 right-2 p-1 bg-ink/70 hover:bg-error text-surface rounded-sm text-xs transition-colors"
                  >
                    ✕
                  </button>
                </div>
              ))}

              {/* File upload tile */}
              <label className={`aspect-square rounded-sm border-2 border-dashed border-hairline hover:border-ink flex flex-col items-center justify-center cursor-pointer transition-colors ${uploading ? 'opacity-60 pointer-events-none' : ''}`}>
                {uploading ? (
                  <>
                    <Loader2 className="w-6 h-6 text-ink animate-spin mb-1" />
                    <span className="text-caption text-steel">上传中...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-6 h-6 text-steel mb-1" />
                    <span className="text-caption text-steel mono-label tracking-mono">上传实拍图</span>
                    <span className="text-[11px] text-steel">支持多选 · ≤10MB</span>
                  </>
                )}
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileUpload(e.target.files);
                      e.target.value = ''; // Reset to allow re-uploading the same file
                    }
                  }}
                />
              </label>
            </div>
          </div>

          {/* Description + AI Generator button */}
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <label className="block mono-label text-steel tracking-mono">
                详细描述 (成色、购买时间、交易地点等) <span className="text-error">*</span>
              </label>

              <button
                type="button"
                onClick={handleGenerateAIDescription}
                disabled={aiGenerating}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-panel hover:bg-slate/10 text-ink border border-hairline rounded-sm mono-label uppercase tracking-mono transition-colors whitespace-nowrap"
              >
                <Sparkles className="w-3.5 h-3.5 text-ink" />
                {aiGenerating ? 'AI 正在构思...' : 'AI 智能润色文案'}
              </button>
            </div>

            <textarea
              rows={5}
              required
              placeholder="详细描述物品的规格、使用频次、有无磨损、是否附带配件，以及期望在校内哪个区域面交..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full p-4 bg-surface border border-hairline rounded-sm text-body-1 leading-relaxed text-ink placeholder:text-steel focus:bg-white focus:border-ink outline-none transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-ink hover:bg-slate text-surface rounded-sm mono-label uppercase tracking-mono transition-colors flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50"
          >
            {loading ? '正在发布...' : '确认发布到市集'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default MarketPublish;
