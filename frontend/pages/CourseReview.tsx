import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, Star, BookOpen, Send, Sparkles, AlertCircle } from 'lucide-react';
import { api } from '../services/api.ts';
import { CourseOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

const CourseReview: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error } = useToast();

  const [courses, setCourses] = useState<CourseOut[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState(searchParams.get('course_id') || '');
  const [rating, setRating] = useState(5);
  const [teacherRating, setTeacherRating] = useState(5);
  const [workload, setWorkload] = useState('适中');
  const [gradingPolicy, setGradingPolicy] = useState('给分较好，看重平时');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCourses = async () => {
      const res = await api.courses.list('', 1, 50);
      if (res.code === 0 && res.data) {
        const items = res.data.items || [];
        setCourses(items);
        if (!selectedCourseId && items.length > 0) {
          setSelectedCourseId(items[0].id);
        }
      }
    };
    fetchCourses();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourseId) {
      error('请选择需要评价的课程');
      return;
    }
    if (!content.trim() || content.length < 5) {
      error('请填写详细评语（至少5个字）');
      return;
    }

    setLoading(true);
    try {
      const res = await api.courses.addReview({
        course_id: selectedCourseId,
        rating,
        content: content.trim(),
        teacher_rating: teacherRating,
        workload,
        grading_policy: gradingPolicy
      });

      if (res.code === 0) {
        success('评课已发布！感谢您的真实经验分享');
        navigate(`/courses/${selectedCourseId}`);
      } else {
        error(res.message || '发布评课失败');
      }
    } catch {
      error('提交评课异常');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-20">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-slate-500 hover:text-indigo-600 font-semibold text-sm transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        取消并返回
      </button>

      <div className="bg-white rounded-3xl p-6 sm:p-10 border border-slate-200 shadow-sm space-y-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            发布真实选课评价
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            分享给分、作业量、考核要求与学习建议，帮助更多学弟学妹合理规划选课
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Select Course */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              选择课程 <span className="text-rose-500">*</span>
            </label>
            <select
              value={selectedCourseId}
              onChange={(e) => setSelectedCourseId(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-medium focus:bg-white focus:border-indigo-600 outline-none"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  [{c.code || 'CS'}] {c.name} - {c.instructor || '老师'} ({c.department || '院系'})
                </option>
              ))}
            </select>
          </div>

          {/* Rating stars */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 p-5 bg-slate-50 rounded-2xl border border-slate-100">
            {/* Overall Rating */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-700 uppercase">
                课程综合推荐度: <span className="text-amber-600 font-black text-base ml-1">{rating} 星</span>
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    type="button"
                    key={star}
                    onClick={() => setRating(star)}
                    className="p-1 hover:scale-125 transition-transform"
                  >
                    <Star
                      className={`w-7 h-7 ${
                        star <= rating ? 'fill-amber-400 text-amber-400' : 'text-slate-300'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Teacher Rating */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-700 uppercase">
                教师授课清晰度: <span className="text-amber-600 font-black text-base ml-1">{teacherRating} 星</span>
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    type="button"
                    key={star}
                    onClick={() => setTeacherRating(star)}
                    className="p-1 hover:scale-125 transition-transform"
                  >
                    <Star
                      className={`w-7 h-7 ${
                        star <= teacherRating ? 'fill-amber-400 text-amber-400' : 'text-slate-300'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Workload and Grading select */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                作业与项目负荷
              </label>
              <select
                value={workload}
                onChange={(e) => setWorkload(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-medium focus:bg-white focus:border-indigo-600 outline-none"
              >
                <option value="轻松无负担">轻松无负担（作业极少）</option>
                <option value="适中">适中（每周1-2次小作业）</option>
                <option value="较繁重">较繁重（有大作业/实验报告）</option>
                <option value="极大挑战">极大挑战（硬核爆肝课）</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                期末给分情况
              </label>
              <select
                value={gradingPolicy}
                onChange={(e) => setGradingPolicy(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-medium focus:bg-white focus:border-indigo-600 outline-none"
              >
                <option value="神仙给分 / 普遍高分">神仙给分 / 普遍高分</option>
                <option value="给分较好，看重平时">给分较好，看重平时</option>
                <option value="按标准严格给分">按标准严格给分</option>
                <option value="杀手课 / 挂科率偏高">杀手课 / 挂科率偏高</option>
              </select>
            </div>
          </div>

          {/* Content */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              详细评语与选课建议 <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={6}
              required
              placeholder="分享讲课风格（板书/PPT/互动）、点名频率、期中期末题型、避坑指南及刷题建议..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm leading-relaxed focus:bg-white focus:border-indigo-600 outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-base shadow-xl shadow-indigo-200 transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
            {loading ? '正在发布...' : '提交我的评课'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default CourseReview;
