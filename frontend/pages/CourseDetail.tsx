import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Star, ThumbsUp, Sparkles, BookOpen, User,
  MessageSquare, Plus, CheckCircle, ShieldAlert, Award
} from 'lucide-react';
import { api } from '../services/api.ts';
import { CourseOut, CourseReviewOut } from '../types.ts';
import { summarizeCourseReviews } from '../services/geminiService.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

const CourseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, openReport } = useAuth();
  const { success, error, info } = useToast();

  const [course, setCourse] = useState<CourseOut | null>(null);
  const [reviews, setReviews] = useState<CourseReviewOut[]>([]);
  const [aiSummary, setAiSummary] = useState<string>('');
  const [summarizing, setSummarizing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchCourseAndReviews = async () => {
      setLoading(true);
      try {
        const cRes = await api.courses.get(id);
        if (cRes.code === 0 && cRes.data) {
          setCourse(cRes.data);
        }
        const rRes = await api.courses.getReviews(id);
        if (rRes.code === 0 && rRes.data) {
          const revList = rRes.data.items || [];
          setReviews(revList);

          // Trigger AI summary
          if (revList.length > 0) {
            setSummarizing(true);
            const reviewTexts = revList.map((r) => r.content);
            summarizeCourseReviews(reviewTexts)
              .then((sum) => setAiSummary(sum || '暂无总结'))
              .finally(() => setSummarizing(false));
          }
        }
      } catch {
        // Mock fallback
      } finally {
        setLoading(false);
      }
    };

    fetchCourseAndReviews();
  }, [id]);

  const handleLikeReview = async (reviewId: string) => {
    if (!id) return;
    try {
      const res = await api.courses.likeReview(id, reviewId);
      if (res.code === 0) {
        setReviews((prev) =>
          prev.map((r) => (r.id === reviewId ? { ...r, helpful_count: (r.helpful_count || 0) + 1 } : r))
        );
        success('已点赞该评价，感谢您的反馈！');
      }
    } catch {
      // Ignored
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center text-slate-400">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-sm">正在加载课程评价详情...</p>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-700">未找到对应课程</h2>
        <Link to="/courses" className="inline-block px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold">
          返回课程列表
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-24">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-slate-500 hover:text-indigo-600 font-semibold text-sm transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回课程列表
      </button>

      {/* Course Header Banner */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-indigo-50 text-indigo-700 font-bold text-xs rounded-xl uppercase">
                {course.code || 'CS-202'}
              </span>
              <span className="text-xs text-slate-400 font-medium">{course.department || '计算机学院'}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              {course.name}
            </h1>
            <p className="text-sm text-slate-600 font-medium flex items-center gap-2">
              <User className="w-4 h-4 text-indigo-600" />
              授课主讲：{course.instructor || '张伟 教授'}
            </p>
          </div>

          <div className="p-4 bg-amber-50/80 rounded-2xl border border-amber-200/60 flex flex-col items-center justify-center min-w-[130px] shrink-0">
            <div className="flex items-center gap-1 text-amber-600">
              <Star className="w-6 h-6 fill-amber-400 text-amber-400" />
              <span className="text-3xl font-black">{course.rating ? Number(course.rating).toFixed(1) : '4.8'}</span>
            </div>
            <span className="text-[11px] text-amber-700 font-bold mt-1">综合评分 (满分5分)</span>
          </div>
        </div>

        <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100">
          {course.description || '本课程系统讲解学科核心思想，配备丰富实验课与讨论班，深受全校同学好评。'}
        </p>

        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-slate-400 font-medium">累计收录 {reviews.length} 条真实学长学姐评课</span>
          <Link
            to={`/courses/review?course_id=${course.id}`}
            className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" />
            撰写评价
          </Link>
        </div>
      </div>

      {/* AI Review Summary Box */}
      <div className="bg-gradient-to-br from-indigo-900 via-slate-900 to-indigo-950 rounded-3xl p-6 sm:p-8 text-white space-y-4 shadow-xl border border-indigo-800/40 relative overflow-hidden">
        <div className="relative z-10 flex items-center gap-2">
          <div className="p-2 bg-indigo-500/20 backdrop-blur-md rounded-xl border border-indigo-400/30">
            <Sparkles className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">AI 智能选课画像 & 评价提炼</h3>
            <p className="text-xs text-indigo-200">基于所有学生真实评价进行语义情感提炼</p>
          </div>
        </div>

        <div className="relative z-10 text-sm leading-relaxed text-slate-200 bg-white/5 p-4 rounded-2xl border border-white/10">
          {summarizing ? (
            <div className="flex items-center gap-2 text-indigo-200 animate-pulse text-xs">
              <div className="w-4 h-4 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin"></div>
              正在深度提炼课程考核难易度、作业量及得分率画像...
            </div>
          ) : (
            aiSummary || '暂无足够的评价数据进行 AI 综合画像生成。'
          )}
        </div>

        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Reviews List */}
      <div className="space-y-4">
        <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-indigo-600" />
          学长学姐评价 ({reviews.length})
        </h3>

        <div className="space-y-4">
          {reviews.map((rev) => (
            <div
              key={rev.id}
              className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4 hover:border-slate-300 transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center font-bold text-indigo-600 border border-slate-200">
                    {rev.user_nickname?.charAt(0) || '校'}
                  </div>
                  <div>
                    <span className="font-bold text-slate-900 text-sm block">
                      {rev.user_nickname || '匿名校友'}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {rev.created_at ? new Date(rev.created_at).toLocaleDateString() : '近日评价'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 rounded-xl text-amber-700 text-xs font-bold">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span>{rev.rating} 分</span>
                </div>
              </div>

              {/* Sub ratings if available */}
              {(rev.workload || rev.grading_policy) && (
                <div className="flex flex-wrap gap-2 text-xs">
                  {rev.workload && (
                    <span className="px-2.5 py-1 bg-slate-50 text-slate-600 rounded-lg border border-slate-200">
                      作业负荷: <strong>{rev.workload}</strong>
                    </span>
                  )}
                  {rev.grading_policy && (
                    <span className="px-2.5 py-1 bg-slate-50 text-slate-600 rounded-lg border border-slate-200">
                      给分偏好: <strong>{rev.grading_policy}</strong>
                    </span>
                  )}
                </div>
              )}

              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {rev.content}
              </p>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                <button
                  onClick={() => handleLikeReview(rev.id)}
                  className="flex items-center gap-1.5 text-slate-500 hover:text-indigo-600 font-semibold px-3 py-1.5 rounded-xl hover:bg-indigo-50 transition-colors"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  <span>对我有用 ({rev.helpful_count || 0})</span>
                </button>

                <button
                  onClick={() => openReport('comment', rev.id, `课程评价: ${rev.content.slice(0, 20)}...`)}
                  className="text-slate-400 hover:text-rose-600 flex items-center gap-1 transition-colors"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  举报
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CourseDetail;
