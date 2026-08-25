import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { api } from '../services/api.ts';
import { AlertTriangle, X, ShieldAlert } from 'lucide-react';

export const ReportModal: React.FC = () => {
  const { reportModal, closeReport } = useAuth();
  const { success, error } = useToast();
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  if (!reportModal.isOpen) return null;

  const typeLabels: Record<string, string> = {
    user: '违规用户',
    item: '二手物品',
    message: '违规私信消息',
    comment: '评论内容',
    share: '共享资源文件'
  };

  const commonReasons = [
    '涉嫌虚假诈骗 / 诱导线下交易',
    '发布违禁品 / 涉及违规违法内容',
    '垃圾广告 / 灌水引流信息',
    '恶意谩骂 / 人身攻击与诽谤',
    '侵犯知识产权 / 虚假盗图盗文'
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      error('请填写具体的举报原因或违规证据');
      return;
    }

    setLoading(true);
    try {
      const res = await api.reports.submit(reportModal.targetType, reportModal.targetId, reason.trim());
      if (res.code === 0) {
        success('举报工单已提交！管理员将会在24小时内审核处理');
        setReason('');
        closeReport();
      } else {
        error(res.message || '提交举报失败');
      }
    } catch {
      error('网络异常，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9990] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-100 relative space-y-6 animate-in zoom-in-95 duration-200">
        <button
          onClick={closeReport}
          className="absolute top-6 right-6 p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="p-3 bg-rose-50 text-rose-600 rounded-2xl">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-slate-900">提交违规举报</h3>
            <p className="text-xs text-slate-500">
              举报对象：
              <span className="font-semibold text-rose-600 ml-1">
                [{typeLabels[reportModal.targetType] || '内容'}]
              </span>{' '}
              {reportModal.targetTitle && `“${reportModal.targetTitle}”`}
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider">
              常见违规类型（点击快速填入）
            </label>
            <div className="flex flex-wrap gap-1.5">
              {commonReasons.map((r) => (
                <button
                  type="button"
                  key={r}
                  onClick={() => setReason(r)}
                  className={`text-xs px-3 py-1.5 rounded-xl border transition-all ${
                    reason === r
                      ? 'bg-rose-50 border-rose-300 text-rose-700 font-medium'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              详细举报说明 / 证据补充 <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="请详细描述违规事实或欺诈细节，支持补充联系方式、聊天截图时间线等..."
              className="w-full p-3.5 bg-slate-50 rounded-2xl border border-slate-200 focus:border-rose-500 focus:ring-2 focus:ring-rose-200 outline-none text-sm leading-relaxed transition-all resize-none"
            />
            <p className="text-[11px] text-slate-400 text-right">已输入 {reason.length} 字 (上限 500 字)</p>
          </div>

          <div className="p-3 bg-amber-50 rounded-2xl flex items-start gap-2.5 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p>
              请如实填写举报内容。恶意虚假举报或滥用举报功能将扣除个人校园信用积分，甚至限制账户操作。
            </p>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={closeReport}
              className="flex-1 py-3 px-4 rounded-xl border border-slate-200 text-slate-600 text-sm font-semibold hover:bg-slate-50 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-[2] py-3 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-sm font-bold shadow-lg shadow-rose-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? '正在提交...' : '确认并提交举报'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
