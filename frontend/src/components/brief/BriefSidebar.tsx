// Brief editor sidebar — section navigation + draft trigger
import { SECTION_LABELS, SECTION_ICONS } from '../../types/brief';
import type { BriefSection, SectionType } from '../../types/brief';

interface BriefSidebarProps {
  sections: BriefSection[];
  draftingSections: Set<string>;
  onDraft?: () => void;
}

export function BriefSidebar({ sections, draftingSections, onDraft }: BriefSidebarProps) {
  const scrollToSection = (id: string) => {
    document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth' });
  };

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

      {onDraft && (
        <button className="brief-sidebar-draft-btn" onClick={onDraft}>
          ✦ AI 起草
        </button>
      )}
    </aside>
  );
}
