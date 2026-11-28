import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** shadcn 风格 className 合并：条件类 + 冲突类覆盖（后者胜）。 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
