// Brief editor sidebar — section navigation + draft trigger + add section
import { useState, useRef, useEffect } from 'react';
import { SECTION_LABELS, SECTION_ICONS } from '../../types/brief';
import type { BriefSection, SectionType } from '../../types/brief';

const ALL_SECTION_TYPES: SectionType[] = [
  'business_process', 'grain', 'dimension', 'measure', 'relationship', 'notes',
];

interface BriefSidebarProps {
  sections: BriefSection[];
  draftingSections: Set<string>;
  onDraft?: () => void;
  onAddSection?: (type: SectionType) => void;
}

export function BriefSidebar({ sections, draftingSections, onDraft, onAddSection }: BriefSidebarProps) {
  const [showAddMenu, setShowAddMenu] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);

  // Close menu on click outside
  useEffect(() => {
    if (!showAddMenu) return;
    const handler = (e: MouseEvent) => {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setShowAddMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showAddMenu]);

  const scrollToSection = (id: string) => {
    document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth' });
  };

  const existingTypes = new Set(sections.map((s) => s.section_type));
  const addableTypes = ALL_SECTION_TYPES.filter((t) => !existingTypes.has(t));

  return (
    <aside className="brief-sidebar">
      <div className="brief-sidebar-title">章节</div>

      <nav className="brief-sidebar-nav">
        {sections.map((s) => (
          <button
            key={s.id}
            className={`brief-sidebar-item ${s.user_edited ? 'edited' : ''}`}
            onClick={() => scrollToSection(s.id)}
          >
            <span className="brief-sidebar-icon">
              {SECTION_ICONS[s.section_type as SectionType] || '📄'}
            </span>
            <span className="brief-sidebar-label">
              {s.name || SECTION_LABELS[s.section_type as SectionType] || s.section_type}
            </span>
            {s.user_edited && <span className="brief-sidebar-badge">✎</span>}
            {!s.user_edited && s.ai_drafts.length > 0 && (
              <span className="brief-sidebar-badge ai">✦</span>
            )}
          </button>
        ))}

        {/* Drafting shimmer items */}
        {Array.from(draftingSections)
          .filter((t) => !sections.some((s) => s.section_type === t))
          .map((type) => (
            <div key={type} className="brief-sidebar-item shimmer">
              <span className="brief-sidebar-icon">
                {SECTION_ICONS[type as SectionType] || '⏳'}
              </span>
              <span className="brief-sidebar-label">
                {SECTION_LABELS[type as SectionType] || type}
              </span>
            </div>
          ))}
      </nav>

      {/* Add section button */}
      {onAddSection && addableTypes.length > 0 && (
        <div className="brief-sidebar-add-wrapper" ref={addMenuRef}>
          <button
            className="brief-sidebar-add-btn"
            onClick={() => setShowAddMenu(!showAddMenu)}
            aria-label="添加章节"
          >
            + 添加章节
          </button>
          {showAddMenu && (
            <div className="brief-sidebar-add-menu">
              {addableTypes.map((type) => (
                <button
                  key={type}
                  className="brief-sidebar-add-option"
                  onClick={() => {
                    onAddSection(type);
                    setShowAddMenu(false);
                  }}
                >
                  <span>{SECTION_ICONS[type]}</span>
                  <span>{SECTION_LABELS[type]}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {onDraft && (
        <button className="brief-sidebar-draft-btn" onClick={onDraft}>
          ✦ AI 起草
        </button>
      )}
    </aside>
  );
}
