// Custom React Flow node for fact table
import { Handle, Position, type NodeProps } from '@xyflow/react';

export interface FactNodeData {
  label: string;
  measures: string[];
  grainDescription?: string;
}

export function FactNode({ data }: NodeProps) {
  const d = data as unknown as FactNodeData;
  return (
    <div className="diagram-node fact-node">
      <Handle type="target" position={Position.Top} style={{ visibility: 'hidden' }} />
      <div className="node-title">{d.label}</div>
      {d.grainDescription && (
        <div className="node-grain">{d.grainDescription}</div>
      )}
      <div className="node-fields">
        {d.measures.slice(0, 8).map((m) => (
          <div key={m} className="node-field measure">{m}</div>
        ))}
        {d.measures.length > 8 && (
          <div className="node-field more">+{d.measures.length - 8} more</div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
    </div>
  );
}
