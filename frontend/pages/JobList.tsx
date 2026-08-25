import React, { useState, useEffect } from 'react';
import {
  Briefcase, Plus, Search, MapPin, DollarSign, Clock,
  Building, CheckCircle2, Send, Tag, Phone, Mail
} from 'lucide-react';
import { api, formatPrice, toCents } from '../services/api.ts';
import { JobOut, SalaryType } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';

const categories = ['全部岗位', '助教/助管', '家教辅导', '校园代理', '技术开发', '设计剪辑', '活动执行', '文案编辑'];

const JobList: React.FC = () => {
  const { user } = useAuth();
  const { success, error } = useToast();

  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [selectedCat, setSelectedCat] = useState('全部岗位');
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);

  // Post modal
  const [showPostModal, setShowPostModal] = useState(false);
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [salaryYuan, setSalaryYuan] = useState('150');
  const [salaryType, setSalaryType] = useState<SalaryType>(SalaryType.Daily);
  const [location, setLocation] = useState('校内图书馆 / 线上');
  const [contact, setContact] = useState('');
  const [requirements, setRequirements] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Apply dialog
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null);
  const [applyMessage, setApplyMessage] = useState('');

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await api.jobs.list({
        keyword: keyword.trim() || undefined,
        category: selectedCat === '全部岗位' ? undefined : selectedCat
      });
      if (res.code === 0 && res.data) {
        setJobs(res.data.items || []);
      }
    } catch {
      // Mock
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [selectedCat]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !company.trim() || !salaryYuan || !contact.trim()) {
      error('请完整填写岗位招聘需求');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.jobs.create({
        title: title.trim(),
        company: company.trim(),
        salary_cents: toCents(parseFloat(salaryYuan)),
        salary_type: salaryType,
        location: location.trim(),
        contact: contact.trim(),
        requirements: requirements.trim(),
        description: description.trim()
      });

      if (res.code === 0) {
        success('兼职招聘信息发布成功！');
        setShowPostModal(false);
        setTitle('');
        setCompany('');
        setDescription('');
        fetchJobs();
      } else {
        error(res.message || '发布失败');
      }
    } catch {
      error('提交出现异常');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApplyJob = async (jobId: string) => {
    if (!applyMessage.trim()) {
      error('请填写您的基本信息与可工作时间');
      return;
    }

    try {
      const res = await api.jobs.apply(jobId, applyMessage.trim());
      if (res.code === 0) {
        success('兼职求职意向已发送至招聘方！请保持手机/微信畅通');
        setApplyingJobId(null);
        setApplyMessage('');
      } else {
        error(res.message || '投递失败');
      }
    } catch {
      error('投递异常');
    }
  };

  const getSalaryLabel = (cents: number, type: SalaryType) => {
    const yuan = formatPrice(cents);
    switch (type) {
      case SalaryType.Hourly:
        return `¥${yuan} / 小时`;
      case SalaryType.Daily:
        return `¥${yuan} / 天`;
      case SalaryType.Monthly:
        return `¥${yuan} / 月`;
      case SalaryType.OneTime:
        return `¥${yuan} / 次`;
      default:
        return `¥${yuan}`;
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-24">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">校内兼职与勤工助学</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            官方助教、校内行政助理、家教辅导与高性价比实习
          </p>
        </div>

        <button
          onClick={() => setShowPostModal(true)}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-700 text-white rounded-2xl font-bold shadow-lg shadow-violet-200 transition-all active:scale-95 shrink-0"
        >
          <Plus className="w-5 h-5" />
          发布兼职招聘
        </button>
      </div>

      {/* Search and Category Filter */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input
              type="text"
              placeholder="搜索岗位、工作地点、雇主名称（如：计算机助教、初三英语家教）..."
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:bg-white focus:border-violet-600 outline-none transition-all"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="px-6 py-3 bg-slate-900 text-white rounded-2xl text-sm font-bold"
          >
            搜索
          </button>
        </form>

        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pt-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCat(cat)}
              className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedCat === cat
                  ? 'bg-violet-600 text-white shadow-sm'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-100'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Jobs Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((n) => (
            <div key={n} className="bg-white rounded-3xl p-6 border border-slate-200 animate-pulse space-y-4">
              <div className="h-5 bg-slate-200 rounded w-1/2"></div>
              <div className="h-16 bg-slate-100 rounded"></div>
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="bg-white rounded-3xl p-16 text-center border border-slate-200 space-y-4">
          <Briefcase className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-lg font-bold text-slate-700">暂无符合条件的兼职岗位</h3>
          <p className="text-xs text-slate-400">请尝试更换搜索词或选择全部岗位</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="group bg-white rounded-3xl p-6 sm:p-7 border border-slate-200 hover:border-violet-300 hover:shadow-xl hover:shadow-violet-500/5 transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-xl font-black text-slate-900 group-hover:text-violet-600 transition-colors">
                      {job.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                      <Building className="w-3.5 h-3.5 text-slate-400" />
                      <span className="font-semibold text-slate-700">{job.company}</span>
                      <span>•</span>
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      <span>{job.location}</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-lg font-black text-violet-600">
                      {getSalaryLabel(job.salary_cents, job.salary_type)}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3.5 rounded-2xl border border-slate-100">
                  {job.description}
                </p>

                {job.requirements && (
                  <div className="text-xs text-slate-600">
                    <span className="font-bold text-slate-700">任职要求：</span>
                    {job.requirements}
                  </div>
                )}
              </div>

              {/* Action bar */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <div className="text-[11px] text-slate-400">
                  联系方式：{job.contact}
                </div>

                <button
                  onClick={() => setApplyingJobId(job.id)}
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-xs font-bold shadow-md shadow-violet-100 transition-all active:scale-95"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>立即投递意向</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Post Job Modal */}
      {showPostModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-slate-900">发布校园兼职与实习招聘</h3>
              <button onClick={() => setShowPostModal(false)} className="text-slate-400 hover:text-slate-600 text-xl font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateJob} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">岗位名称 *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 计算机学院《算法导论》助教 (批改作业与答疑)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">招聘主体 / 老师 / 企业 *</label>
                  <input
                    type="text"
                    required
                    placeholder="例如: 计算机科学系教研室"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">工作地点 *</label>
                  <input
                    type="text"
                    required
                    placeholder="例如: 计电楼302 / 远程线上"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">薪资标准 (元) *</label>
                  <input
                    type="number"
                    required
                    value={salaryYuan}
                    onChange={(e) => setSalaryYuan(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">结算周期 *</label>
                  <select
                    value={salaryType}
                    onChange={(e) => setSalaryType(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                  >
                    <option value={SalaryType.Hourly}>按小时结算</option>
                    <option value={SalaryType.Daily}>按日结算</option>
                    <option value={SalaryType.Monthly}>按月结算</option>
                    <option value={SalaryType.OneTime}>按次 / 项目结算</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">雇主联系方式 (手机/微信/邮箱) *</label>
                <input
                  type="text"
                  required
                  placeholder="例如: 微信号: cs_tutor_recruit / 邮箱: job@example.edu.cn"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">岗位职责描述 *</label>
                <textarea
                  rows={3}
                  required
                  placeholder="详细说明具体工作内容、每周所需工作时长及要求..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">任职要求</label>
                <input
                  type="text"
                  placeholder="例如: 限大三及以上 / 算法导论成绩90分以上 / 细致负责"
                  value={requirements}
                  onChange={(e) => setRequirements(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowPostModal(false)}
                  className="flex-1 py-3 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-3 bg-violet-600 hover:bg-violet-700 text-white rounded-xl text-sm font-bold shadow-md shadow-violet-100 disabled:opacity-50"
                >
                  {submitting ? '发布中...' : '确认发布岗位'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Apply Modal */}
      {applyingJobId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-100">
            <h3 className="text-lg font-bold text-slate-900">投递兼职意向</h3>
            <p className="text-xs text-slate-500">简要附上您的专业年级、相关特长及每周可出勤时间：</p>
            <textarea
              rows={4}
              required
              placeholder="例如：您好，我是计算机大三学生张三，曾获校二等奖学金，算法课成绩94分，每周二、四下午及周末均可线下答疑！联系电话：13800138000"
              value={applyMessage}
              onChange={(e) => setApplyMessage(e.target.value)}
              className="w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:border-violet-600 outline-none"
            />
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setApplyingJobId(null)}
                className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => handleApplyJob(applyingJobId)}
                className="flex-1 py-2.5 bg-violet-600 text-white rounded-xl text-xs font-bold shadow-md shadow-violet-100"
              >
                确认发送投递
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobList;
