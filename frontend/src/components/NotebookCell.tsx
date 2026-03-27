// Notebook cell component for each modeling step
import type { StepState, StepStatus } from '../types';
import { STEPS } from '../types';
import { AISuggestionBubble } from './AISuggestionBubble';

interface Props {
  step: StepState;
  isActive: boolean;
  loading: boolean;
  onAccept: () => void;
  onModify: () => void;
  onReject: () => void;
  onRetry: () => void;
  onRollback: () => void;
  children?: React.ReactNode;
}

const STATUS_LABELS: Record<StepStatus, string> = {
  locked: '待解锁',
  active: '当前步骤',
  ai_thinking: 'AI 分析中...',
  ai_suggested: 'AI 已建议',
  user_confirmed: '已确认',
  completed: '已完成',
};

export function NotebookCell({
  step,
  isActive,
  loading,
  onAccept,
  onModify,
  onReject,
  onRetry,
  onRollback,
  children,
}: Props) {
  const stepDef = STEPS.find((s) => s.number === step.step_number);
  if (!stepDef) return null;

  const isCompleted = step.status === 'completed';
  const isLocked = step.status === 'locked';

  return (
    <div
      className={`notebook-cell cell-${step.status} ${isActive ? 'cell-active' : ''}`}
    >
      <div className="cell-header">
        <div className="cell-title">
          Step {stepDef.number}: {stepDef.name}
        </div>
        <div className="cell-status-group">
          <span className={`cell-status status-${step.status}`}>
            {STATUS_LABELS[step.status]}
          </span>
          {isCompleted && (
            <button className="btn btn-sm btn-rollback" onClick={onRollback}>
              回退
            </button>
          )}
        </div>
      </div>

      {!isLocked && (
        <div className="cell-body">
          {/* AI suggestion bubble for steps 3-7 */}
          {step.step_number >= 3 && step.step_number <= 7 && (
            <AISuggestionBubble
              stepNumber={step.step_number}
              suggestion={step.ai_suggestion}
              confidence={step.confidence}
              loading={loading && step.status === 'ai_thinking'}
              error={step.error}
              onAccept={onAccept}
              onModify={onModify}
              onReject={onReject}
              onRetry={onRetry}
            />
          )}

          {/* Step-specific content */}
          {children}

          {/* User input display when confirmed */}
          {step.user_input && isCompleted && (
            <div className="user-input-display">
              <span className="input-label">你的选择:</span>
              <pre>{JSON.stringify(step.user_input, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
