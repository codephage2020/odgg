// ODGG main application
import { useEffect } from 'react';
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
    clearError,
  } = useSessionStore();

  useEffect(() => {
    createSession();
  }, [createSession]);

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

  const handleGetSuggestion = async (stepNumber: number) => {
    try {
      await getSuggestion(stepNumber);
    } catch {
      // Error handled in store
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>ODGG — 数据建模工作台</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" disabled={!session.dimensional_model}>导出 SQL</button>
          <button className="btn btn-secondary" disabled={!session.dimensional_model}>导出 dbt</button>
          <button className="btn btn-primary" disabled={!session.dimensional_model}>一键建表</button>
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
                      session.dimensional_model
                        ? (session.dimensional_model as Record<string, unknown>)
                            .fact_table as { name: string; measures: { name: string }[] }
                        : null
                    }
                    dimensions={
                      session.dimensional_model
                        ? ((session.dimensional_model as Record<string, unknown>)
                            .dimensions as { name: string; columns: string[]; is_degenerate: boolean }[])
                        : []
                    }
                  />
                )}

                {step.step_number === 8 && session.generated_ddl && (
                  <CodeOutput
                    ddl={session.generated_ddl}
                    etl={session.generated_etl}
                    dbt={session.generated_dbt}
                    dataDictionary=""
                    onExecute={() => {}}
                    loading={loading}
                  />
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
