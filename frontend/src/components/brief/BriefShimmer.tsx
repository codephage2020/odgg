// Shimmer placeholder for sections being drafted by AI
interface BriefShimmerProps {
  label: string;
  active: boolean;
}

export function BriefShimmer({ label, active }: BriefShimmerProps) {
  return (
    <div className={`brief-shimmer ${active ? 'active' : ''}`} role="status" aria-live="polite" aria-busy={active}>
      <div className="brief-shimmer-header">
        <span>{label}</span>
        {active && <span className="brief-shimmer-status">AI 起草中...</span>}
      </div>
      <div className="brief-shimmer-lines">
        <div className="brief-shimmer-line" style={{ width: '90%' }} />
        <div className="brief-shimmer-line" style={{ width: '75%' }} />
        <div className="brief-shimmer-line" style={{ width: '85%' }} />
        <div className="brief-shimmer-line" style={{ width: '60%' }} />
      </div>
    </div>
  );
}
