import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import { api } from '../services/api.ts';
import { ShieldAlert } from 'lucide-react';
import { Button, Dialog, Textarea, Label, Alert } from './ui';

export const ReportModal: React.FC = () => {
  const { reportModal, closeReport } = useAuth();
  const { success, error } = useToast();
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);


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
    <Dialog
      open={reportModal.isOpen}
      onClose={closeReport}
      title="提交违规举报"
      description={`举报对象：[${typeLabels[reportModal.targetType] || '内容'}] ${reportModal.targetTitle || ''}`}
      className="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label>常见违规类型（点击快速填入）</Label>
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
          <Label>详细举报说明 / 证据补充 <span className="text-error">*</span></Label>
          <Textarea
            rows={4}
            required
            maxLength={500}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="请详细描述违规事实或欺诈细节..."
          />
          <p className="text-caption text-steel text-right">已输入 {reason.length} 字 (上限 500 字)</p>
        </div>

        <Alert variant="warning">
          请如实填写举报内容。恶意虚假举报或滥用举报功能将扣除个人校园信用积分。
        </Alert>

        <div className="flex gap-3 pt-2">
          <Button variant="ghost" onClick={closeReport} className="flex-1">取消</Button>
          <Button variant="destructive" type="submit" loading={loading} className="flex-[2]">
            确认并提交举报
          </Button>
        </div>
      </form>
    </Dialog>
  );
};
