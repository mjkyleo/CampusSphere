import React, { useState, useEffect } from 'react';
import {
  Share2, Plus, Download, Heart, MessageSquare, Search,
  FileText, FileArchive, CheckCircle2, ShieldAlert, Sparkles, Send, Tag
} from 'lucide-react';
import { api } from '../services/api.ts';
import { ShareOut, ShareCommentOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

// 兜底分类：后端不可达时使用（真实值由 /api/shares/categories 下发）
const FALLBACK_CATEGORIES = ['期末复习题', '考研考证', '课件PPT', '实验报告模版', '竞赛真题', '开源代码'];

const ShareFeed: React.FC = () => {
  const { user, openReport } = useAuth();
  const { success, error, info } = useToast();

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
  const [fileUrl, setFileUrl] = useState('https://campus-resources.example.edu/downloads/cs101-final-exam-key.pdf');
  const [fileSize, setFileSize] = useState('4.2 MB');
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

  const handleDownload = async (share: ShareOut) => {
    try {
      const res = await api.shares.download(share.id);
      if (res.code === 0) {
        setShares((prev) =>
          prev.map((s) => (s.id === share.id ? { ...s, downloads: (s.downloads || 0) + 1 } : s))
        );
        success(`正在启动安全下载通道: 《${share.title}》`);
      }
    } catch {
      error('下载服务异常');
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
      error('请填写完整资料标题及附件链接');
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
        file_size: fileSize.trim(),
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

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-24">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">学术资源与资料共享</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            历年期末真题、考研笔记、实验代码与高分复习提纲，开放互助下载
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold shadow-lg shadow-indigo-200 transition-all active:scale-95 shrink-0"
        >
          <Plus className="w-5 h-5" />
          贡献上传资料
        </button>
      </div>

      {/* Search and Category Filter */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索高数复习、离散数学、考研408、英语六级真题..."
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none transition-all"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-6 py-3 bg-slate-900 text-white rounded-2xl text-sm font-bold"
          >
            检索
          </button>
        </form>

        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCat(cat)}
              className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedCat === cat
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Share List Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-6 border border-slate-200 animate-pulse space-y-4">
              <div className="h-5 bg-slate-200 rounded w-2/3"></div>
              <div className="h-12 bg-slate-100 rounded"></div>
            </div>
          ))}
        </div>
      ) : shares.length === 0 ? (
        <div className="bg-white rounded-3xl p-16 text-center border border-slate-200 space-y-4">
          <FileText className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-bold text-slate-700">暂无相关资源分享</h3>
          <p className="text-xs text-slate-400">快来上传分享你的学霸笔记吧！</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {shares.map((share) => (
            <div
              key={share.id}
              className="group bg-white rounded-3xl p-6 sm:p-7 border border-slate-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600 shrink-0 border border-indigo-100">
                      <FileArchive className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50/80 px-2 py-0.5 rounded">
                        {share.category}
                      </span>
                      <h3 className="text-lg font-black text-slate-900 group-hover:text-indigo-600 transition-colors mt-1">
                        {share.title}
                      </h3>
                    </div>
                  </div>

                  <span className="text-xs font-bold text-slate-400 bg-slate-100 px-2.5 py-1 rounded-xl shrink-0">
                    {share.file_size || '3.5 MB'}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3.5 rounded-2xl border border-slate-100">
                  {share.description}
                </p>

                {/* Tags */}
                {share.tags && share.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {share.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2.5 py-0.5 bg-slate-100 text-slate-600 text-[11px] font-medium rounded-lg"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Action bar */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <button
                    onClick={() => handleLike(share.id)}
                    className="flex items-center gap-1 hover:text-rose-600 font-semibold transition-colors"
                  >
                    <Heart className="w-4 h-4 text-rose-500" />
                    <span>{share.likes || 0}</span>
                  </button>

                  <button
                    onClick={() => handleOpenComments(share.id)}
                    className="flex items-center gap-1 hover:text-indigo-600 font-semibold transition-colors"
                  >
                    <MessageSquare className="w-4 h-4 text-indigo-600" />
                    <span>讨论</span>
                  </button>

                  <button
                    onClick={() => openReport('share', share.id, share.title)}
                    className="text-slate-400 hover:text-rose-600 flex items-center gap-1 text-[11px]"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    举报
                  </button>
                </div>

                <button
                  onClick={() => handleDownload(share)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all active:scale-95"
                >
                  <Download className="w-4 h-4" />
                  <span>下载附件 ({share.downloads || 0})</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-slate-900">贡献上传校园学术资源</h3>
              <button onClick={() => setShowUploadModal(false)} className="text-slate-400 hover:text-slate-600 text-xl font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">资料标题 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 2025-2026学年高等数学A期末复习题精解(附详细解析)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">资料类别 *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                  >
                    {categories.filter((c) => c !== '全部').map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">预估文件大小</label>
                  <input
                    type="text"
                    value={fileSize}
                    onChange={(e) => setFileSize(e.target.value)}
                    placeholder="例如: 5.8 MB"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">标签分类 (逗号分隔)</label>
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="高等数学, 期末题, 笔记"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">资源文件下载链接 / 云盘分享地址 *</label>
                <input
                  type="url"
                  required
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none font-mono text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">内容简介 / 适用专业与建议 *</label>
                <textarea
                  rows={4}
                  required
                  placeholder="简述该资料的适用年级、重点章节及学习方法建议..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-indigo-600 outline-none"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="flex-1 py-3 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold shadow-md shadow-indigo-100 disabled:opacity-50"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-slate-100 max-h-[85vh] flex flex-col">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="font-bold text-slate-900 text-base">学术资料讨论交流区</h3>
              <button onClick={() => setActiveShareId(null)} className="text-slate-400 hover:text-slate-600 text-xl font-bold">
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {comments.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  暂无讨论留言，发表你的学习体会或向上传者致谢吧！
                </div>
              ) : (
                comments.map((c) => (
                  <div key={c.id} className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-800">{c.user_nickname || '校友同学'}</span>
                      <span className="text-[10px] text-slate-400">{new Date(c.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-xs text-slate-600">{c.content}</p>
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
                className="flex-1 px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:border-indigo-600 outline-none"
              />
              <button
                type="submit"
                className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition-colors"
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
