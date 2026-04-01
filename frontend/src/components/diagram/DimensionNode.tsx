// Custom React Flow node for dimension table
import { Handle, Position, type NodeProps } from '@xyflow/react';

export interface DimensionNodeData {
  label: string;
  columns: string[];
  isDegenerate?: boolean;
  isDate?: boolean;
  sourceTable?: string;
}

export function DimensionNode({ data }: NodeProps) {
  const d = data as unknown as DimensionNodeData;
  return (
    <div className={`diagram-node dim-node ${d.isDegenerate ? 'dim-degenerate' : ''}`}>
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
      <div className="node-header">
        <div className="node-title">{d.label}</div>
        {d.isDate && <span className="node-badge date">日期</span>}
        {d.isDegenerate && <span className="node-badge degen">退化</span>}
      </div>
      {d.sourceTable && <div className="node-source">{d.sourceTable}</div>}
      <div className="node-fields">
        {d.columns.slice(0, 5).map((c) => (
          <div key={c} className="node-field">{c}</div>
        ))}
        {d.columns.length > 5 && (
          <div className="node-field more" title={d.columns.slice(5).join('\n')}>
            +{d.columns.length - 5} more
          </div>
        )}
      </div>
      <Handle type="target" position={Position.Top} style={{ visibility: 'hidden' }} />
    </div>
  );
}
