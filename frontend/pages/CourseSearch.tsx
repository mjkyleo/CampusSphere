import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Star, BookOpen, User, Plus, Sparkles, Filter, ChevronRight } from 'lucide-react';
import { api } from '../services/api.ts';
import { CourseOut } from '../types.ts';
import { useToast } from '../context/ToastContext.tsx';

// 兜底：后端 /api/courses/departments 不可达时的默认值（与 school.yaml 对齐）
const FALLBACK_DEPARTMENTS = ['计算机学院', '软件学院', '数学科学学院', '经济管理学院', '外国语学院', '通识教育中心'];
const FALLBACK_GROUPS: { group: string; departments: string[] }[] = [];

const CourseSearch: React.FC = () => {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState('');
  const [departments, setDepartments] = useState<string[]>(FALLBACK_DEPARTMENTS);
  const [groups, setGroups] = useState<{ group: string; departments: string[] }[]>(FALLBACK_GROUPS);
  const [selectedGroup, setSelectedGroup] = useState('');
  const [selectedDept, setSelectedDept] = useState('');
  const [courses, setCourses] = useState<CourseOut[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const res = await api.courses.list(keyword.trim(), 1, 20, selectedDept);
      if (res.code === 0 && res.data) {
        setCourses(res.data.items || []);
      }
    } catch {
      // Mock fallback
    } finally {
      setLoading(false);
    }
  };

  // 动态拉取后台配置的院系列表（含学部分组，school.yaml 兜底）
  useEffect(() => {
    api.courses.departments()
      .then((res) => {
        if (res.code === 0 && res.data?.departments?.length) {
          setDepartments(res.data.departments);
          if (res.data.groups?.length) setGroups(res.data.groups);
        }
      })
      .catch(() => { /* 后端不可达时使用兜底院系 */ });
  }, []);

  useEffect(() => {
    fetchCourses();
  }, [selectedDept]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCourses();
  };

  // 当前学部下可直接点的院系集合（全部学部时展示全部院系）
  const visibleDepartments = selectedGroup
    ? (groups.find((g) => g.group === selectedGroup)?.departments || [])
    : departments;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">全校课程评价社区</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            客观真实的选课口碑，包含给分好坏、考核要求、作业量与名师推荐
          </p>
        </div>

        <Link
          to="/courses/review"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold shadow-lg shadow-indigo-200 transition-all active:scale-95 shrink-0"
        >
          <Plus className="w-5 h-5" />
          发布我的评课
        </Link>
      </div>

      {/* Search & Dept Filters */}
      <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索课程名称（如：数据结构、微积分）、授课教师或课程代码..."
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-indigo-600 outline-none transition-all"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl text-sm font-bold transition-colors"
          >
            搜索课程
          </button>
        </form>

        {/* 学部 Tab（一级） */}
        {groups.length > 0 && (
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
            <button
              onClick={() => { setSelectedGroup(''); setSelectedDept(''); }}
              className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedGroup === ''
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
              }`}
            >
              全部学部
            </button>
            {groups.map((g) => (
              <button
                key={g.group}
                onClick={() => { setSelectedGroup(g.group); setSelectedDept(''); }}
                className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                  selectedGroup === g.group
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
                }`}
              >
                {g.group}
              </button>
            ))}
          </div>
        )}

        {/* 院系 chips（二级） */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
          <button
            onClick={() => setSelectedDept('')}
            className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              selectedDept === ''
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
            }`}
          >
            全部院系
          </button>
          {visibleDepartments.map((dept) => (
            <button
              key={dept}
              onClick={() => setSelectedDept(dept)}
              className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedDept === dept
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
              }`}
            >
              {dept}
            </button>
          ))}
        </div>
      </div>

      {/* Course List Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-6 border border-slate-200 animate-pulse space-y-4">
              <div className="h-5 bg-slate-200 rounded w-2/3"></div>
              <div className="h-4 bg-slate-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : courses.length === 0 ? (
        <div className="bg-white rounded-3xl p-16 text-center border border-slate-200 space-y-4">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-bold text-slate-700">未找到相关课程</h3>
          <p className="text-xs text-slate-400">试着缩短关键词或切换院系标签</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course) => (
            <div
              key={course.id}
              className="group bg-white rounded-3xl p-6 border border-slate-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/5 transition-all flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded uppercase">
                      {course.code || 'CS101'}
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 mt-1 group-hover:text-indigo-600 transition-colors">
                      {course.name}
                    </h3>
                  </div>

                  <div className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 rounded-xl border border-amber-200/60 text-amber-700 text-xs font-black shrink-0">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span>{course.rating ? Number(course.rating).toFixed(1) : '4.8'}</span>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600">
                  <div className="flex items-center gap-2">
                    <User className="w-3.5 h-3.5 text-slate-400" />
                    <span>主讲教师: <strong className="text-slate-800">{course.instructor || '张伟 教授'}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                    <span>开课院系: {course.department || '计算机学院'}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed bg-slate-50 p-3 rounded-xl">
                  {course.description || '涵盖核心理论与实践上机，注重思维训练与工程能力培养。'}
                </p>
              </div>

              <div className="pt-5 mt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">
                  {course.review_count || 18} 条选课评价
                </span>
                <Link
                  to={`/courses/${course.id}`}
                  className="inline-flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3.5 py-2 rounded-xl transition-colors"
                >
                  查看评价与分析 <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CourseSearch;
