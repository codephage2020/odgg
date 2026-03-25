// AI suggestion bubble with accept/modify/reject actions
interface Props {
  suggestion: Record<string, unknown> | null;
  confidence: number | null;
  loading: boolean;
  error: string | null;
  onAccept: () => void;
  onModify: () => void;
  onReject: () => void;
  onRetry: () => void;
}

export function AISuggestionBubble({
  suggestion,
  confidence,
  loading,
  error,
  onAccept,
  onModify,
  onReject,
  onRetry,
}: Props) {
  // Loading state
  if (loading) {
    return (
      <div className="ai-bubble ai-bubble-loading">
        <div className="ai-badge">AI</div>
        <div className="ai-skeleton">
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="ai-bubble ai-bubble-error">
        <div className="ai-badge">AI</div>
        <div className="ai-content">
          <p className="error-text">{error}</p>
          <div className="ai-actions">
            <button className="btn btn-retry" onClick={onRetry}>
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!suggestion) {
    return (
      <div className="ai-bubble ai-bubble-empty">
        <div className="ai-badge">AI</div>
        <p className="empty-text">等待 AI 分析...</p>
      </div>
    );
  }

  // Suggestion state
  return (
    <div className="ai-bubble ai-bubble-suggested">
      <div className="ai-header">
        <div className="ai-badge">AI</div>
        {confidence != null && (
          <span className="confidence-badge">
            置信度 {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
      <div className="ai-content">
        <pre className="suggestion-text">
          {JSON.stringify(suggestion, null, 2)}
        </pre>
      </div>
      <div className="ai-actions">
        <button className="btn btn-accept" onClick={onAccept}>
          接受
        </button>
        <button className="btn btn-modify" onClick={onModify}>
          修改
        </button>
        <button className="btn btn-reject" onClick={onReject}>
          拒绝
        </button>
      </div>
    </div>
  );
}
