import React from 'react';
import { ImageIcon, User } from 'lucide-react';

/**
 * 中性图片/头像占位：替代 unsplash 兜底与假实拍图。
 * - variant="media"：方形图片占位（面板底 + hairline 描边 + ImageIcon）
 * - variant="avatar"：圆形头像占位（User 图标）
 * 仅当无真实图时渲染；永不伪装成真实内容。
 */
export function ImagePlaceholder({
  variant = 'media',
  label,
  className = '',
  iconClassName = '',
}: {
  variant?: 'media' | 'avatar';
  label?: string;
  className?: string;
  iconClassName?: string;
}) {
  if (variant === 'avatar') {
    return (
      <div
        aria-hidden
        className={`inline-flex items-center justify-center rounded-full bg-panel border border-hairline text-steel ${className}`}
      >
        <User className={`w-1/2 h-1/2 ${iconClassName}`} strokeWidth={1.6} />
      </div>
    );
  }
  return (
    <div
      aria-hidden
      className={`flex flex-col items-center justify-center gap-1.5 bg-panel border border-hairline text-steel ${className}`}
    >
      <ImageIcon className={`w-1/3 h-1/3 ${iconClassName}`} strokeWidth={1.4} />
      {label ? <span className="mono-label text-steel">{label}</span> : null}
    </div>
  );
}
