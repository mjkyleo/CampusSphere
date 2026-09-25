import React from 'react';
import { Link } from 'react-router-dom';

type Variant = 'primary' | 'ghost' | 'text';

const base =
  'mono-label inline-flex items-center justify-center gap-2 rounded-md transition-all duration-feedback ease-impeccable select-none disabled:opacity-40 disabled:pointer-events-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink';

const variants: Record<Variant, string> = {
  primary: 'bg-ink text-surface hover:bg-slate active:scale-[0.98]',
  ghost: 'bg-transparent text-slate border border-hairline hover:border-ink',
  text: 'bg-transparent text-ink hover:underline',
};

interface ButtonProps {
  children: React.ReactNode;
  variant?: Variant;
  to?: string;
  onClick?: () => void;
  type?: 'button' | 'submit';
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
}

/** 主 / 次 / 文字按钮；文字一律 mono 大写（登机牌·航站屏世界） */
export function Button({
  children,
  variant = 'primary',
  to,
  onClick,
  type = 'button',
  disabled,
  className = '',
  ariaLabel,
}: ButtonProps) {
  const cls = `${base} ${variants[variant]} ${className}`;
  if (to) {
    return (
      <Link to={to} className={cls} onClick={onClick} aria-label={ariaLabel}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} className={cls} onClick={onClick} disabled={disabled} aria-label={ariaLabel}>
      {children}
    </button>
  );
}
