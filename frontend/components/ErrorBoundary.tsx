import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Card, CardContent, Button, Alert } from './ui';

interface ErrorBoundaryProps {
  children?: React.ReactNode;
}
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

/**
 * 路由级错误边界：页面渲染异常时给出可恢复的降级界面（原为静默白屏/重定向）。
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: unknown, info: unknown) {
    console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex items-center justify-center">
          <Card className="max-w-md w-full text-center">
            <CardContent className="space-y-4">
              <div className="p-3 bg-error/10 text-error rounded-md inline-flex">
                <AlertTriangle className="h-7 w-7" />
              </div>
              <div className="space-y-1">
                <div className="mono-label text-steel">PAGE ERROR</div>
                <h1 className="text-heading-2 text-ink">页面加载出现异常</h1>
                <p className="text-body-2 text-steel">服务暂未就绪，请稍后重试或返回首页。</p>
              </div>
              <Alert variant="destructive" title="错误详情">
                {String(this.state.error?.message || '未知错误')}
              </Alert>
              <Button onClick={() => { this.setState({ hasError: false }); window.location.href = '/'; }}>
                返回首页
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}
