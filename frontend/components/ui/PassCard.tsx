import React from 'react';

export interface PassSegment {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}

/** 分段信息凭证卡：头部色条 + 分段字段 + mono 编号块 */
export function PassCard({
  title,
  seq,
  segments,
  scanCode,
  scanNote,
  footer,
  onClick,
}: {
  title: string;
  seq?: string;
  segments: PassSegment[];
  scanCode?: string;
  scanNote?: string;
  footer?: React.ReactNode;
  onClick?: () => void;
}) {
  const even = segments.length % 2 === 0;
  return (
    <div
      className={`bg-surface rounded-lg overflow-hidden shadow-surface transition-all duration-300 ease-impeccable ${
        onClick ? 'cursor-pointer hover:shadow-elevate hover:-translate-y-0.5' : ''
      }`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
    >
      <div className="bg-gradient-to-r from-primary to-primary-hover text-surface px-4 py-3 flex items-center justify-between">
        <span className="mono-label text-white/95">{title}</span>
        {seq ? <span className="mono-label text-white/75">{seq}</span> : null}
      </div>

      <div className={`grid ${even ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {segments.map((s, i) => (
          <div
            key={s.label}
            className={`px-4 py-3 ${i < segments.length - (even ? 2 : 1) ? 'border-b border-hairline' : ''} ${
              i % 2 === 1 ? 'border-l border-hairline' : ''
            }`}
          >
            <div className="mono-label text-steel mb-1">{s.label}</div>
            <div className={s.mono === false ? 'text-heading-3 text-ink' : 'mono-data !font-semibold !text-ink'}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {(scanCode || footer) && (
        <div className="flex items-center gap-3 px-4 py-3 border-t border-hairline">
          {scanCode && (
            <>
              <div
                className="h-6 w-20 shrink-0 opacity-90"
                style={{
                  background:
                    'repeating-linear-gradient(90deg, var(--primary) 0 3px, transparent 3px 5px)',
                }}
              />
              <span className="mono-data !font-semibold !text-ink">{scanCode}</span>
            </>
          )}
          {scanNote && <span className="caption text-steel ml-auto">{scanNote}</span>}
          {footer}
        </div>
      )}
    </div>
  );
}
