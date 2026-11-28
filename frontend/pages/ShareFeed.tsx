import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Share2, Plus, Heart, MessageSquare, Search,
  FileText, FileArchive, CheckCircle2, ShieldAlert, Sparkles, Send, Tag, ExternalLink
} from 'lucide-react';
import { api } from '../services/api.ts';
import { ShareOut, ShareCommentOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

// 兜底分类：后端不可达时使用（真实值由 /api/shares/categories 下发）
const FALLBACK_CATEGORIES = ['期末复习题', '考研考证', '课件PPT', '实验报告模版', '竞赛真题', '开源代码'];

const ShareFeed: React.FC = () => {
  const navigate = useNavigate();
  const { user, openReport } = useAuth();
  const { success, error } = useToast();

  const [shares, setShares] = useState<ShareOut[]>([]);
  const [categories, setCategories] = useState<string[]>(['全部', ...FALLBACK_CATEGORIES]);
  const [selectedCat, setSelectedCat] = useState('全部');
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState(FALLBACK_CATEGORIES[0]);
  const [description, setDescription] = useState('');
  const [fileUrl, setFileUrl] = useState('');
  const [tagsInput, setTagsInput] = useState('高等数学, 历年真题, 98分学霸手写');
  const [submitting, setSubmitting] = useState(false);

  // Active resource comments drawer
  const [activeShareId, setActiveShareId] = useState<string | null>(null);
  const [comments, setComments] = useState<ShareCommentOut[]>([]);
  const [commentContent, setCommentContent] = useState('');

  const fetchShares = async () => {
    setLoading(true);
    try {
      const res = await api.shares.list({
        keyword: keyword.trim() || undefined,
        category: selectedCat === '全部' ? undefined : selectedCat
      });
      if (res.code === 0 && res.data) {
        setShares(res.data.items || []);
      }
    } catch {
      // Mock fallback
    } finally {
      setLoading(false);
    }
  };

  // 动态拉取资料分类（后台可配置，含 school.yaml 兜底）；失败则用前端兜底常量
  useEffect(() => {
    (async () => {
      try {
        const res = await api.shares.categories();
        if (res.code === 0 && res.data?.categories?.length) {
          setCategories(['全部', ...res.data.categories]);
        }
      } catch {
        // 保留兜底分类
      }
    })();
  }, []);

  useEffect(() => {
    fetchShares();
  }, [selectedCat]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchShares();
  };

  const handleLike = async (shareId: string) => {
    try {
      const res = await api.shares.like(shareId);
      if (res.code === 0) {
        setShares((prev) =>
          prev.map((s) => (s.id === shareId ? { ...s, likes: (s.likes || 0) + 1 } : s))
        );
        success('已点赞该共享资料！');
      }
    } catch {
      // Ignored
    }
  };

  const handleOpenResource = async (share: ShareOut) => {
    try {
      const res = await api.shares.download(share.id);
      const url = res.data?.download_url || share.file_url;
      // 只允许 http(s) 链接，防止后端配置异常时把 javascript:/data: 之类地址交给浏览器
      if (!url || !/^https?:\/\//i.test(url)) {
        error('资源链接无效，请联系分享者');
        return;
      }
      setShares((prev) =>
        prev.map((s) => (s.id === share.id ? { ...s, downloads: (s.downloads || 0) + 1 } : s))
      );
      success(`正在打开《${share.title}》的外部链接`);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch {
      error('打开资源失败');
    }
  };

  const handleOpenComments = async (shareId: string) => {
    setActiveShareId(shareId);
    try {
      const res = await api.shares.getComments(shareId);
      if (res.code === 0 && res.data) {
        setComments(res.data.items || []);
      }
    } catch {
      // Mock
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeShareId || !commentContent.trim()) return;

    try {
      const res = await api.shares.addComment(activeShareId, commentContent.trim());
      if (res.code === 0 && res.data) {
        success('讨论留言已发布！');
        setComments((prev) => [...prev, res.data]);
        setCommentContent('');
      }
    } catch {
      error('发布留言失败');
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !fileUrl.trim()) {
      error('请填写资源标题和外部链接');
      return;
    }
    if (!/^https?:\/\//i.test(fileUrl.trim())) {
      error('资源链接需以 http:// 或 https:// 开头');
      return;
    }

    setSubmitting(true);
    try {
      const tags = tagsInput
        .split(/[,， ]+/)
        .map((t) => t.trim())
        .filter(Boolean);

      const res = await api.shares.create({
        title: title.trim(),
        category,
        description: description.trim(),
        file_url: fileUrl.trim(),
        tags
      });

      if (res.code === 0) {
        success('资料发布成功！感谢您为校园开源知识库添砖加瓦');
        setShowUploadModal(false);
        setTitle('');
        setDescription('');
        fetchShares();
      } else {
        error(res.message || '发布失败');
      }
    } catch {
      error('提交出现异常');
    } finally {
      setSubmitting(false);
    }
  };

  const inputCls =
    'w-full px-3.5 py-2.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft focus:ring-2 focus:ring-ink/10 outline-none transition-colors';

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-24">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="mono-label text-zone-share tracking-mono mb-1">SHARE · 资源共享</div>
          <h1 className="text-heading-1 text-ink tracking-tight">学术资源与资料共享</h1>
          <p className="text-body-2 text-steel mt-0.5">
            历年期末真题、考研笔记、实验代码与高分复习提纲，开放互助交流
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors active:scale-95 shrink-0"
        >
          <Plus className="w-4 h-4" />
          分享资源链接
        </button>
      </div>

      {/* Search and Category Filter */}
      <div className="bg-surface p-4 rounded-lg border border-hairline shadow-surface space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-steel w-4 h-4" />
            <input
              type="text"
              placeholder="搜索高数复习、离散数学、考研408、英语六级真题..."
              className="w-full pl-10 pr-4 py-2.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft focus:ring-2 focus:ring-ink/10 outline-none transition-colors"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono transition-colors"
          >
            检索
          </button>
        </form>

        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCat(cat)}
              className={`whitespace-nowrap px-3.5 py-1.5 mono-label uppercase tracking-mono rounded-lg transition-colors ${
                selectedCat === cat
                  ? 'bg-zone-share text-surface'
                  : 'bg-panel text-steel hover:text-ink'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Share List Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((n) => (
            <div key={n} className="soft-card animate-pulse space-y-4">
              <div className="h-5 bg-panel rounded w-2/3"></div>
              <div className="h-12 bg-panel rounded"></div>
            </div>
          ))}
        </div>
      ) : shares.length === 0 ? (
        <div className="bg-surface rounded-lg p-16 text-center border border-hairline space-y-4">
          <FileText className="w-12 h-12 text-steel mx-auto" />
          <h3 className="text-heading-3 text-ink">暂无相关资源分享</h3>
          <p className="text-body-2 text-steel">快来分享你的学习资源链接吧！</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {shares.map((share) => (
            <div
              key={share.id}
              role="link"
              tabIndex={0}
              onClick={() => navigate(`/share/${share.id}`)}
              onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/share/${share.id}`); }}
              className="group bg-surface rounded-lg p-6 sm:p-7 border border-hairline hover:border-zone-share hover:shadow-md-4 cursor-pointer transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-zone-share/10 flex items-center justify-center text-zone-share shrink-0 border border-zone-share/20">
                      <FileArchive className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[11px] font-mono font-bold text-zone-share bg-zone-share/10 px-2 py-0.5 rounded-lg tracking-mono">
                        {share.category}
                      </span>
                      <h3 className="text-heading-3 text-ink group-hover:text-zone-share transition-colors mt-1">
                        {share.title}
                      </h3>
                    </div>
                  </div>

                  <span className="text-caption font-bold text-steel bg-panel px-2.5 py-1 rounded-lg font-mono shrink-0">
                    外部链接
                  </span>
                </div>

                <p className="text-body-2 text-steel leading-relaxed bg-panel/40 p-3.5 rounded-lg border border-hairline">
                  {share.description}
                </p>

                {/* Tags */}
                {share.tags && share.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {share.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2.5 py-0.5 bg-panel text-steel text-[11px] font-mono rounded-lg"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Action bar */}
              <div className="pt-4 border-t border-hairline flex items-center justify-between">
                <div className="flex items-center gap-4 text-body-2 text-steel">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleLike(share.id); }}
                    className="flex items-center gap-1 hover:text-error font-semibold transition-colors"
                  >
                    <Heart className="w-4 h-4 text-error" />
                    <span>{share.likes || 0}</span>
                  </button>

                  <button
                    onClick={(e) => { e.stopPropagation(); handleOpenComments(share.id); }}
                    className="flex items-center gap-1 hover:text-zone-share font-semibold transition-colors"
                  >
                    <MessageSquare className="w-4 h-4 text-zone-share" />
                    <span>讨论</span>
                  </button>

                  <button
                    onClick={(e) => { e.stopPropagation(); openReport('share', share.id, share.title); }}
                    className="text-steel hover:text-error flex items-center gap-1 text-caption font-mono"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    举报
                  </button>
                </div>

                <button
                  onClick={(e) => { e.stopPropagation(); handleOpenResource(share); }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-hover text-surface shadow-md-2 rounded-md md-button-text transition-colors active:scale-95"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>访问链接 ({share.downloads || 0})</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate/70">
          <div className="bg-surface rounded-lg max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-elevate border border-hairline max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-heading-3 text-ink">分享校园学习资源</h3>
              <button onClick={() => setShowUploadModal(false)} className="text-steel hover:text-ink text-xl font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">资料标题 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 2025-2026学年高等数学A期末复习题精解(附详细解析)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className={inputCls}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block mono-label text-steel tracking-mono">资料类别 *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className={inputCls}
                  >
                    {categories.filter((c) => c !== '全部').map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">标签分类 (逗号分隔)</label>
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="高等数学, 期末题, 笔记"
                  className={inputCls}
                />
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">资源链接（网盘 / 课程站 / 开源仓库）*</label>
                <input
                  type="url"
                  required
                  placeholder="https://..."
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  className={inputCls + ' font-mono text-xs'}
                />
              </div>

              <div className="space-y-1">
                <label className="block mono-label text-steel tracking-mono">内容简介 / 适用专业与建议 *</label>
                <textarea
                  rows={4}
                  required
                  placeholder="简述该资料的适用年级、重点章节及学习方法建议..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-3.5 bg-surface border-0 rounded-lg shadow-slate text-body-1 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft outline-none transition-colors"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="flex-1 py-3 border border-hairline text-steel rounded-lg text-body-2 font-semibold mono-label uppercase tracking-mono hover:bg-panel transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-3 bg-primary hover:bg-primary-hover text-surface shadow-soft rounded-lg text-body-2 font-bold mono-label uppercase tracking-mono disabled:opacity-50 transition-colors"
                >
                  {submitting ? '上传中...' : '确认发布'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resource Comments Drawer/Modal */}
      {activeShareId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate/70">
          <div className="bg-surface rounded-lg max-w-lg w-full p-6 space-y-4 shadow-elevate border border-hairline max-h-[85vh] flex flex-col">
            <div className="flex justify-between items-center pb-2 border-b border-hairline">
              <h3 className="text-heading-3 text-ink">学术资料讨论交流区</h3>
              <button onClick={() => setActiveShareId(null)} className="text-steel hover:text-ink text-xl font-bold">
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {comments.length === 0 ? (
                <div className="p-8 text-center text-steel text-body-2">
                  暂无讨论留言，发表你的学习体会或向上传者致谢吧！
                </div>
              ) : (
                comments.map((c) => (
                  <div key={c.id} className="p-3.5 bg-panel/40 rounded-lg border border-hairline space-y-1">
                    <div className="flex items-center justify-between text-body-2 font-mono">
                      <span className="font-bold text-ink">{c.user_nickname || '校友同学'}</span>
                      <span className="text-caption text-steel">{new Date(c.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-body-2 text-slate">{c.content}</p>
                  </div>
                ))
              )}
            </div>

            <form onSubmit={handleAddComment} className="pt-2 flex gap-2">
              <input
                type="text"
                required
                placeholder="留下您的疑问、纠错或感谢..."
                value={commentContent}
                onChange={(e) => setCommentContent(e.target.value)}
                className="flex-1 px-3.5 py-2.5 bg-surface border-0 rounded-lg shadow-slate text-body-2 text-ink placeholder:text-steel focus:bg-white focus:shadow-soft outline-none transition-colors"
              />
              <button
                type="submit"
                className="px-4 py-2.5 bg-primary text-surface shadow-soft rounded-lg mono-label uppercase tracking-mono hover:bg-primary-hover transition-colors"
              >
                发表
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ShareFeed;
