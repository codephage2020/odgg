// Interactive star schema model diagram — always visible, progressively populated
import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FactNode } from './diagram/FactNode';
import { DimensionNode } from './diagram/DimensionNode';
import { useSessionStore } from '../store/sessionStore';

const nodeTypes: NodeTypes = {
  fact: FactNode,
  dim: DimensionNode,
};

export function ModelDiagram() {
  const session = useSessionStore((s) => s.session);

  const { nodes, edges, placeholder } = useMemo(() => {
    const n: Node[] = [];
    const e: Edge[] = [];

    if (!session) return { nodes: n, edges: e, placeholder: '初始化中...' };

    const currentStep = session.steps.find(
      (s) => s.status === 'active' || s.status === 'ai_thinking' || s.status === 'ai_suggested'
    )?.step_number || session.steps.filter(s => s.status === 'completed').length + 1;

    if (currentStep <= 2) {
      return { nodes: n, edges: e, placeholder: '连接数据源后开始建模' };
    }

    // Try to get model data from multiple sources
    const model = session.dimensional_model as Record<string, unknown> | null;
    const step7 = session.steps.find((s) => s.step_number === 7);
    const step7Model = (step7?.ai_suggestion as Record<string, unknown>)?.model as Record<string, unknown> | undefined;
    const modelData = model || step7Model;

    // Get dimensions from model or step 5 suggestion
    const step5 = session.steps.find((s) => s.step_number === 5);
    const step6 = session.steps.find((s) => s.step_number === 6);

    let factName = `fact_${session.business_process?.toLowerCase().replace(/\s+/g, '_') || 'unknown'}`;
    let measures: string[] = [];
    let dimensions: Array<{
      name: string; columns?: string[]; source_table?: string;
      is_degenerate?: boolean; is_date_dimension?: boolean;
    }> = [];

    if (modelData) {
      // Full model available
      const ft = modelData.fact_table as { name: string; measures?: { name: string }[] } | undefined;
      const dims = modelData.dimensions as Array<{
        name: string; columns?: string[]; source_table?: string;
        is_degenerate?: boolean; is_date_dimension?: boolean;
      }> | undefined;
      if (ft) {
        factName = ft.name;
        measures = ft.measures?.map((m) => m.name) || [];
      }
      if (dims) dimensions = dims;
    } else {
      // Progressive: build from step data
      if (step6?.ai_suggestion) {
        const ms = (step6.ai_suggestion as Record<string, unknown>).measures as Array<{ name: string }> | undefined;
        measures = ms?.map((m) => m.name) || [];
      } else if (Array.isArray(session.selected_measures)) {
        measures = session.selected_measures.map((m) =>
          typeof m === 'string' ? m : ((m as Record<string, string>).name || '')
        ).filter(Boolean);
      }

      if (step5?.ai_suggestion) {
        dimensions = ((step5.ai_suggestion as Record<string, unknown>).dimensions || []) as typeof dimensions;
      } else if (Array.isArray(session.selected_dimensions)) {
        dimensions = session.selected_dimensions.map((d) =>
          typeof d === 'string'
            ? { name: d.startsWith('dim_') ? d : `dim_${d}`, columns: [] }
            : d as typeof dimensions[0]
        );
      }
    }

    // Need at least something to render
    if (currentStep < 3 && !session.business_process) {
      return { nodes: n, edges: e, placeholder: 'AI 正在分析业务过程...' };
    }

    // Fact table
    n.push({
      id: 'fact',
      type: 'fact',
      position: { x: 400, y: 300 },
      data: {
        label: factName,
        measures,
        grainDescription: session.grain_description || undefined,
      },
    });

    // Dimensions
    const nonDegenerate = dimensions.filter((d) => !d.is_degenerate);
    const angleStep = (2 * Math.PI) / Math.max(nonDegenerate.length, 1);
    const radius = Math.max(220, nonDegenerate.length * 30);

    nonDegenerate.forEach((dim, i) => {
      const angle = angleStep * i - Math.PI / 2;
      const x = 400 + radius * Math.cos(angle);
      const y = 300 + radius * Math.sin(angle);

      n.push({
        id: `dim-${dim.name}`,
        type: 'dim',
        position: { x, y },
        data: {
          label: dim.name,
          columns: dim.columns || [],
          isDegenerate: dim.is_degenerate || false,
          isDate: dim.is_date_dimension || false,
          sourceTable: dim.source_table || '',
        },
      });

      e.push({
        id: `edge-${dim.name}`,
        source: `dim-${dim.name}`,
        target: 'fact',
        animated: true,
        style: { stroke: '#2563eb', strokeWidth: 1.5 },
      });
    });

    if (n.length === 1 && measures.length === 0) {
      return { nodes: n, edges: e, placeholder: null };
    }

    return { nodes: n, edges: e, placeholder: null };
  }, [session]);

  if (placeholder) {
    return (
      <div className="diagram-placeholder">
        <p>{placeholder}</p>
      </div>
    );
  }

  return (
    <div className="diagram-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} color="#e5e7eb" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
