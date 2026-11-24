import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Star, ThumbsUp, Sparkles, BookOpen, User,
  MessageSquare, Plus, CheckCircle, ShieldAlert, Award
} from 'lucide-react';
import { api } from '../services/api.ts';
import { CourseOut, CourseReviewOut } from '../types.ts';
import { summarizeCourseReviews, getAiStatus, isCapabilityAvailable } from '../services/aiService.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { PassCard } from '../components/ui';

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
  // AI 能力级开关：未配置 Key / 后台关闭时隐藏「AI 智能选课画像」整块
  const [aiEnabled, setAiEnabled] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchCourseAndReviews = async () => {
      setLoading(true);
      // P3：切课程先清空上一门课的 AI 画像，避免串课显示旧文案
      setAiSummary('');
      setReviews([]);
      try {
        const cRes = await api.courses.get(id);
        if (cRes.code === 0 && cRes.data) {
          setCourse(cRes.data);
        }
        const rRes = await api.courses.getReviews(id);
        if (rRes.code === 0 && rRes.data) {
          const revList = rRes.data.items || [];
          setReviews(revList);

          // Trigger AI summary（能力级 gating：未配置 Key 不请求、不渲染）
          const status = await getAiStatus();
          const on = isCapabilityAvailable(status, 'course_summary');
          setAiEnabled(on);
          if (on && revList.length > 0) {
            setSummarizing(true);
            const reviewTexts = revList.map((r) => r.content);
            summarizeCourseReviews(reviewTexts)
              .then((sum) => setAiSummary(sum || '暂无总结'))
              .catch(() => setAiSummary(''))
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
      if (res.code === 0 && res.data) {
        // 以服务端返回的计数为准（P2-22 起为真实落库端点）
        setReviews((prev) =>
          prev.map((r) => (r.id === reviewId ? { ...r, helpful_count: res.data!.helpful_count } : r))
        );
        success('已点赞该评价，感谢您的反馈！');
      }
    } catch {
      // Ignored
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center text-steel">
        <div className="w-10 h-10 border-4 border-ink border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-body-2 mono-label tracking-mono">正在加载课程评价详情...</p>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center space-y-4">
        <h2 className="text-heading-2 text-ink">未找到对应课程</h2>
        <Link to="/courses" className="inline-block px-4 py-2 bg-ink text-surface rounded-sm mono-label uppercase tracking-mono hover:bg-slate transition-colors">
          返回课程列表
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-24">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-steel hover:text-ink mono-label uppercase tracking-mono transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回课程列表
      </button>

      {/* Course Header */}
      <div className="bg-surface rounded-md p-6 sm:p-8 border border-hairline shadow-surface space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 bg-zone-course/10 text-zone-course font-mono font-bold text-xs rounded-sm uppercase tracking-mono">
                {course.code || 'CS-202'}
              </span>
              <span className="text-caption text-steel">{course.department || '计算机学院'}</span>
            </div>
            <h1 className="text-heading-1 text-ink tracking-tight">
              {course.name}
            </h1>
            <p className="text-body-2 text-slate font-medium flex items-center gap-2">
              <User className="w-4 h-4 text-zone-course" />
              授课主讲：{course.instructor || '张伟 教授'}
            </p>
          </div>

          <div className="p-4 bg-zone-course/10 rounded-sm border border-zone-course/20 flex flex-col items-center justify-center min-w-[130px] shrink-0">
            <div className="flex items-center gap-1 text-zone-course">
              <Star className="w-6 h-6 fill-zone-course text-zone-course" />
              <span className="text-3xl font-black font-display tabular-nums">{course.rating ? Number(course.rating).toFixed(1) : '4.8'}</span>
            </div>
            <span className="mono-label text-zone-course tracking-mono mt-1">综合评分 (满分5分)</span>
          </div>
        </div>

        <p className="text-body-2 text-slate leading-relaxed bg-panel/40 p-4 rounded-sm border border-hairline">
          {course.description || '本课程系统讲解学科核心思想，配备丰富实验课与讨论班，深受全校同学好评。'}
        </p>

        <div className="flex items-center justify-between pt-2">
          <span className="text-caption text-steel font-mono">累计收录 {reviews.length} 条真实学长学姐评课</span>
          <Link
            to={`/courses/review?course_id=${course.id}`}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-ink hover:bg-slate text-surface rounded-sm mono-label uppercase tracking-mono transition-colors active:scale-95"
          >
            <Plus className="w-4 h-4" />
            撰写评价
          </Link>
        </div>
      </div>

      {/* AI Review Summary —— 仅在 AI 能力可用时渲染（未配置 Key 时整块隐藏） */}
      {aiEnabled && (
      <div className="bg-slate rounded-md p-6 sm:p-8 text-surface space-y-4 shadow-surface border border-slate relative overflow-hidden">
        <div className="relative z-10 flex items-center gap-2">
          <div className="p-2 bg-ink/40 rounded-sm border border-surface/20">
            <Sparkles className="w-5 h-5 text-surface" />
          </div>
          <div>
            <h3 className="text-body-1 font-semibold text-surface">AI 智能选课画像 & 评价提炼</h3>
            <p className="text-caption text-surface/70">基于所有学生真实评价进行语义情感提炼</p>
          </div>
        </div>

        <div className="relative z-10 text-body-2 leading-relaxed text-panel bg-ink/40 p-4 rounded-sm border border-surface/10">
          {summarizing ? (
            <div className="flex items-center gap-2 text-surface/80 animate-pulse text-caption mono-label tracking-mono">
              <div className="w-4 h-4 border-2 border-surface/60 border-t-transparent rounded-full animate-spin"></div>
              正在深度提炼课程考核难易度、作业量及得分率画像...
            </div>
          ) : (
            aiSummary || '暂无足够的评价数据进行 AI 综合画像生成。'
          )}
        </div>
      </div>
      )}

      {/* 课程登机卡：登机牌·航站屏世界签名组件（PassCard）落地 */}
      <PassCard
        title="COURSE · 选课登机卡"
        seq={`ID ${course.id}`}
        segments={[
          { label: '课程代码', value: course.code || 'CS-202', mono: true },
          { label: '授课教师', value: course.instructor || '张伟 教授' },
          { label: '所属院系', value: course.department || '计算机学院' },
          { label: '综合评分', value: `${Number(course.rating || 4.8).toFixed(1)} / 5.0`, mono: true }
        ]}
        scanCode={course.code || String(course.id)}
        scanNote="凭课程代码登记选课意向"
        footer={
          <Link
            to={`/courses/review?course_id=${course.id}`}
            className="mono-label inline-flex items-center gap-1.5 text-zone-course hover:text-ink transition-colors"
          >
            <Plus className="w-4 h-4" />
            前往评课登机口
          </Link>
        }
      />

      {/* Reviews List */}
      <div className="space-y-4">
        <h3 className="text-heading-2 text-ink flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-zone-course" />
          学长学姐评价 ({reviews.length})
        </h3>

        <div className="space-y-4">
          {reviews.map((rev) => (
            <div
              key={rev.id}
              className="bg-surface rounded-md p-6 border border-hairline shadow-surface space-y-4 hover:border-zone-course transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-sm bg-panel flex items-center justify-center font-bold text-zone-course border border-hairline">
                    {rev.user_nickname?.charAt(0) || '校'}
                  </div>
                  <div>
                    <span className="font-bold text-ink text-body-1 block">
                      {rev.user_nickname || '匿名校友'}
                    </span>
                    <span className="text-caption text-steel font-mono">
                      {rev.created_at ? new Date(rev.created_at).toLocaleDateString() : '近日评价'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1 px-2 py-1 bg-zone-course/10 rounded-sm text-zone-course mono-label tracking-mono">
                  <Star className="w-3.5 h-3.5 fill-zone-course text-zone-course" />
                  <span>{rev.rating} 分</span>
                </div>
              </div>

              {/* Sub ratings if available */}
              {(rev.workload || rev.grading_policy) && (
                <div className="flex flex-wrap gap-2 text-caption mono-label tracking-mono">
                  {rev.workload && (
                    <span className="px-2.5 py-1 bg-panel text-slate rounded-sm border border-hairline">
                      作业负荷: <strong className="text-ink">{rev.workload}</strong>
                    </span>
                  )}
                  {rev.grading_policy && (
                    <span className="px-2.5 py-1 bg-panel text-slate rounded-sm border border-hairline">
                      给分偏好: <strong className="text-ink">{rev.grading_policy}</strong>
                    </span>
                  )}
                </div>
              )}

              <p className="text-body-2 text-slate leading-relaxed whitespace-pre-wrap">
                {rev.content}
              </p>

              <div className="flex items-center justify-between pt-3 border-t border-hairline text-caption mono-label tracking-mono">
                <button
                  onClick={() => handleLikeReview(rev.id)}
                  className="flex items-center gap-1.5 text-steel hover:text-zone-course font-semibold px-3 py-1.5 rounded-sm hover:bg-zone-course/10 transition-colors"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  <span>对我有用 ({rev.helpful_count || 0})</span>
                </button>

                <button
                  onClick={() => openReport('comment', rev.id, `课程评价: ${rev.content.slice(0, 20)}...`)}
                  className="text-steel hover:text-error flex items-center gap-1 transition-colors"
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
