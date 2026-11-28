/**
 * shadcn/ui 风格基础组件（Material 主题适配版）。
 * 自实现而非引入 Radix：避免 React 19 兼容风险与包体积膨胀，
 * 但保留 shadcn 的 API 形态（variant/size/asChild）+ ARIA 语义。
 */
import React from 'react';
import { Loader2, X } from 'lucide-react';
import { cn } from '../../lib/utils';

/* -------------------------------------------------------------------------- */
/* Button                                                                      */
/* -------------------------------------------------------------------------- */
type ButtonVariant = 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' | 'primary' | 'text';
type ButtonSize = 'default' | 'sm' | 'lg' | 'icon';

const buttonVariants: Record<ButtonVariant, string> = {
  default: 'bg-primary text-white hover:bg-primary-hover shadow-md-2 hover:shadow-md-4',
  destructive: 'bg-error text-white hover:bg-error/90 shadow-md-2',
  outline: 'border border-primary/40 bg-surface text-primary hover:bg-primary-soft',
  secondary: 'bg-panel text-ink hover:bg-hairline',
  ghost: 'bg-transparent text-slate hover:bg-panel hover:text-ink',
  link: 'bg-transparent text-primary underline-offset-4 hover:underline',
  primary: 'bg-primary text-white hover:bg-primary-hover shadow-md-2 hover:shadow-md-4',
  text: 'bg-transparent text-primary hover:bg-primary-soft',
};
const buttonSizes: Record<ButtonSize, string> = {
  default: 'h-10 px-5 py-2',
  sm: 'h-8 px-3 text-caption',
  lg: 'h-12 px-8 text-body-1',
  icon: 'h-10 w-10',
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'md-button-text inline-flex items-center justify-center gap-2 rounded-md',
        'transition-all duration-[250ms] ease-impeccable select-none',
        'hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]',
        'disabled:opacity-40 disabled:pointer-events-none disabled:hover:translate-y-0',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
        buttonVariants[variant], buttonSizes[size], className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  ),
);
Button.displayName = 'Button';

/* -------------------------------------------------------------------------- */
/* Badge                                                                       */
/* -------------------------------------------------------------------------- */
type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'muted' | 'outline';
const badgeVariants: Record<BadgeVariant, string> = {
  default: 'bg-primary text-white',
  success: 'bg-success text-white',
  warning: 'bg-alert text-white',
  danger: 'bg-error text-white',
  muted: 'bg-panel text-slate',
  outline: 'border border-hairline text-slate',
};
export function Badge({
  variant = 'default', dot, className, children,
}: { variant?: BadgeVariant; dot?: boolean; className?: string; children?: React.ReactNode }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium', badgeVariants[variant], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/* Input / Textarea / Label / Field                                            */
/* -------------------------------------------------------------------------- */
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full px-4 py-3 bg-ground border-0 border-b-2 border-hairline rounded-t-md text-ink',
        'placeholder:text-steel transition-colors duration-[250ms]',
        'focus:bg-surface focus:outline-none focus:border-primary',
        'disabled:opacity-50', className,
      )}
      {...props}
    />
  ),
);
Input.displayName = 'Input';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'w-full px-4 py-3 bg-ground border border-hairline rounded-md text-ink',
        'placeholder:text-steel focus:bg-surface focus:outline-none focus:border-primary',
        'disabled:opacity-50 resize-y', className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = 'Textarea';

export function Label({ className, children, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label className={cn('block mono-label text-steel mb-1.5', className)} {...props}>
      {children}
    </label>
  );
}

export function Field({
  label, required, description, error, children, className,
}: {
  label?: string; required?: boolean; description?: string; error?: string;
  children: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && <Label>{label}{required && <span className="text-error ml-0.5">*</span>}</Label>}
      {children}
      {error && <p className="text-caption text-error" role="alert">{error}</p>}
      {description && !error && <p className="text-caption text-steel">{description}</p>}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Card                                                                        */
/* -------------------------------------------------------------------------- */
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('bg-surface rounded-lg shadow-surface', className)} {...props} />;
}
export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-5 py-4 border-b border-hairline', className)} {...props} />;
}
export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('font-display text-heading-3 text-ink', className)} {...props} />;
}
export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5', className)} {...props} />;
}
export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('px-5 py-4 border-t border-hairline', className)} {...props} />;
}

/* -------------------------------------------------------------------------- */
/* Separator / Skeleton / Spinner                                              */
/* -------------------------------------------------------------------------- */
export function Separator({ className, orientation = 'horizontal' }: { className?: string; orientation?: 'horizontal' | 'vertical' }) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={cn(orientation === 'horizontal' ? 'h-px w-full bg-hairline' : 'w-px h-full bg-hairline', className)}
    />
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('bg-panel rounded-md animate-pulse', className)} aria-hidden />;
}

