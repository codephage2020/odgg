// Global error boundary — catches render errors and shows fallback UI
import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <h2>页面出错了</h2>
            <p>{this.state.error?.message || '发生未知错误'}</p>
            <button
              className="btn btn-primary"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/brief';
              }}
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
