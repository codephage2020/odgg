// ODGG — Modeling Brief Editor (document-centric mode)
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBriefStore } from '../store/briefStore';
import { BriefSidebar } from '../components/brief/BriefSidebar';
import { BriefSectionCard } from '../components/brief/BriefSectionCard';
import { BriefShimmer } from '../components/brief/BriefShimmer';
import { BriefConnectDialog } from '../components/brief/BriefConnectDialog';
import { ThemeToggle } from '../components/ThemeToggle';
import { SECTION_LABELS, SECTION_ICONS } from '../types/brief';
import type { SectionType } from '../types/brief';
import './BriefEditor.css';

export function BriefEditor() {
  const { briefId } = useParams<{ briefId: string }>();
  const navigate = useNavigate();

  const {
    currentBrief,
    loading,
    drafting,
    draftingSection,
    error,
    fetchBrief,
    updateBrief,
    draftSections,
    generateCode,
    clearError,
  } = useBriefStore();

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [showConnect, setShowConnect] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    if (briefId) {
      fetchBrief(briefId);
    }
  }, [briefId, fetchBrief]);

  const handleTitleSave = useCallback(async () => {
    if (currentBrief && titleDraft.trim() && titleDraft !== currentBrief.title) {
      await updateBrief(currentBrief.id, { title: titleDraft.trim() });
    }
    setEditingTitle(false);
  }, [currentBrief, titleDraft, updateBrief]);

  const handleDraft = useCallback(async () => {
    if (!currentBrief) return;
    await draftSections(currentBrief.id);
  }, [currentBrief, draftSections]);

  const handleConnected = useCallback(async () => {
    setShowConnect(false);
    // Refresh brief to get updated metadata_snapshot
    if (briefId) {
      await fetchBrief(briefId);
    }
  }, [briefId, fetchBrief]);

  const handleGenerate = useCallback(async () => {
    if (!currentBrief) return;
    try {
      const code = await generateCode(currentBrief.id);
      setGeneratedCode(code);
    } catch {
      // Error handled in store
    }
  }, [currentBrief, generateCode]);

  if (loading && !currentBrief) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>加载 Brief...</p>
      </div>
    );
  }

  if (!currentBrief) {
    return (
      <div className="brief-empty">
        <p>Brief 未找到</p>
        <button onClick={() => navigate('/brief')}>返回列表</button>
      </div>
    );
  }

  const sections = currentBrief.sections;
  const hasMetadata = !!currentBrief.metadata_snapshot;
  const hasSections = sections.length > 0;

  // Determine which sections are being shimmer-loaded
  const draftingSections = new Set<string>();
  if (drafting && draftingSection) {
    if (draftingSection === 'dimensions_and_measures') {
      draftingSections.add('dimension');
      draftingSections.add('measure');
    } else {
      draftingSections.add(draftingSection);
    }
  }

  // Section types that should show shimmer (not yet created)
  const existingTypes = new Set(sections.map((s) => s.section_type));
  const pendingSections: SectionType[] = (
    ['business_process', 'grain', 'dimension', 'measure'] as SectionType[]
  ).filter((t) => !existingTypes.has(t) && drafting);

  return (
    <div className="brief-editor">
      {/* Header */}
      <header className="brief-header">
        <button className="brief-back" onClick={() => navigate('/brief')}>
          ← 返回
        </button>
        <div className="brief-title-area">
          {editingTitle ? (
            <input
              className="brief-title-input"
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onBlur={handleTitleSave}
              onKeyDown={(e) => e.key === 'Enter' && handleTitleSave()}
              autoFocus
            />
          ) : (
            <h1
              className="brief-title"
              onClick={() => {
                setTitleDraft(currentBrief.title);
                setEditingTitle(true);
              }}
            >
              {currentBrief.title}
            </h1>
          )}
          <span className="brief-status-badge">{currentBrief.status}</span>
          {hasMetadata && (
            <span className="brief-db-badge">
              🗄 {currentBrief.database_name || 'Connected'}
            </span>
          )}
        </div>
        <div className="brief-header-spacer" />

        {/* Action buttons */}
        {!hasMetadata && (
          <button className="brief-header-btn" onClick={() => setShowConnect(true)}>
            🔌 连接数据库
          </button>
        )}
        {hasMetadata && !hasSections && !drafting && (
          <button className="brief-header-btn primary" onClick={handleDraft}>
            ✦ AI 起草
          </button>
        )}
        {hasSections && (
          <button className="brief-header-btn" onClick={handleGenerate} disabled={loading}>
            {loading ? '生成中...' : '⚡ 生成代码'}
          </button>
        )}

        <ThemeToggle />
        {error && (
          <div className="wb-error">
            <span>{error}</span>
            <button onClick={clearError}>×</button>
          </div>
        )}
      </header>

      <div className="brief-body">
        {/* Sidebar */}
        <BriefSidebar
          sections={sections}
          draftingSections={draftingSections}
          onDraft={hasMetadata && !hasSections ? handleDraft : undefined}
        />

        {/* Document */}
        <main className="brief-document">
          {/* Empty state: no metadata */}
          {!hasMetadata && !hasSections && (
            <div className="brief-empty-doc">
              <div className="brief-empty-icon">🗄</div>
              <h2>连接数据库开始建模</h2>
              <p>连接你的数据库，AI 将自动分析 schema 并起草维度模型。</p>
              <button
                className="brief-draft-btn"
                onClick={() => setShowConnect(true)}
              >
                🔌 连接数据库
              </button>
            </div>
          )}

          {/* Empty state: has metadata but no sections */}
          {hasMetadata && !hasSections && !drafting && (
            <div className="brief-empty-doc">
              <div className="brief-empty-icon">✦</div>
              <h2>元数据已就绪</h2>
              <p>
                发现了{' '}
                {(currentBrief.metadata_snapshot as Record<string, unknown[]>)?.tables?.length || '?'}{' '}
                张表。点击按钮让 AI 起草维度模型。
              </p>
              <button className="brief-draft-btn" onClick={handleDraft}>
                ✦ AI 起草所有章节
              </button>
            </div>
          )}

          {/* Existing sections */}
          {sections.map((section) => (
            <BriefSectionCard
              key={section.id}
              section={section}
              briefId={currentBrief.id}
            />
          ))}

          {/* Shimmer placeholders for drafting sections */}
          {pendingSections.map((type) => (
            <BriefShimmer
              key={type}
              label={`${SECTION_ICONS[type]} ${SECTION_LABELS[type]}`}
              active={draftingSections.has(type)}
            />
          ))}

          {/* Code output */}
          {generatedCode && (
            <div className="brief-code-output">
              <div className="brief-section-header">
                <span className="brief-section-icon">⚡</span>
                <h3 className="brief-section-title">生成的代码</h3>
                <button
                  className="brief-action-btn"
                  onClick={() => setGeneratedCode(null)}
                >
                  关闭
                </button>
              </div>
              {Object.entries(generatedCode).map(([key, value]) => (
                <div key={key} className="brief-code-block">
                  <div className="brief-code-label">{key.toUpperCase()}</div>
                  <pre className="brief-code-pre">
                    {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Connect dialog */}
      {showConnect && (
        <BriefConnectDialog
          briefId={currentBrief.id}
          onConnected={handleConnected}
          onClose={() => setShowConnect(false)}
        />
      )}
    </div>
  );
}
