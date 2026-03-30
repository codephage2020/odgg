// Single section card — edit content, regenerate with instructions, view draft history
import { useState, useCallback, useRef, useEffect } from 'react';
import { useBriefStore } from '../../store/briefStore';
import { SECTION_LABELS, SECTION_ICONS } from '../../types/brief';
import type { BriefSection, SectionType } from '../../types/brief';

interface BriefSectionCardProps {
  section: BriefSection;
  briefId: string;
}

export function BriefSectionCard({ section, briefId }: BriefSectionCardProps) {
  const { updateSection, regenerateSection } = useBriefStore();
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(section.content);
  const [showDrafts, setShowDrafts] = useState(false);
  const [showRedraftInput, setShowRedraftInput] = useState(false);
  const [redraftInstructions, setRedraftInstructions] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const redraftRef = useRef<HTMLInputElement>(null);

  // Sync content when section updates from SSE
  useEffect(() => {
    if (!editing) {
      setContent(section.content);
    }
  }, [section.content, editing]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [content, editing]);

  const handleSave = useCallback(async () => {
    if (content !== section.content) {
      await updateSection(briefId, section.id, { content });
    }
    setEditing(false);
  }, [content, section.content, section.id, briefId, updateSection]);

  // Focus the redraft input when it appears
  useEffect(() => {
    if (showRedraftInput && redraftRef.current) {
      redraftRef.current.focus();
    }
  }, [showRedraftInput]);

  const handleRegenerate = useCallback(async () => {
    setRegenerating(true);
    setShowRedraftInput(false);
    setRedraftInstructions('');
    try {
      await regenerateSection(briefId, section.id);
    } finally {
      setRegenerating(false);
    }
  }, [briefId, section.id, regenerateSection]);

  const handleRestoreDraft = useCallback(
    async (draft: string) => {
      await updateSection(briefId, section.id, { content: draft });
      setShowDrafts(false);
    },
    [briefId, section.id, updateSection]
  );

  const label =
    section.name || SECTION_LABELS[section.section_type as SectionType] || section.section_type;
  const icon = SECTION_ICONS[section.section_type as SectionType] || '📄';

  return (
    <div
      id={`section-${section.id}`}
      className={`brief-section ${section.user_edited ? 'edited' : 'ai-draft'}`}
    >
      {/* Section header */}
      <div className="brief-section-header">
        <span className="brief-section-icon">{icon}</span>
        <h3 className="brief-section-title">{label}</h3>
        <div className="brief-section-badges">
          {!section.user_edited && section.ai_drafts.length > 0 && (
            <span className="brief-badge ai">✦ AI draft</span>
          )}
          {section.user_edited && (
            <span className="brief-badge edited">✎ Edited</span>
          )}
        </div>
        <div className="brief-section-actions">
          {section.ai_drafts.length > 1 && (
            <button
              className="brief-action-btn"
              onClick={() => setShowDrafts(!showDrafts)}
              title="查看草稿历史"
            >
              📋 {section.ai_drafts.length}
            </button>
          )}
          <button
            className="brief-action-btn"
            onClick={() => setShowRedraftInput(!showRedraftInput)}
            disabled={regenerating}
            title="重新生成（可附加指令）"
          >
            {regenerating ? '⏳' : '🔄'}
          </button>
        </div>
      </div>

      {/* Draft history popover */}
      {showDrafts && (
        <div className="brief-draft-history">
          <div className="brief-draft-history-title">草稿历史</div>
          {section.ai_drafts.map((draft, i) => (
            <div key={i} className="brief-draft-item">
              <div className="brief-draft-preview">
                {draft.substring(0, 100)}
                {draft.length > 100 ? '...' : ''}
              </div>
              <button
                className="brief-draft-restore"
                onClick={() => handleRestoreDraft(draft)}
              >
                恢复
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Redraft input */}
      {showRedraftInput && !regenerating && (
        <div className="brief-redraft-bar">
          <input
            ref={redraftRef}
            className="brief-redraft-input"
            placeholder="输入修改指令（可选），例如：更详细地描述维度属性..."
            value={redraftInstructions}
            onChange={(e) => setRedraftInstructions(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRegenerate();
              if (e.key === 'Escape') {
                setShowRedraftInput(false);
                setRedraftInstructions('');
              }
            }}
          />
          <button className="brief-redraft-go" onClick={handleRegenerate}>
            重新生成
          </button>
          <button
            className="brief-redraft-cancel"
            onClick={() => { setShowRedraftInput(false); setRedraftInstructions(''); }}
          >
            取消
          </button>
        </div>
      )}

      {/* Content area */}
      {editing ? (
        <div className="brief-section-editing">
          <textarea
            ref={textareaRef}
            className="brief-section-textarea"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onBlur={handleSave}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setContent(section.content);
                setEditing(false);
              }
            }}
          />
          <div className="brief-section-edit-hint">
            按 Escape 取消 · 点击外部保存
          </div>
        </div>
      ) : (
        <div
          className="brief-section-content"
          onClick={() => setEditing(true)}
        >
          {section.content ? (
            <div className="brief-section-text">{section.content}</div>
          ) : (
            <div className="brief-section-placeholder">
              点击编辑...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
