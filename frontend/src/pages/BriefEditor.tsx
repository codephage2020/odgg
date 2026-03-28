// ODGG — Modeling Brief Editor (document-centric mode)
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBriefStore } from '../store/briefStore';
import { BriefSidebar } from '../components/brief/BriefSidebar';
import { BriefSectionCard } from '../components/brief/BriefSectionCard';
import { BriefShimmer } from '../components/brief/BriefShimmer';
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
    clearError,
  } = useBriefStore();

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');

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
        </div>
        <div className="brief-header-spacer" />
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
          onDraft={sections.length === 0 ? handleDraft : undefined}
        />

        {/* Document */}
        <main className="brief-document">
          {sections.length === 0 && !drafting && (
            <div className="brief-empty-doc">
              <p>这个 Brief 还没有任何内容。</p>
              {currentBrief.metadata_snapshot ? (
                <button className="brief-draft-btn" onClick={handleDraft}>
                  ✦ AI 起草所有章节
                </button>
              ) : (
                <p className="brief-hint">请先连接数据库并发现元数据。</p>
              )}
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
        </main>
      </div>
    </div>
  );
}
