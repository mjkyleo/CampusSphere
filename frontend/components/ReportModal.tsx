import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { api } from '../services/api.ts';
import { AlertTriangle, X, ShieldAlert } from 'lucide-react';
import { Button } from './ui';

export const ReportModal: React.FC = () => {
  const { reportModal, closeReport } = useAuth();
  const { success, error } = useToast();
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Esc 关闭 + 打开时聚焦弹窗面板（可访问性）
  // hooks 必须全部声明在早退之前：开合切换时 hook 数量不变，否则整棵组件树崩溃
  useEffect(() => {
    if (!reportModal.isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeReport();
    };
    window.addEventListener('keydown', onKey);
    panelRef.current?.focus();
    return () => window.removeEventListener('keydown', onKey);
  }, [reportModal.isOpen, closeReport]);

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
    <div
      className="fixed inset-0 z-[9990] flex items-center justify-center p-4 bg-slate-900/60 animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-label="提交违规举报"
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="bg-surface border border-hairline rounded-md max-w-lg w-full p-6 shadow-elevate relative space-y-6 animate-in zoom-in-95 duration-200 outline-none"
      >
        <button
          onClick={closeReport}
          aria-label="关闭举报弹窗"
          className="absolute top-4 right-4 p-2 rounded-md hover:bg-panel text-steel transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="p-3 bg-error/10 text-error rounded-md">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-heading-2 font-bold text-ink">提交违规举报</h3>
            <p className="text-caption text-steel">
              举报对象：
              <span className="font-semibold text-error ml-1">
                [{typeLabels[reportModal.targetType] || '内容'}]
              </span>{' '}
              {reportModal.targetTitle && `“${reportModal.targetTitle}”`}
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block mono-label text-slate tracking-mono">
              常见违规类型（点击快速填入）
            </label>
            <div className="flex flex-wrap gap-1.5">
              {commonReasons.map((r) => (
                <button
                  type="button"
                  key={r}
                  onClick={() => setReason(r)}
                  aria-pressed={reason === r}
                  className={`text-xs px-3 py-1.5 rounded-md border transition-all ${
                    reason === r
                      ? 'bg-error/10 border-error text-error font-medium'
                      : 'bg-transparent border-hairline text-slate hover:border-ink'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block mono-label text-slate tracking-mono">
              详细举报说明 / 证据补充 <span className="text-error">*</span>
            </label>
            <textarea
              rows={4}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="请详细描述违规事实或欺诈细节，支持补充联系方式、聊天截图时间线等..."
              className="w-full p-3.5 bg-surface rounded-md border border-hairline focus:border-error focus:ring-2 focus:ring-error/20 outline-none text-body-2 text-ink leading-relaxed transition-all resize-none"
            />
            <p className="text-caption text-steel text-right">已输入 {reason.length} 字 (上限 500 字)</p>          </div>

          <div className="p-3 bg-alert/20 rounded-md flex items-start gap-2.5 text-xs text-ink">
            <AlertTriangle className="w-4 h-4 text-ink shrink-0 mt-0.5" />
            <p>
              请如实填写举报内容。恶意虚假举报或滥用举报功能将扣除个人校园信用积分，甚至限制账户操作。
            </p>
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="ghost" onClick={closeReport} className="flex-1 py-3">
              取消
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={loading}
              className="flex-[2] py-3"
            >
              {loading ? '正在提交...' : '确认并提交举报'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
