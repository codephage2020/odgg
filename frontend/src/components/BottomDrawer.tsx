// Collapsible bottom drawer for code output
import { useState, useEffect, useCallback } from 'react';
import { CodeOutput } from './CodeOutput';
import { useSessionStore } from '../store/sessionStore';

export function BottomDrawer() {
  const { session, loading, generateCode } = useSessionStore();
  const [collapsed, setCollapsed] = useState(true);
  const [codeOutput, setCodeOutput] = useState<{
    ddl: string; etl: string; dbt: Record<string, string>; dataDictionary: string;
  } | null>(null);
  const [generating, setGenerating] = useState(false);

  // Auto-generate code when step 8 becomes active
  useEffect(() => {
    if (!session || generating || codeOutput) return;
    const step8 = session.steps.find((s) => s.step_number === 8);
    if (step8?.status === 'active' && session.dimensional_model) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- triggers async code gen on step transition
      setGenerating(true);
      setCollapsed(false);
      generateCode('full', true)
        .then((data) => {
          const d = data as Record<string, unknown>;
          setCodeOutput({
            ddl: (d.ddl as string) || '',
            etl: (d.etl as string) || '',
            dbt: (d.dbt as Record<string, string>) || {},
            dataDictionary: (d.data_dictionary as string) || '',
          });
        })
        .catch(() => {})
        .finally(() => setGenerating(false));
    }
  }, [session, generateCode, generating, codeOutput]);

  const handleGenerate = useCallback(() => {
    if (!session) return;
    setGenerating(true);
    generateCode('full', true)
      .then((data) => {
        const d = data as Record<string, unknown>;
        setCodeOutput({
          ddl: (d.ddl as string) || '',
          etl: (d.etl as string) || '',
          dbt: (d.dbt as Record<string, string>) || {},
          dataDictionary: (d.data_dictionary as string) || '',
        });
        setCollapsed(false);
      })
      .catch(() => {})
      .finally(() => setGenerating(false));
  }, [session, generateCode]);

  const hasModel = !!session?.dimensional_model;

  return (
    <div className={`bottom-drawer ${collapsed ? 'drawer-collapsed' : ''}`}>
      <button
        className="drawer-handle"
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
        aria-label={collapsed ? '展开代码输出' : '收起代码输出'}
      >
        <span className="drawer-title">
          代码输出
          {codeOutput && <span className="drawer-ready">已生成</span>}
        </span>
        <span className="drawer-actions">
          {hasModel && !codeOutput && (
            <button
              className="btn btn-sm btn-primary"
              onClick={(e) => { e.stopPropagation(); handleGenerate(); }}
              disabled={generating || loading}
            >
              {generating ? '生成中...' : '生成代码'}
            </button>
          )}
          <span className="drawer-toggle" aria-hidden="true">{collapsed ? '▲' : '▼'}</span>
        </span>
      </button>
      {!collapsed && (
        <div className="drawer-content">
          {codeOutput ? (
            <CodeOutput
              ddl={codeOutput.ddl}
              etl={codeOutput.etl}
              dbt={codeOutput.dbt}
              dataDictionary={codeOutput.dataDictionary}
              loading={loading}
            />
          ) : generating ? (
            <div className="drawer-loading">
              <div className="spinner" />
              <span>正在生成 DDL、ETL 和 dbt 代码...</span>
            </div>
          ) : (
            <div className="drawer-empty">
              <p>完成模型构建后可生成代码</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