export function Spinner({ size = 'md', label = '加载中' }: { size?: 'sm' | 'md' | 'lg'; label?: string }) {
  const sizes = { sm: 'h-4 w-4 border-2', md: 'h-8 w-8 border-[3px]', lg: 'h-12 w-12 border-4' };
  return (
    <div role="status" aria-label={label} className={cn('inline-flex items-center gap-2 text-steel')}>
      <div className={cn('animate-spin rounded-full border-primary border-t-transparent', sizes[size])} />
      <span className="sr-only">{label}</span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Alert                                                                       */
/* -------------------------------------------------------------------------- */
type AlertVariant = 'info' | 'success' | 'warning' | 'destructive';
const alertVariants: Record<AlertVariant, string> = {
  info: 'bg-primary-soft text-primary-dark',
  success: 'bg-success/10 text-success',
  warning: 'bg-alert/15 text-alert',
  destructive: 'bg-error/10 text-error',
};
export function Alert({
  variant = 'info', title, children, className,
}: { variant?: AlertVariant; title?: string; children?: React.ReactNode; className?: string }) {
  return (
    <div role="alert" className={cn('rounded-md px-4 py-3 text-body-2', alertVariants[variant], className)}>
      {title && <p className="font-medium">{title}</p>}
      {children && <div className="mt-1 opacity-90">{children}</div>}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Empty                                                                       */
/* -------------------------------------------------------------------------- */
export function Empty({
  icon, title, description, action, className,
}: { icon?: React.ReactNode; title: string; description?: string; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-12 px-4 space-y-3', className)}>
      {icon && <div className="text-steel [&>svg]:h-10 [&>svg]:w-10">{icon}</div>}
      <p className="text-body-1 font-medium text-ink">{title}</p>
      {description && <p className="text-body-2 text-steel max-w-sm">{description}</p>}
      {action}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Switch / ToggleGroup                                                        */
/* -------------------------------------------------------------------------- */
export function Switch({
  checked, onCheckedChange, label, disabled,
}: { checked: boolean; onCheckedChange: (v: boolean) => void; label?: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-[250ms]',
        checked ? 'bg-primary' : 'bg-hairline',
        disabled && 'opacity-50 pointer-events-none',
      )}
    >
      <span className={cn(
        'inline-block h-5 w-5 rounded-full bg-white shadow-md-2 transition-transform duration-[250ms]',
        checked ? 'translate-x-5' : 'translate-x-0.5',
      )} />
    </button>
  );
}

export function ToggleGroup({
  options, value, onChange, label,
}: {
  options: Array<{ value: string; label: React.ReactNode }>;
  value: string | string[];
  onChange: (v: string) => void;
  label?: string;
}) {
  const values = Array.isArray(value) ? value : [value];
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          aria-pressed={values.includes(opt.value)}
          onClick={() => onChange(opt.value)}
          className={cn(
            'px-3 py-1 rounded-full text-caption font-medium transition-all duration-[250ms]',
            values.includes(opt.value)
              ? 'bg-primary text-white shadow-md-2'
              : 'bg-surface text-slate shadow-slate hover:shadow-md-2 hover:-translate-y-0.5',
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Tabs                                                                        */
/* -------------------------------------------------------------------------- */
export function Tabs({
  tabs, value, onChange,
}: { tabs: Array<{ value: string; label: React.ReactNode }>; value: string; onChange: (v: string) => void }) {
  const onKeyDown = (e: React.KeyboardEvent, idx: number) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const next = e.key === 'ArrowRight' ? (idx + 1) % tabs.length : (idx - 1 + tabs.length) % tabs.length;
    onChange(tabs[next].value);
  };
  return (
    <div role="tablist" className="flex gap-1 p-1 bg-panel rounded-md">
      {tabs.map((tab, idx) => (
        <button
          key={tab.value}
          role="tab"
          type="button"
          aria-selected={value === tab.value}
          tabIndex={value === tab.value ? 0 : -1}
          onClick={() => onChange(tab.value)}
          onKeyDown={(e) => onKeyDown(e, idx)}
          className={cn(
            'flex-1 px-3 py-2 rounded-md text-body-2 transition-all duration-[250ms]',
            value === tab.value ? 'bg-primary text-white shadow-md-2' : 'text-steel hover:text-ink',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Dialog                                                                      */
/* -------------------------------------------------------------------------- */
export function Dialog({
  open, onClose, title, description, children, footer, className,
}: {
  open: boolean; onClose: () => void; title: string; description?: string;
  children?: React.ReactNode; footer?: React.ReactNode; className?: string;
}) {
  const panelRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    const prev = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
      prev?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[9990] flex items-center justify-center p-4 bg-ink/50 animate-in fade-in duration-200" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cn('w-full max-w-md bg-surface rounded-lg shadow-elevate outline-none p-5 space-y-4 animate-in zoom-in-95 duration-200', className)}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-heading-2 text-ink">{title}</h2>
            {description && <p className="text-body-2 text-steel mt-1">{description}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="关闭" className="p-1 rounded-md text-steel hover:bg-panel hover:text-ink">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
        {footer && <div className="flex justify-end gap-2 pt-2">{footer}</div>}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Table / Avatar / Progress                                                   */
/* -------------------------------------------------------------------------- */
export function Table({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn('w-full overflow-x-auto rounded-md border border-hairline', className)}>
      <table className="w-full text-left text-body-2">{children}</table>
    </div>
  );
}
export function TableHeader({ children }: { children: React.ReactNode }) {
  return <thead className="bg-panel/60 border-b border-hairline text-steel mono-label">{children}</thead>;
}
export function TableRow({ children, className }: { children: React.ReactNode; className?: string }) {
  return <tr className={cn('border-b border-hairline last:border-0 hover:bg-panel/40', className)}>{children}</tr>;
}
export function TableCell({ children, className, head }: { children?: React.ReactNode; className?: string; head?: boolean }) {
  const Tag = head ? 'th' : 'td';
  return <Tag className={cn('px-3 py-2.5', className)}>{children}</Tag>;
}

export function Avatar({ src, name, className }: { src?: string; name?: string; className?: string }) {
  const [failed, setFailed] = React.useState(false);
  const initial = (name || '?').trim().charAt(0).toUpperCase();
  return (
    <span className={cn('inline-flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary-soft text-primary font-medium', className)}>
      {src && !failed ? (
        <img src={src} alt={name || ''} className="h-full w-full object-cover" onError={() => setFailed(true)} />
      ) : initial}
    </span>
  );
}

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} className={cn('h-2 w-full rounded-full bg-panel overflow-hidden', className)}>
      <div className="h-full bg-primary transition-all duration-[250ms]" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}
