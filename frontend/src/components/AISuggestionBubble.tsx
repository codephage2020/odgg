// AI suggestion bubble with human-readable rendering per step type
import { useState, useEffect, useRef } from 'react';

interface Props {
  stepNumber: number;
  suggestion: Record<string, unknown> | null;
  confidence: number | null;
  loading: boolean;
  error: string | null;
  onAccept: () => void;
  onModify: () => void;
  onReject: () => void;
  onRetry: () => void;
}

function ElapsedTimer() {
  const [elapsed, setElapsed] = useState(0);
  const start = useRef(Date.now());
  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="elapsed-timer">{elapsed}s</span>;
}

// Step 3: Business processes
function RenderProcesses({ data }: { data: Record<string, unknown> }) {
  const processes = (data.processes || []) as Array<{
    name: string; description?: string; confidence?: number; involved_tables?: string[];
  }>;
  if (!processes.length) return <p className="empty-text">未发现业务过程</p>;
  return (
    <div className="suggestion-cards">
      {processes.map((p, i) => (
        <div key={i} className="suggestion-card">
          <div className="card-header">
            <span className="card-title">{p.name}</span>
            {p.confidence != null && (
              <span className="card-confidence">{Math.round(p.confidence * 100)}%</span>
            )}
          </div>
          {p.description && <p className="card-desc">{p.description}</p>}
          {p.involved_tables && p.involved_tables.length > 0 && (
            <div className="card-tags">
              {p.involved_tables.map((t) => (
                <span key={t} className="tag">{t}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Step 4: Grain options
function RenderGrain({ data }: { data: Record<string, unknown> }) {
  const options = (data.options || []) as Array<{
    description: string; recommended?: boolean; reasoning?: string;
    grain_columns?: string[]; source_table?: string;
  }>;
  if (!options.length) return <p className="empty-text">未生成粒度选项</p>;
  return (
    <div className="suggestion-cards">
      {options.map((o, i) => (
        <div key={i} className={`suggestion-card ${o.recommended ? 'card-recommended' : ''}`}>
          <div className="card-header">
            <span className="card-title">
              {o.recommended && <span className="recommended-badge">推荐</span>}
              选项 {i + 1}
            </span>
            {o.source_table && <span className="card-meta">源表: {o.source_table}</span>}
          </div>
          <p className="card-desc">{o.description}</p>
          {o.reasoning && <p className="card-reasoning">{o.reasoning}</p>}
          {o.grain_columns && o.grain_columns.length > 0 && (
            <div className="card-tags">
              {o.grain_columns.map((c) => (
                <span key={c} className="tag">{c}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Step 5: Dimensions
function RenderDimensions({ data }: { data: Record<string, unknown> }) {
  const dims = (data.dimensions || []) as Array<{
    name: string; source_table?: string; description?: string;
    is_degenerate?: boolean; is_date_dimension?: boolean;
    columns?: string[]; confidence?: number;
  }>;
  if (!dims.length) return <p className="empty-text">未生成维度建议</p>;
  return (
    <div className="suggestion-cards compact">
      {dims.map((d) => (
        <div key={d.name} className={`suggestion-card dim-card ${d.is_degenerate ? 'card-degenerate' : ''}`}>
          <div className="card-header">
            <span className="card-title">
              {d.is_date_dimension && <span className="type-badge date">日期</span>}
              {d.is_degenerate && <span className="type-badge degen">退化</span>}
              {d.name}
            </span>
            {d.confidence != null && (
              <span className="card-confidence">{Math.round(d.confidence * 100)}%</span>
            )}
          </div>
          {d.description && <p className="card-desc">{d.description}</p>}
          <div className="card-meta-row">
            {d.source_table && <span className="card-meta">源表: {d.source_table}</span>}
            {d.columns && (
              <span className="card-meta">{d.columns.length} 列</span>
            )}
          </div>
          {d.columns && d.columns.length > 0 && (
            <div className="card-tags">
              {d.columns.slice(0, 6).map((c) => (
                <span key={c} className="tag tag-sm">{c}</span>
              ))}
              {d.columns.length > 6 && <span className="tag tag-sm tag-more">+{d.columns.length - 6}</span>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Step 6: Measures
function RenderMeasures({ data }: { data: Record<string, unknown> }) {
  const measures = (data.measures || []) as Array<{
    name: string; source_column?: string; source_table?: string;
    aggregation?: string; description?: string; confidence?: number; data_type?: string;
  }>;
  if (!measures.length) return <p className="empty-text">未生成度量建议</p>;
  return (
    <div className="suggestion-cards compact">
      {measures.map((m) => (
        <div key={m.name} className="suggestion-card measure-card">
          <div className="card-header">
            <span className="card-title">{m.name}</span>
            <span className="agg-badge">{m.aggregation || 'SUM'}</span>
          </div>
          {m.description && <p className="card-desc">{m.description}</p>}
          <div className="card-meta-row">
            {m.source_column && <span className="card-meta">列: {m.source_column}</span>}
            {m.source_table && <span className="card-meta">表: {m.source_table}</span>}
            {m.data_type && <span className="card-meta">类型: {m.data_type}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// Step 7: Model summary
function RenderModel({ data }: { data: Record<string, unknown> }) {
  const model = data.model as {
    fact_table?: { name: string; measures?: { name: string }[]; dimension_keys?: string[] };
    dimensions?: { name: string; is_degenerate?: boolean }[];
    business_process?: string;
  } | undefined;
  if (!model) return <pre className="suggestion-text">{JSON.stringify(data, null, 2)}</pre>;

  const fact = model.fact_table;
  const dims = model.dimensions || [];
  const nonDegen = dims.filter(d => !d.is_degenerate);
  const degen = dims.filter(d => d.is_degenerate);

  return (
    <div className="model-summary">
      <div className="model-summary-header">
        <span className="model-bp">{model.business_process}</span>
        <span className="model-status-badge">模型已验证</span>
      </div>
      {fact && (
        <div className="model-section">
          <h4>事实表: {fact.name}</h4>
          <div className="card-meta-row">
            <span className="card-meta">{fact.measures?.length || 0} 个度量</span>
            <span className="card-meta">{fact.dimension_keys?.length || 0} 个维度键</span>
          </div>
        </div>
      )}
      <div className="model-section">
        <h4>维度表 ({nonDegen.length})</h4>
        <div className="card-tags">
          {nonDegen.map(d => <span key={d.name} className="tag">{d.name}</span>)}
        </div>
      </div>
      {degen.length > 0 && (
        <div className="model-section">
          <h4>退化维度 ({degen.length})</h4>
          <div className="card-tags">
            {degen.map(d => <span key={d.name} className="tag tag-degen">{d.name}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}

function renderSuggestion(stepNumber: number, suggestion: Record<string, unknown>) {
  switch (stepNumber) {
    case 3: return <RenderProcesses data={suggestion} />;
    case 4: return <RenderGrain data={suggestion} />;
    case 5: return <RenderDimensions data={suggestion} />;
    case 6: return <RenderMeasures data={suggestion} />;
    case 7: return <RenderModel data={suggestion} />;
    default: return <pre className="suggestion-text">{JSON.stringify(suggestion, null, 2)}</pre>;
  }
}

export function AISuggestionBubble({
  stepNumber,
  suggestion,
  confidence,
  loading,
  error,
  onAccept,
  onModify,
  onReject,
  onRetry,
}: Props) {
  if (loading) {
    return (
      <div className="ai-bubble ai-bubble-loading">
        <div className="ai-header">
          <div className="ai-badge">AI</div>
          <span className="loading-text">正在分析...</span>
          <ElapsedTimer />
        </div>
        <div className="ai-skeleton">
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
          <div className="skeleton-line" />
        </div>
      </div>
    );
  }

  if (error) {
    const isTimeout = error.includes('Timeout') || error.includes('timed out');
    return (
      <div className="ai-bubble ai-bubble-error">
        <div className="ai-badge">AI</div>
        <div className="ai-content">
          <p className="error-text">
            {isTimeout ? 'AI 分析超时，请重试（模型响应可能较慢）' : error}
          </p>
          <div className="ai-actions">
            <button className="btn btn-retry" onClick={onRetry}>重试</button>
          </div>
        </div>
      </div>
    );
  }

  if (!suggestion) {
    return (
      <div className="ai-bubble ai-bubble-empty">
        <div className="ai-badge">AI</div>
        <p className="empty-text">等待 AI 分析...</p>
      </div>
    );
  }

  return (
    <div className="ai-bubble ai-bubble-suggested">
      <div className="ai-header">
        <div className="ai-badge">AI</div>
        {confidence != null && (
          <span className="confidence-badge">
            AI 置信度 {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
      <div className="ai-content">
        {renderSuggestion(stepNumber, suggestion)}
      </div>
      <div className="ai-actions">
        <button className="btn btn-accept" onClick={onAccept}>接受</button>
        <button className="btn btn-modify" onClick={onModify}>修改</button>
        <button className="btn btn-reject" onClick={onReject}>拒绝</button>
      </div>
    </div>
  );
}
