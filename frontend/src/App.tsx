// ODGG — Canvas-centric dimensional modeling workbench
import { useEffect, useCallback } from 'react';
import { DatasourceManager } from './components/DatasourceManager';
import { StepProgress } from './components/StepProgress';
import { DBInfoPanel } from './components/DBInfoPanel';
import { ModelDiagram } from './components/ModelDiagram';
import { AIChatPanel } from './components/chat/AIChatPanel';
import { BottomDrawer } from './components/BottomDrawer';
import { useSessionStore } from './store/sessionStore';
import { useChatStore } from './store/chatStore';
import type { MetadataSnapshot } from './types';
import './App.css';

function App() {
  const {
    session,
    loading,
    error,
    createSession,
    confirmStep,
    discoverMetadata,
    clearError,
  } = useSessionStore();

  const addMessage = useChatStore((s) => s.addMessage);

  useEffect(() => {
    createSession();
  }, [createSession]);

  const handleConnect = useCallback(
    async (url: string, schema: string) => {
      try {
        const snapshot = await discoverMetadata(url, schema);
        if (session) {
          session.metadata_snapshot = snapshot as unknown as Record<string, unknown>;
        }
        await confirmStep(1, { connected: true });
        await confirmStep(2, { tables: (snapshot as MetadataSnapshot).tables.length });
        addMessage({
          role: 'system',
          content: `已连接数据库，发现 ${(snapshot as MetadataSnapshot).tables.length} 张表`,
          status: 'complete',
        });
      } catch {
        // Error handled in store
      }
    },
    [session, discoverMetadata, confirmStep, addMessage]
  );

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

  return (
    <div className="workbench">
      {/* Header */}
      <header className="wb-header">
        <h1>ODGG</h1>
        <span className="wb-subtitle">数据建模工作台</span>
        <div className="wb-header-spacer" />
        {error && (
          <div className="wb-error">
            <span>{error}</span>
            <button onClick={clearError}>×</button>
          </div>
        )}
      </header>

      {/* Left Sidebar */}
      <aside className="wb-left">
        <DatasourceManager onConnect={handleConnect} loading={loading} />
        <div className="wb-left-divider" />
        <StepProgress steps={session.steps} />
        <DBInfoPanel metadata={metadata} />
      </aside>

      {/* Center Canvas */}
      <main className="wb-center">
        <ModelDiagram />
      </main>

      {/* Right Panel — AI Chat */}
      <aside className="wb-right">
        <AIChatPanel />
      </aside>

      {/* Bottom Drawer — Code Output */}
      <BottomDrawer />
    </div>
  );
}

export default App;
