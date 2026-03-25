// Left sidebar: step navigation with progress tracking
import { STEPS } from '../types';
import type { StepState } from '../types';

interface Props {
  steps: StepState[];
  onStepClick: (stepNumber: number) => void;
}

export function StepNavigator({ steps, onStepClick }: Props) {
  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const progress = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="step-navigator">
      <div className="step-progress">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <span className="progress-text">{progress}% 完成</span>
      </div>

      <div className="step-list">
        {STEPS.map((stepDef) => {
          const state = steps.find((s) => s.step_number === stepDef.number);
          const status = state?.status || 'locked';

          return (
            <button
              key={stepDef.number}
              className={`step-item step-${status}`}
              onClick={() => onStepClick(stepDef.number)}
              disabled={status === 'locked'}
            >
              <div className="step-num">
                {status === 'completed' ? '✓' : stepDef.number}
              </div>
              <div className="step-info">
                <span className="step-name">{stepDef.name}</span>
                {state?.confidence != null && status === 'ai_suggested' && (
                  <span className="step-confidence">
                    {Math.round(state.confidence * 100)}%
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
