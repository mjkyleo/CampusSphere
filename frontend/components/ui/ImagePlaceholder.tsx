import React from 'react';
import { ImageIcon, User } from 'lucide-react';
import { cn } from '../../lib/utils';

/**
 * 中性图片/头像占位（shadcn Avatar 语义 + Material 主题）。
 * - variant="media"：方形图片占位（面板底 + hairline 描边 + ImageIcon）
 * - variant="avatar"：圆形头像；传 src/name 时按 Avatar 渲染（含加载失败回退），
 *   否则渲染 User 图标占位。
 * 仅当无真实图时渲染；永不伪装成真实内容。
 */
export function ImagePlaceholder({
  variant = 'media',
  label,
  className = '',
  iconClassName = '',
  src,
  name,
}: {
  variant?: 'media' | 'avatar';
  label?: string;
  className?: string;
  iconClassName?: string;
  src?: string;
  name?: string;
}) {
  const [failed, setFailed] = React.useState(false);

  if (variant === 'avatar') {
    const initial = (name || '').trim().charAt(0).toUpperCase();
    return (
      <span
        className={cn(
          'inline-flex items-center justify-center overflow-hidden rounded-full',
          'bg-primary-soft text-primary font-medium',
          className,
        )}
        aria-label={name ? `${name}的头像` : '用户头像'}
      >
        {src && !failed ? (
          <img
            src={src}
            alt={name || '用户头像'}
            className="h-full w-full object-cover"
            onError={() => setFailed(true)}
          />
        ) : initial ? (
          <span>{initial}</span>
        ) : (
          <User className={cn('h-1/2 w-1/2', iconClassName)} strokeWidth={1.6} aria-hidden />
        )}
      </span>
    );
  }

  return (
    <div
      aria-hidden
      className={cn(
        'flex flex-col items-center justify-center gap-1.5',
        'bg-panel border border-hairline text-steel',
        className,
      )}
    >
      <ImageIcon className={cn('h-1/3 w-1/3', iconClassName)} strokeWidth={1.4} />
      {label ? <span className="mono-label text-steel">{label}</span> : null}
    </div>
  );
}
