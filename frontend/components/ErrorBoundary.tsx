import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorBoundaryProps {
  children?: React.ReactNode;
}
interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * 路由级错误边界：页面渲染异常时给出可恢复的降级界面（原为静默白屏/重定向）。
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, info: unknown) {
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex items-center justify-center">
          <div className="bg-surface border border-hairline rounded-lg p-8 max-w-md w-full text-center shadow-surface space-y-4">
            <div className="p-3 bg-error/10 text-error rounded-md inline-flex">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <div className="mono-label text-steel tracking-mono">FLIGHT INTERRUPTED</div>
              <h1 className="text-heading-2 text-ink">页面加载出现异常</h1>
              <p className="text-body-2 text-steel">服务暂未就绪，请稍后重试或返回首页。</p>
            </div>
            <button
              onClick={() => {
                this.setState({ hasError: false });
                window.location.href = '/';
              }}
              className="px-6 py-3 bg-ink hover:bg-slate text-surface rounded-md mono-label uppercase tracking-mono transition-colors"
            >
              返回首页
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
