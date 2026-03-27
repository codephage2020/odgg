// Compact vertical step progress indicator
import { STEPS } from '../types';
import type { StepState } from '../types';

interface Props {
  steps: StepState[];
}

export function StepProgress({ steps }: Props) {
  const completed = steps.filter((s) => s.status === 'completed').length;
  const progress = Math.round((completed / steps.length) * 100);

  return (
    <div className="step-progress-panel">
      <div className="sp-header">
        <span className="sp-title">建模进度</span>
        <span className="sp-pct">{progress}%</span>
      </div>
      <div className="sp-bar">
        <div className="sp-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="sp-steps">
        {STEPS.map((def) => {
          const state = steps.find((s) => s.step_number === def.number);
          const status = state?.status || 'locked';
          return (
            <div key={def.number} className={`sp-step sp-${status}`}>
              <span className="sp-dot">
                {status === 'completed' ? '✓' : def.number}
              </span>
              <span className="sp-name">{def.name}</span>
              {status === 'ai_thinking' && <span className="sp-thinking" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
