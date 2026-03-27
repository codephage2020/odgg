// ODGG main application
import { useEffect, useRef, useCallback, useState } from 'react';
import { StepNavigator } from './components/StepNavigator';
import { DBInfoPanel } from './components/DBInfoPanel';
import { NotebookCell } from './components/NotebookCell';
import { ConnectStep } from './components/ConnectStep';
import { ModelDiagram } from './components/ModelDiagram';
import { CodeOutput } from './components/CodeOutput';
import { useSessionStore } from './store/sessionStore';
import type { MetadataSnapshot } from './types';
import './App.css';

function App() {
  const {
    session,
    loading,
    error,
    createSession,
    confirmStep,
    rollbackToStep,
    getSuggestion,
    discoverMetadata,
    generateCode,
    clearError,
  } = useSessionStore();

  // All hooks MUST be called before any conditional return
  const prevStepRef = useRef<number | null>(null);
  const [codeOutput, setCodeOutput] = useState<{
    ddl: string; etl: string; dbt: Record<string, string>; dataDictionary: string;
  } | null>(null);
  const codeGenRef = useRef(false);

  useEffect(() => {
    createSession();
  }, [createSession]);

  const handleGetSuggestion = useCallback(async (stepNumber: number) => {
    try {
      await getSuggestion(stepNumber);
    } catch {
      // Error handled in store
    }
  }, [getSuggestion]);

  // Auto-trigger AI suggestion when a step with AI (3-7) becomes active
  useEffect(() => {
    if (!session || loading) return;
    const activeStep = session.steps.find((s) => s.status === 'active');
    if (
      activeStep &&
      activeStep.step_number >= 3 &&
      activeStep.step_number <= 7 &&
      activeStep.step_number !== prevStepRef.current
    ) {
      prevStepRef.current = activeStep.step_number;
      handleGetSuggestion(activeStep.step_number);
    }
  }, [session, loading, handleGetSuggestion]);

  // Auto-trigger code generation when Step 8 becomes active
  useEffect(() => {
    if (!session || loading || codeGenRef.current) return;
    const step8 = session.steps.find((s) => s.step_number === 8);
    if (step8?.status === 'active' && session.dimensional_model) {
      codeGenRef.current = true;
      generateCode('full', true)
        .then((data) => {
          setCodeOutput({
            ddl: (data as Record<string, string>).ddl || '',
            etl: (data as Record<string, string>).etl || '',
            dbt: (data as Record<string, Record<string, string>>).dbt as Record<string, string> || {},
            dataDictionary: (data as Record<string, string>).data_dictionary || '',
          });
        })
        .catch(() => {})
        .finally(() => { codeGenRef.current = false; });
    }
  }, [session, loading, generateCode]);

  if (!session) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>初始化会话...</p>
      </div>
    );
  }

  const metadata: MetadataSnapshot | null = session.metadata_snapshot
    ? (session.metadata_snapshot as unknown as MetadataSnapshot)
    : null;

  const currentStep = session.steps.find(
    (s) =>
      s.status === 'active' ||
      s.status === 'ai_thinking' ||
      s.status === 'ai_suggested'
  )?.step_number || 1;

  const handleStepClick = (stepNumber: number) => {
    const el = document.getElementById(`step-${stepNumber}`);
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleConnect = async (url: string, schema: string) => {
    try {
      const snapshot = await discoverMetadata(url, schema);
      session.metadata_snapshot = snapshot as unknown as Record<string, unknown>;
      await confirmStep(1, { connected: true });
      await confirmStep(2, { tables: snapshot.tables.length });
    } catch {
      // Error handled in store
    }
  };

  // Extract model data from session or step 7's AI suggestion
  const step7 = session.steps.find((s) => s.step_number === 7);
  const modelData = session.dimensional_model
    || (step7?.ai_suggestion as Record<string, unknown>)?.model as Record<string, unknown> | null
    || null;

  const handleExportDDL = () => {
    if (!codeOutput?.ddl) return;
    const blob = new Blob([codeOutput.ddl], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'schema.sql';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportDbt = () => {
    if (!codeOutput?.dbt) return;
    // Download all dbt files as a single concatenated file
    const content = Object.entries(codeOutput.dbt)
      .map(([name, sql]) => `-- ${name}\n${sql}`)
      .join('\n\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dbt_models.sql';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>ODGG — 数据建模工作台</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" disabled={!codeOutput} onClick={handleExportDDL}>
            导出 SQL
          </button>
          <button className="btn btn-secondary" disabled={!codeOutput} onClick={handleExportDbt}>
            导出 dbt
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={clearError}>×</button>
        </div>
      )}

      <div className="app-layout">
        <aside className="app-sidebar">
          <StepNavigator steps={session.steps} onStepClick={handleStepClick} />
          <DBInfoPanel metadata={metadata} />
        </aside>

        <main className="app-main">
          {session.steps.map((step) => (
            <div key={step.step_number} id={`step-${step.step_number}`}>
              <NotebookCell
                step={step}
                isActive={step.step_number === currentStep}
                loading={loading}
                onAccept={() => confirmStep(step.step_number)}
                onModify={() => {}}
                onReject={() => rollbackToStep(step.step_number)}
                onRetry={() => handleGetSuggestion(step.step_number)}
                onRollback={() => rollbackToStep(step.step_number)}
              >
                {step.step_number === 1 && step.status !== 'completed' && (
                  <ConnectStep onConnect={handleConnect} loading={loading} />
                )}

                {step.step_number === 7 && (
                  <ModelDiagram
                    factTable={
                      modelData
                        ? (modelData as Record<string, unknown>)
                            .fact_table as { name: string; measures: { name: string }[] }
                        : null
                    }
                    dimensions={
                      modelData
                        ? ((modelData as Record<string, unknown>)
                            .dimensions as { name: string; columns: string[]; is_degenerate: boolean }[])
                        : []
                    }
                  />
                )}

                {step.step_number === 8 && codeOutput && (
                  <CodeOutput
                    ddl={codeOutput.ddl}
                    etl={codeOutput.etl}
                    dbt={codeOutput.dbt}
                    dataDictionary={codeOutput.dataDictionary}
                    loading={loading}
                  />
                )}

                {step.step_number === 8 && !codeOutput && step.status === 'active' && loading && (
                  <div className="code-generating">
                    <div className="spinner" />
                    <p>正在生成 DDL、ETL 和 dbt 代码...</p>
                  </div>
                )}
              </NotebookCell>
            </div>
          ))}
        </main>
      </div>
    </div>
  );
}

export default App;
