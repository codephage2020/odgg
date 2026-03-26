// Star schema model diagram using React Flow
import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface DimensionData {
  name: string;
  columns?: string[];
  is_degenerate?: boolean;
}

interface FactData {
  name: string;
  measures?: { name: string }[];
}

interface Props {
  factTable: FactData | null;
  dimensions: DimensionData[];
}

export function ModelDiagram({ factTable, dimensions }: Props) {
  const { nodes, edges } = useMemo(() => {
    const n: Node[] = [];
    const e: Edge[] = [];

    if (!factTable) {
      return { nodes: n, edges: e };
    }

    // Fact table in center
    n.push({
      id: 'fact',
      position: { x: 300, y: 250 },
      data: {
        label: (
          <div className="diagram-node fact-node">
            <div className="node-title">{factTable.name}</div>
            {factTable.measures?.map((m) => (
              <div key={m.name} className="node-field measure">
                {m.name}
              </div>
            ))}
          </div>
        ),
      },
      sourcePosition: Position.Top,
      targetPosition: Position.Bottom,
    });

    // Dimensions around the fact table
    const nonDegenerate = dimensions.filter((d) => !d.is_degenerate);
    const angleStep = (2 * Math.PI) / Math.max(nonDegenerate.length, 1);
    const radius = 200;

    nonDegenerate.forEach((dim, i) => {
      const angle = angleStep * i - Math.PI / 2;
      const x = 300 + radius * Math.cos(angle);
      const y = 250 + radius * Math.sin(angle);

      n.push({
        id: `dim-${dim.name}`,
        position: { x, y },
        data: {
          label: (
            <div className="diagram-node dim-node">
              <div className="node-title">{dim.name}</div>
              {dim.columns?.slice(0, 5).map((c) => (
                <div key={c} className="node-field">
                  {c}
                </div>
              ))}
              {(dim.columns?.length || 0) > 5 && (
                <div className="node-field more">
                  +{(dim.columns?.length || 0) - 5} more
                </div>
              )}
            </div>
          ),
        },
      });

      e.push({
        id: `edge-${dim.name}`,
        source: `dim-${dim.name}`,
        target: 'fact',
        animated: true,
        style: { stroke: '#2563eb' },
      });
    });

    return { nodes: n, edges: e };
  }, [factTable, dimensions]);

  if (!factTable) {
    return (
      <div className="model-diagram-empty">
        <p>完成建模步骤后，星型模型图将在此显示</p>
      </div>
    );
  }

  return (
    <div className="model-diagram" style={{ height: 500 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
