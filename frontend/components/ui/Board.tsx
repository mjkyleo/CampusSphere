import React from 'react';

export type BoardCols = string;

/** 信息板容器：表面底 + hairline 边 + 小圆角 */
export function Board({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-surface border-0 rounded-lg shadow-slate overflow-hidden ${className}`}>
      {children}
    </div>
  );
}

/** 信息板列头：mono 大写列名（风格 B） */
export function BoardColumns({
  cols,
  labels,
}: {
  cols: BoardCols;
  labels: string[];
}) {
  return (
    <div
      className="grid items-center gap-2.5 px-3 py-2 border-b border-hairline"
      style={{ gridTemplateColumns: cols }}
    >
      {labels.map((l) => (
        <span key={l} className="mono-label text-steel truncate">
          {l}
        </span>
      ))}
    </div>
  );
}

interface BoardRowProps {
  cols: BoardCols;
  children: React.ReactNode;
  /** 变更态：警示色点亮并保持（签名交互） */
  changed?: boolean;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
  className?: string;
}

/** 信息板行：行即控件；变更行亮 alert */
export function BoardRow({
  cols,
  children,
  changed,
  onClick,
  className = '',
}: BoardRowProps) {
  const cls = [
    'grid items-center gap-2.5 px-3 py-2.5 border-b border-hairline transition-colors duration-rerank ease-impeccable',
    onClick ? 'cursor-pointer hover:bg-panel' : '',
    changed ? 'bg-alert text-ink' : 'bg-surface text-ink',
    className,
  ].join(' ');
  return (
    <div
      className={cls}
      style={{ gridTemplateColumns: cols }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick(e as unknown as React.MouseEvent<HTMLDivElement>);
              }
            }
          : undefined
      }
    >
      {children}
    </div>
  );
}

/** 行内 mono 数据单元（价格/时间/编号） */
export function DataCell({ children, strong }: { children: React.ReactNode; strong?: boolean }) {
  return (
    <span className={`mono-data text-slate truncate ${strong ? '!font-semibold !text-ink' : ''}`}>
      {children}
    </span>
  );
}

/** 行内文本单元 */
export function TextCell({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <span className={`text-body-2 text-slate truncate ${className}`}>{children}</span>;
}

/** 行内动作胶囊 */
export function ActionCell({ children }: { children: React.ReactNode }) {
  return (
    <span className="mono-label text-slate bg-panel px-2 py-1 rounded text-center truncate">
      {children}
    </span>
  );
}
