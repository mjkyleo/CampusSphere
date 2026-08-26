import React, { useState, useEffect } from 'react';
import {
  Users, ShoppingBag, ShieldAlert, Activity, CheckCircle,
  XCircle, Search, ArrowUpRight, TrendingUp, BarChart3,
  FileText, ShieldCheck, RefreshCw, AlertTriangle, Eye,
  Package, Mail, Trash2, ArrowDownCircle, Save, ChevronLeft, ChevronRight,
  Sparkles
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { api, formatPrice } from '../services/api.ts';
import {
  AdminOverviewOut, AdminReportOut, ReportStatus,
  ReportAction,
  ItemOut, ItemStatus, EmailRegisterConfig, ItemReviewConfig, AiConfig
} from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { invalidateAiStatusCache } from '../services/geminiService.ts';

type AdminTab = 'overview' | 'reports' | 'users' | 'items' | 'email' | 'ai' | 'logs';

/** Human-readable labels for item status codes (matching backend ItemStatus enum). */
const itemStatusMap: Record<number, string> = {
  [ItemStatus.OnSale]: '上架中',
  [ItemStatus.OffSale]: '已下架',
  [ItemStatus.Sold]: '已售出',
  [ItemStatus.Reserved]: '已保留',
  [ItemStatus.Pending]: '待审核'
};

const ITEMS_PAGE_SIZE = 10;

const AdminDashboard: React.FC = () => {
  const { admin } = useAuth();
  const { success, error, info } = useToast();

  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [metrics, setMetrics] = useState<AdminOverviewOut | null>(null);
  const [reports, setReports] = useState<AdminReportOut[]>([]);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Item audit state
  const [itemsList, setItemsList] = useState<ItemOut[]>([]);
  const [itemsPage, setItemsPage] = useState(1);
  const [itemsTotal, setItemsTotal] = useState(0);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemActionLoading, setItemActionLoading] = useState<string | null>(null);
  const [itemsStatusFilter, setItemsStatusFilter] = useState<number | undefined>(undefined);
  const [reviewEnabled, setReviewEnabled] = useState(false);
  const [reviewConfigLoading, setReviewConfigLoading] = useState(false);

  // Email config state
  const [emailConfig, setEmailConfig] = useState<EmailRegisterConfig | null>(null);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [emailDomainsInput, setEmailDomainsInput] = useState('');
  const [emailPatternInput, setEmailPatternInput] = useState('');
  const [emailConfigLoading, setEmailConfigLoading] = useState(false);

  // AI 助手配置 state
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiModel, setAiModel] = useState('gemini-2.0-flash');
  const [aiConfigLoading, setAiConfigLoading] = useState(false);

  // Audit log state — derived from reports (processed records)
  const [auditReports, setAuditReports] = useState<AdminReportOut[]>([]);

  // Report resolution dialog state
  const [selectedReport, setSelectedReport] = useState<AdminReportOut | null>(null);
  const [reportAction, setReportAction] = useState<ReportAction>(ReportAction.None);
  const [reportFeedback, setReportFeedback] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // ---- Fetch core admin data (metrics, reports, users) ----
  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [mRes, rRes, uRes] = await Promise.all([
        api.admin.getOverview(),
        api.admin.getReports(),
        api.admin.getUsers()
      ]);

      if (mRes.code === 0 && mRes.data) setMetrics(mRes.data);
      if (rRes.code === 0 && rRes.data) {
        setReports(rRes.data.items || []);
        // Use the same reports data for the audit log tab —
        // the backend has no dedicated audit-log endpoint, so we
        // display processed reports as audit/processing records.
        setAuditReports(rRes.data.items || []);
      }
      if (uRes.code === 0 && uRes.data) setUsersList(uRes.data.items || []);
    } catch {
      // Mock engine fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  // ---- Fetch items for the item audit tab (lazy-loaded, via admin endpoints) ----
  const fetchItems = async (page: number) => {
    setItemsLoading(true);
    setItemsPage(page);
    try {
      const res = await api.admin.adminItems(itemsStatusFilter, page, ITEMS_PAGE_SIZE);
      if (res.code === 0 && res.data) {
        setItemsList(res.data.items || []);
        setItemsTotal(res.data.total || 0);
      }
    } catch {
      // Mock fallback
    } finally {
      setItemsLoading(false);
    }
  };

  // ---- Fetch item review switch (lazy-loaded when the items tab is opened) ----
  const fetchReviewConfig = async () => {
    try {
      const res = await api.admin.getItemReviewConfig();
      if (res.code === 0 && res.data) {
        setReviewEnabled(res.data.enabled ?? false);
      }
    } catch {
      // Mock fallback
    }
  };

  // ---- Save item review switch ----
  const handleSaveReviewConfig = async () => {
    setReviewConfigLoading(true);
    try {
      const res = await api.admin.updateItemReviewConfig({ enabled: reviewEnabled } as ItemReviewConfig);
      if (res.code === 0 && res.data) {
        success(res.data.enabled ? '已开启发布审核（新发布将进入待审核）' : '已关闭发布审核（新发布直接上架）');
        setReviewEnabled(res.data.enabled ?? false);
      } else {
        error(res.message || '审核设置保存失败');
      }
    } catch {
      error('审核设置保存异常');
    } finally {
      setReviewConfigLoading(false);
    }
  };

  // ---- Fetch email config (lazy-loaded when the email tab is opened) ----
  const fetchEmailConfig = async () => {
    try {
      const res = await api.admin.getEmailConfig();
      if (res.code === 0 && res.data) {
        setEmailConfig(res.data);
        setEmailEnabled(res.data.enabled ?? true);
        setEmailDomainsInput((res.data.domains || []).join(', '));
        setEmailPatternInput(res.data.pattern || '');
      }
    } catch {
      // Mock fallback
    }
  };

  // ---- Lazy-load tab-specific data when tabs are first opened ----
  useEffect(() => {
    if (activeTab === 'items' && itemsList.length === 0) {
      fetchItems(1);
      fetchReviewConfig();
    }
    if (activeTab === 'email' && !emailConfig) {
      fetchEmailConfig();
    }
    if (activeTab === 'ai' && !aiConfig) {
      fetchAiConfig();
    }
  }, [activeTab]);

  // ---- Item audit actions (via admin endpoints, bypasses owner checks) ----
  const handleTakeDownItem = async (itemId: string) => {
    setItemActionLoading(itemId);
    try {
      const res = await api.admin.adminUpdateItem(itemId, { status: ItemStatus.OffSale });
      if (res.code === 0) {
        success('物品已下架处理');
        fetchItems(itemsPage);
      } else {
        error(res.message || '下架失败');
      }
    } catch {
      error('下架操作异常');
    } finally {
      setItemActionLoading(null);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    setItemActionLoading(itemId);
    try {
      const res = await api.admin.adminDeleteItem(itemId);
      if (res.code === 0) {
        success('物品已删除');
        fetchItems(itemsPage);
      } else {
        error(res.message || '删除失败');
      }
    } catch {
      error('删除操作异常');
    } finally {
      setItemActionLoading(null);
    }
  };

  const handleApproveItem = async (itemId: string) => {
    setItemActionLoading(itemId);
    try {
      const res = await api.admin.approveItem(itemId);
      if (res.code === 0) {
        success('审核通过，物品已上架');
        fetchItems(itemsPage);
      } else {
        error(res.message || '审核通过失败');
      }
    } catch {
      error('审核操作异常');
    } finally {
      setItemActionLoading(null);
    }
  };

  const handleRejectItem = async (itemId: string) => {
    setItemActionLoading(itemId);
    try {
      const reason = window.prompt('填写拒绝原因（卖家可见）：', '内容不符合平台规范');
      if (reason === null) return;
      const res = await api.admin.rejectItem(itemId, reason);
      if (res.code === 0) {
        success('已拒绝，物品已下架');
        fetchItems(itemsPage);
      } else {
        error(res.message || '审核拒绝失败');
      }
    } catch {
      error('审核操作异常');
    } finally {
      setItemActionLoading(null);
    }
  };

  // ---- Email config save ----
  const handleSaveEmailConfig = async () => {
    setEmailConfigLoading(true);
    try {
      const config: EmailRegisterConfig = {
        enabled: emailEnabled,
        domains: emailDomainsInput
          .split(',')
          .map((d) => d.trim())
          .filter(Boolean),
        pattern: emailPatternInput.trim() || undefined
      };
      const res = await api.admin.updateEmailConfig(config);
      if (res.code === 0 && res.data) {
        success('邮箱注册配置已保存');
        setEmailConfig(res.data);
      } else {
        error(res.message || '配置保存失败');
      }
    } catch {
      error('配置保存异常');
    } finally {
      setEmailConfigLoading(false);
    }
  };

  // ---- Fetch AI config (lazy-loaded when the AI tab is opened) ----
  const fetchAiConfig = async () => {
    try {
      const res = await api.admin.getAiConfig();
      if (res.code === 0 && res.data) {
        setAiConfig(res.data);
        setAiEnabled(res.data.enabled ?? false);
        setAiModel(res.data.model || 'gemini-2.0-flash');
      }
    } catch {
      // Mock fallback
    }
  };

  // ---- Save AI config ----
  const handleSaveAiConfig = async () => {
    setAiConfigLoading(true);
    try {
      const res = await api.admin.updateAiConfig({
        enabled: aiEnabled,
        model: aiModel.trim() || 'gemini-2.0-flash'
      });
      if (res.code === 0 && res.data) {
        success(res.data.enabled ? 'AI 智能助手已开启，前端将实时生效' : 'AI 智能助手已关闭');
        invalidateAiStatusCache(); // 使首页等处的 AI 状态缓存失效，立即按新开关渲染
        setAiEnabled(res.data.enabled ?? false);
        setAiModel(res.data.model || 'gemini-2.0-flash');
        setAiConfig((prev) =>
          prev ? { ...prev, enabled: res.data.enabled, model: res.data.model } : prev
        );
      } else {
        error(res.message || 'AI 配置保存失败');
      }
    } catch {
      error('AI 配置保存异常');
    } finally {
      setAiConfigLoading(false);
    }
  };

  // ---- Report handling ----
  const handleResolveReport = async (status: ReportStatus) => {
    if (!selectedReport) return;
    setActionLoading(true);
    try {
      const res = await api.admin.handleReport(selectedReport.id, {
        status,
        action: reportAction,
        feedback: reportFeedback.trim() || '审核处理完毕'
      });

      if (res.code === 0) {
        success('举报工单已处理完毕并留存审计日志！');
        setSelectedReport(null);
        setReportFeedback('');
        fetchAdminData();
      } else {
        error(res.message || '处理工单失败');
      }
    } catch {
      error('工单操作异常');
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleUserBan = async (userId: string, currentStatus: number) => {
    const nextStatus = currentStatus === 1 ? 0 : 1;
    try {
      const res = await api.admin.updateUserStatus(userId, nextStatus);
      if (res.code === 0) {
        success(nextStatus === 1 ? '用户已解封恢复正常' : '已成功封禁该违规用户');
        fetchAdminData();
      }
    } catch {
      error('用户状态变更失败');
    }
  };

  // Mock trend chart data
  const growthData = [
    { day: '周一', dau: 1240, trades: 180, growth: 12 },
    { day: '周二', dau: 1420, trades: 210, growth: 15 },
    { day: '周三', dau: 1680, trades: 260, growth: 22 },
    { day: '周四', dau: 1590, trades: 245, growth: 18 },
    { day: '周五', dau: 1950, trades: 340, growth: 28 },
    { day: '周六', dau: 2310, trades: 420, growth: 35 },
    { day: '周日', dau: 2180, trades: 390, growth: 31 }
  ];

  const itemsTotalPages = Math.ceil(itemsTotal / ITEMS_PAGE_SIZE);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-24">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-amber-100 text-amber-800 text-xs font-bold rounded-lg flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
              校园后台综合治理控制台
            </span>
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">
            运营与风控管理中枢
          </h1>
        </div>

        <button
          onClick={fetchAdminData}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold shadow-xs transition-colors self-start sm:self-center"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          刷新数据看板
        </button>
      </div>

      {/* Navigation tabs */}
      <div className="flex gap-2 p-1.5 bg-slate-100 rounded-2xl text-xs font-bold overflow-x-auto no-scrollbar">
        {[
          { id: 'overview', label: '指标大盘 & 数据分析', icon: BarChart3 },
          {
            id: 'reports',
            label: `违规举报受理 (${reports.filter((r) => r.status === ReportStatus.Pending).length})`,
            icon: ShieldAlert
          },
          { id: 'users', label: '用户治理 & 封禁', icon: Users },
          { id: 'items', label: '物品审核管理', icon: Package },
          { id: 'email', label: '邮箱注册配置', icon: Mail },
          { id: 'ai', label: 'AI 智能助手', icon: Sparkles },
          { id: 'logs', label: '处理记录与审计', icon: FileText }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as AdminTab)}
            className={`flex items-center gap-2 py-2.5 px-4 rounded-xl transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab 1: Overview & Metrics */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-3xl border border-slate-200 space-y-2 shadow-xs">
              <span className="text-xs font-bold text-slate-400 uppercase">日活跃用户 (DAU)</span>
              <div className="text-2xl sm:text-3xl font-black text-slate-900">
                {metrics?.dau?.toLocaleString() || '2,420'}
              </div>
              <div className="flex items-center gap-1 text-[11px] font-bold text-emerald-600">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>较昨日 +14.2%</span>
              </div>
            </div>

            <div className="bg-white p-5 rounded-3xl border border-slate-200 space-y-2 shadow-xs">
              <span className="text-xs font-bold text-slate-400 uppercase">累计注册学生</span>
              <div className="text-2xl sm:text-3xl font-black text-slate-900">
                {metrics?.total_users?.toLocaleString() || '18,500'}
              </div>
              <div className="text-[11px] text-slate-400 font-medium">覆盖全校 92% 院系</div>
            </div>

            <div className="bg-white p-5 rounded-3xl border border-slate-200 space-y-2 shadow-xs">
              <span className="text-xs font-bold text-slate-400 uppercase">市集发布物品总数</span>
              <div className="text-2xl sm:text-3xl font-black text-slate-900">
                {metrics?.total_items?.toLocaleString() || '3,840'}
              </div>
              <div className="text-[11px] text-indigo-600 font-bold">成交率 68.4%</div>
            </div>

            <div className="bg-white p-5 rounded-3xl border border-slate-200 space-y-2 shadow-xs">
              <span className="text-xs font-bold text-slate-400 uppercase">待审核违规举报</span>
              <div className="text-2xl sm:text-3xl font-black text-rose-600">
                {metrics?.pending_reports || reports.filter((r) => r.status === ReportStatus.Pending).length}
              </div>
              <div className="text-[11px] text-slate-400">平均处理时长 &lt; 15分钟</div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Chart 1: DAU Growth Curve */}
            <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4 shadow-xs">
              <div className="flex justify-between items-center">
                <h3 className="font-bold text-slate-900 text-sm">过去7天日活跃用户 (DAU) 走势</h3>
                <span className="text-xs text-indigo-600 font-bold">单位: 人次</span>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={growthData}>
                    <defs>
                      <linearGradient id="colorDau" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Area type="monotone" dataKey="dau" stroke="#4f46e5" strokeWidth={3} fillOpacity={1} fill="url(#colorDau)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Second-hand Trade Count */}
            <div className="bg-white p-6 rounded-3xl border border-slate-200 space-y-4 shadow-xs">
              <div className="flex justify-between items-center">
                <h3 className="font-bold text-slate-900 text-sm">二手市集每日成交撮合笔数</h3>
                <span className="text-xs text-emerald-600 font-bold">单位: 单</span>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={growthData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Bar dataKey="trades" fill="#10b981" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Reports Moderation */}
      {activeTab === 'reports' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">举报工单处理列表 ({reports.length})</h3>
            <span className="text-xs text-slate-400">支持下架违规内容、封禁用户与驳回虚假举报</span>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-bold">
                  <tr>
                    <th className="p-4">举报类型</th>
                    <th className="p-4">被举报目标</th>
                    <th className="p-4">举报原因与违规描述</th>
                    <th className="p-4">提交时间</th>
                    <th className="p-4">处理状态</th>
                    <th className="p-4 text-right">审核操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {reports.map((report) => (
                    <tr key={report.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="p-4 font-bold text-slate-700">
                        <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-600">
                          {report.target_type}
                        </span>
                      </td>
                      <td className="p-4 font-mono text-indigo-600 font-semibold truncate max-w-[120px]">
                        {report.target_id}
                      </td>
                      <td className="p-4 max-w-xs text-slate-700 font-medium line-clamp-2">
                        {report.reason}
                      </td>
                      <td className="p-4 text-slate-400 whitespace-nowrap">
                        {new Date(report.created_at).toLocaleString()}
                      </td>
                      <td className="p-4 whitespace-nowrap">
                        {report.status === ReportStatus.Pending && (
                          <span className="px-2.5 py-1 bg-amber-50 text-amber-700 font-bold rounded-lg">
                            待审核
                          </span>
                        )}
                        {report.status === ReportStatus.Resolved && (
                          <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 font-bold rounded-lg">
                            已处理
                          </span>
                        )}
                        {report.status === ReportStatus.Rejected && (
                          <span className="px-2.5 py-1 bg-slate-100 text-slate-500 font-bold rounded-lg">
                            已驳回
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-right whitespace-nowrap">
                        {report.status === ReportStatus.Pending ? (
                          <button
                            onClick={() => setSelectedReport(report)}
                            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs"
                          >
                            介入审核
                          </button>
                        ) : (
                          <span className="text-slate-400 text-[11px]">
                            {report.action ? `[${report.action}]` : '处理完毕'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Users Governance */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">注册学生用户治理 ({usersList.length})</h3>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-xs">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-bold">
                <tr>
                  <th className="p-4">用户</th>
                  <th className="p-4">账号</th>
                  <th className="p-4">院系与校区</th>
                  <th className="p-4">信用分</th>
                  <th className="p-4">当前状态</th>
                  <th className="p-4 text-right">账号管控</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {usersList.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4 flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full overflow-hidden bg-slate-100">
                        <img src={u.avatar} alt="avatar" className="w-full h-full object-cover" />
                      </div>
                      <span className="font-bold text-slate-900">{u.nickname}</span>
                    </td>
                    <td className="p-4 text-slate-500">@{u.username}</td>
                    <td className="p-4 text-slate-600">{u.major || '计算机系'} ({u.campus || '主校区'})</td>
                    <td className="p-4 font-bold text-emerald-600">信用良好 (5.0)</td>
                    <td className="p-4">
                      {u.status === 1 ? (
                        <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded font-bold">正常</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-rose-50 text-rose-700 rounded font-bold">已封禁</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleToggleUserBan(u.id, u.status)}
                        className={`px-3 py-1 rounded-xl font-bold text-xs transition-colors ${
                          u.status === 1
                            ? 'bg-rose-50 text-rose-600 hover:bg-rose-100'
                            : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
                        }`}
                      >
                        {u.status === 1 ? '封禁账号' : '解除封禁'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Item Audit Management */}
      {activeTab === 'items' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">物品审核管理 ({itemsTotal})</h3>
            <span className="text-xs text-slate-400">支持下架违规物品、删除不当内容与发布审核</span>
          </div>

          {/* Item review switch (admin-controlled) */}
          <div className="bg-white rounded-3xl border border-slate-200 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div>
              <p className="text-sm font-bold text-slate-800">发布审核开关</p>
              <p className="text-xs text-slate-400 mt-0.5">
                开启后新发布物品进入"待审核"，需在此处通过后方可上架；关闭后发布即上架（默认）
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setReviewEnabled(!reviewEnabled)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  reviewEnabled ? 'bg-indigo-600' : 'bg-slate-300'
                }`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                  reviewEnabled ? 'translate-x-6' : 'translate-x-0'
                }`} />
              </button>
              <button
                onClick={handleSaveReviewConfig}
                disabled={reviewConfigLoading}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-colors disabled:opacity-50"
              >
                {reviewConfigLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                {reviewConfigLoading ? '保存中...' : '保存设置'}
              </button>
            </div>
          </div>

          {/* Status filter */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-slate-500 mr-1">状态筛选：</span>
            {[{ label: '全部', value: undefined }, { label: '待审核', value: ItemStatus.Pending }, { label: '上架中', value: ItemStatus.OnSale }, { label: '已下架', value: ItemStatus.OffSale }, { label: '已售出', value: ItemStatus.Sold }, { label: '已保留', value: ItemStatus.Reserved }].map((opt) => (
              <button
                key={opt.label}
                onClick={() => {
                  setItemsStatusFilter(opt.value);
                  fetchItems(1);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                  itemsStatusFilter === opt.value
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-bold">
                  <tr>
                    <th className="p-4">物品标题</th>
                    <th className="p-4">分类</th>
                    <th className="p-4">价格</th>
                    <th className="p-4">状态</th>
                    <th className="p-4">发布时间</th>
                    <th className="p-4 text-right">审核操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {itemsLoading ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-400">
                        <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-2 text-slate-300" />
                        正在加载物品列表...
                      </td>
                    </tr>
                  ) : itemsList.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-400">
                        <Package className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                        暂无物品数据
                      </td>
                    </tr>
                  ) : (
                    itemsList.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="p-4 font-bold text-slate-800 max-w-[200px] truncate">
                          {item.title}
                        </td>
                        <td className="p-4 text-slate-600 whitespace-nowrap">
                          {item.category || '未分类'}
                        </td>
                        <td className="p-4 font-bold text-indigo-600 whitespace-nowrap">
                          ¥{formatPrice(item.price)}
                        </td>
                        <td className="p-4 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded font-bold ${
                            item.status === ItemStatus.OnSale
                              ? 'bg-emerald-50 text-emerald-700'
                              : item.status === ItemStatus.OffSale
                              ? 'bg-amber-50 text-amber-700'
                              : item.status === ItemStatus.Sold
                              ? 'bg-slate-100 text-slate-600'
                              : item.status === ItemStatus.Pending
                              ? 'bg-violet-50 text-violet-700'
                              : 'bg-blue-50 text-blue-700'
                          }`}>
                            {itemStatusMap[item.status] || '未知'}
                          </span>
                        </td>
                        <td className="p-4 text-slate-400 whitespace-nowrap">
                          {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                        </td>
                        <td className="p-4 text-right whitespace-nowrap">
                          <div className="flex gap-2 justify-end">
                            {item.status === ItemStatus.Pending ? (
                              <>
                                <button
                                  onClick={() => handleApproveItem(item.id)}
                                  disabled={itemActionLoading === item.id}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-40"
                                >
                                  <CheckCircle className="w-3 h-3" />
                                  通过
                                </button>
                                <button
                                  onClick={() => handleRejectItem(item.id)}
                                  disabled={itemActionLoading === item.id}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-40"
                                >
                                  <XCircle className="w-3 h-3" />
                                  拒绝
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => handleTakeDownItem(item.id)}
                                disabled={itemActionLoading === item.id || item.status === ItemStatus.OffSale || item.status === ItemStatus.Sold}
                                className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-40"
                              >
                                <ArrowDownCircle className="w-3 h-3" />
                                下架
                              </button>
                            )}
                            <button
                              onClick={() => handleDeleteItem(item.id)}
                              disabled={itemActionLoading === item.id}
                              className="inline-flex items-center gap-1 px-2.5 py-1 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-40"
                            >
                              <Trash2 className="w-3 h-3" />
                              删除
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {itemsTotalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t border-slate-100">
                <span className="text-xs text-slate-400">
                  第 {itemsPage} / {itemsTotalPages} 页 · 共 {itemsTotal} 条
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => fetchItems(Math.max(1, itemsPage - 1))}
                    disabled={itemsPage <= 1 || itemsLoading}
                    className="p-1.5 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg disabled:opacity-40 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4 text-slate-600" />
                  </button>
                  <button
                    onClick={() => fetchItems(Math.min(itemsTotalPages, itemsPage + 1))}
                    disabled={itemsPage >= itemsTotalPages || itemsLoading}
                    className="p-1.5 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg disabled:opacity-40 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4 text-slate-600" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 5: Email Register Config */}
      {activeTab === 'email' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">邮箱注册配置</h3>
            <span className="text-xs text-slate-400">控制校园邮箱注册开关与允许域名</span>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 space-y-6 shadow-xs">
            {/* Enabled toggle */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-slate-800">启用邮箱注册</p>
                <p className="text-xs text-slate-400 mt-0.5">关闭后，新用户将无法通过邮箱注册</p>
              </div>
              <button
                onClick={() => setEmailEnabled(!emailEnabled)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  emailEnabled ? 'bg-indigo-600' : 'bg-slate-300'
                }`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                  emailEnabled ? 'translate-x-6' : 'translate-x-0'
                }`} />
              </button>
            </div>

            {/* Domains */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                允许的邮箱域名 <span className="text-slate-400 normal-case">(逗号分隔)</span>
              </label>
              <input
                type="text"
                placeholder="例如: edu.cn, campus.edu, university.edu.cn"
                value={emailDomainsInput}
                onChange={(e) => setEmailDomainsInput(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-medium focus:bg-white focus:border-indigo-600 outline-none transition-all"
              />
              <p className="text-[11px] text-slate-400">
                只有匹配这些域名的邮箱地址才能注册
              </p>
            </div>

            {/* Pattern */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                邮箱正则匹配模式 <span className="text-slate-400 normal-case">(可选)</span>
              </label>
              <input
                type="text"
                placeholder="例如: .*@.*\.edu(\.cn)?"
                value={emailPatternInput}
                onChange={(e) => setEmailPatternInput(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-mono focus:bg-white focus:border-indigo-600 outline-none transition-all"
              />
              <p className="text-[11px] text-slate-400">
                当域名列表不足以覆盖时，可使用正则表达式做更灵活的匹配
              </p>
            </div>

            {/* Save button */}
            <div className="flex justify-end pt-2">
              <button
                onClick={handleSaveEmailConfig}
                disabled={emailConfigLoading}
                className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl text-sm font-bold shadow-lg shadow-indigo-200 disabled:opacity-50 transition-all active:scale-95"
              >
                {emailConfigLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {emailConfigLoading ? '保存中...' : '保存配置'}
              </button>
            </div>

            {/* Current config preview */}
            {emailConfig && (
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-1 text-xs">
                <p className="font-bold text-slate-500 uppercase mb-2">当前生效配置</p>
                <p><span className="text-slate-400">启用状态：</span><span className={`font-bold ${emailConfig.enabled ? 'text-emerald-600' : 'text-rose-600'}`}>{emailConfig.enabled ? '已启用' : '已关闭'}</span></p>
                <p><span className="text-slate-400">允许域名：</span><span className="font-mono text-slate-700">{(emailConfig.domains || []).join(', ') || '无'}</span></p>
                <p><span className="text-slate-400">匹配模式：</span><span className="font-mono text-slate-700">{emailConfig.pattern || '无'}</span></p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 6: AI 智能助手配置 */}
      {activeTab === 'ai' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">AI 智能助手配置</h3>
            <span className="text-xs text-slate-400">控制全站 AI 能力开关、模型与运行状态</span>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 space-y-6 shadow-xs">
            {/* 运行状态 banner */}
            {aiConfig?.status && (
              <div className={`flex items-start gap-3 p-4 rounded-2xl border text-xs font-medium ${
                aiConfig.status.available
                  ? 'bg-emerald-50 border-emerald-100 text-emerald-700'
                  : 'bg-amber-50 border-amber-100 text-amber-700'
              }`}>
                {aiConfig.status.available ? (
                  <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="font-bold">{aiConfig.status.available ? 'AI 服务可用' : 'AI 服务暂不可用'}</p>
                  <p className="opacity-80">{aiConfig.status.message || '未配置 GEMINI_API_KEY 或后端未启动'}</p>
                </div>
              </div>
            )}

            {/* Enabled toggle */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-slate-800">启用 AI 智能助手</p>
                <p className="text-xs text-slate-400 mt-0.5">关闭后，首页灵感、物品润色、课程画像等全部 AI 入口隐藏</p>
              </div>
              <button
                onClick={() => setAiEnabled(!aiEnabled)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  aiEnabled ? 'bg-indigo-600' : 'bg-slate-300'
                }`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${
                  aiEnabled ? 'translate-x-6' : 'translate-x-0'
                }`} />
              </button>
            </div>

            {/* Model selection (可自定义输入) */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Gemini 模型 <span className="text-slate-400 normal-case">(可自定义输入)</span>
              </label>
              <input
                list="ai-model-options"
                type="text"
                placeholder="gemini-2.0-flash"
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-mono focus:bg-white focus:border-indigo-600 outline-none transition-all"
              />
              <datalist id="ai-model-options">
                <option value="gemini-2.0-flash" />
                <option value="gemini-2.0-flash-lite" />
                <option value="gemini-2.5-flash" />
                <option value="gemini-2.5-pro" />
              </datalist>
              <p className="text-[11px] text-slate-400">
                需为当前 GEMINI_API_KEY 有权访问的模型；温度等生成参数由服务端按场景预设
              </p>
            </div>

            {/* Save button */}
            <div className="flex justify-end pt-2">
              <button
                onClick={handleSaveAiConfig}
                disabled={aiConfigLoading}
                className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl text-sm font-bold shadow-lg shadow-indigo-200 disabled:opacity-50 transition-all active:scale-95"
              >
                {aiConfigLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {aiConfigLoading ? '保存中...' : '保存配置'}
              </button>
            </div>

            {/* Current config preview */}
            {aiConfig && (
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-1 text-xs">
                <p className="font-bold text-slate-500 uppercase mb-2">当前生效配置</p>
                <p><span className="text-slate-400">启用状态：</span><span className={`font-bold ${aiConfig.enabled ? 'text-emerald-600' : 'text-rose-600'}`}>{aiConfig.enabled ? '已启用' : '已关闭'}</span></p>
                <p><span className="text-slate-400">使用模型：</span><span className="font-mono text-slate-700">{aiConfig.model || 'gemini-2.0-flash'}</span></p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 7: Audit Logs (Processing Records from Reports) */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-slate-900">处理记录与审计日志 ({auditReports.length})</h3>
            <span className="text-xs text-slate-400">展示所有举报工单的处理状态与记录</span>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 divide-y divide-slate-100 shadow-xs">
            {auditReports.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <FileText className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p className="text-sm">暂无处理记录</p>
              </div>
            ) : (
              auditReports.map((report) => (
                <div key={report.id} className="p-4 flex items-center justify-between text-xs">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                        {report.target_type}
                      </span>
                      <span className="text-slate-800 font-semibold">
                        {report.status === ReportStatus.Resolved
                          ? '已解决'
                          : report.status === ReportStatus.Rejected
                          ? '已驳回'
                          : report.status === ReportStatus.Processing
                          ? '处理中'
                          : '待处理'}
                      </span>
                      {report.action && report.action !== ReportAction.None && (
                        <span className="text-slate-400 text-[11px]">[{report.action}]</span>
                      )}
                    </div>
                    <div className="text-slate-400">
                      举报原因：{report.reason} · 目标ID：{report.target_id}
                      {report.feedback && ` · 处理意见：${report.feedback}`}
                    </div>
                  </div>
                  <span className="text-slate-400 whitespace-nowrap">
                    {report.created_at ? new Date(report.created_at).toLocaleString() : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Report Handling Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 space-y-6 shadow-2xl border border-slate-100">
            <h3 className="text-xl font-bold text-slate-900">审核处置违规举报工单</h3>

            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 space-y-2 text-xs">
              <p><strong>举报类型：</strong>{selectedReport.target_type}</p>
              <p><strong>目标ID：</strong>{selectedReport.target_id}</p>
              <p><strong>举报原因：</strong>{selectedReport.reason}</p>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-700">选择处罚措施</label>
              <select
                value={reportAction}
                onChange={(e) => setReportAction(e.target.value as ReportAction)}
                className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium outline-none"
              >
                <option value={ReportAction.None}>无实质处罚 (仅口头警告)</option>
                <option value={ReportAction.ItemOffSale}>下架违规二手物品</option>
                <option value={ReportAction.UserBan}>直接封禁违规发布者账号</option>
                <option value={ReportAction.CommentDelete}>删除违规评论/留言</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-700">处理意见与留存反馈</label>
              <textarea
                rows={3}
                placeholder="填写处理意见，将同步抄送举报人与被举报人..."
                value={reportFeedback}
                onChange={(e) => setReportFeedback(e.target.value)}
                className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setSelectedReport(null)}
                className="flex-1 py-3 border border-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => handleResolveReport(ReportStatus.Rejected)}
                disabled={actionLoading}
                className="flex-1 py-3 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl text-xs font-bold disabled:opacity-50"
              >
                驳回虚假举报
              </button>
              <button
                type="button"
                onClick={() => handleResolveReport(ReportStatus.Resolved)}
                disabled={actionLoading}
                className="flex-1 py-3 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-md shadow-rose-100 disabled:opacity-50"
              >
                {actionLoading ? '处理中...' : '确认执行处罚'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
