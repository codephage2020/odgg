// ODGG — Modeling Brief Editor (document-centric mode)
import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBriefStore } from '../store/briefStore';
import { BriefSidebar } from '../components/brief/BriefSidebar';
import { BriefSectionCard } from '../components/brief/BriefSectionCard';
import { BriefShimmer } from '../components/brief/BriefShimmer';
import { BriefConnectDialog } from '../components/brief/BriefConnectDialog';
import TableSelector from '../components/brief/TableSelector';
import { ThemeToggle } from '../components/ThemeToggle';
import { CodeBlock } from '../components/CodeBlock';
import { SECTION_LABELS, SECTION_ICONS } from '../types/brief';
import type { SectionType } from '../types/brief';
import './BriefEditor.css';

/** Trigger a file download in the browser. */
function downloadFile(content: string, filename: string, mime = 'text/plain') {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

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
    createSection,
    draftSections,
    generateCode,
    exportBrief,
    clearError,
  } = useBriefStore();

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [showConnect, setShowConnect] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<Record<string, string> | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [showStatusMenu, setShowStatusMenu] = useState(false);
  const [confirmRedraftAll, setConfirmRedraftAll] = useState(false);
  const statusRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (briefId) {
      fetchBrief(briefId);
    }
  }, [briefId, fetchBrief]);

  // Auto-dismiss error after 5 seconds
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(clearError, 5000);
    return () => clearTimeout(timer);
  }, [error, clearError]);

  // Close status menu on click outside or Escape
  useEffect(() => {
    if (!showStatusMenu) return;
    const handleClick = (e: MouseEvent) => {
      if (statusRef.current && !statusRef.current.contains(e.target as Node)) {
        setShowStatusMenu(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowStatusMenu(false);
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [showStatusMenu]);

  const handleTitleSave = useCallback(async () => {
    if (!titleDraft.trim()) {
      // Restore original title if empty
      if (currentBrief) setTitleDraft(currentBrief.title);
      setEditingTitle(false);
      return;
    }
    if (currentBrief && titleDraft.trim() !== currentBrief.title) {
      await updateBrief(currentBrief.id, { title: titleDraft.trim() });
    }
    setEditingTitle(false);
  }, [currentBrief, titleDraft, updateBrief]);

  const handleAddSection = useCallback(async (type: SectionType) => {
    if (!currentBrief) return;
    await createSection(currentBrief.id, {
      section_type: type,
      content: '',
    });
  }, [currentBrief, createSection]);

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
    // Validate required sections before calling API
    const types = new Set(currentBrief.sections.map((s) => s.section_type));
    const missing: string[] = [];
    if (!types.has('business_process')) missing.push('业务过程');
    if (!types.has('measure')) missing.push('度量');
    if (missing.length > 0) {
      useBriefStore.setState({ error: `需要以下章节才能生成代码：${missing.join('、')}` });
      return;
    }
    try {
      const code = await generateCode(currentBrief.id);
      setGeneratedCode(code);
      // Scroll to code output after generation
      setTimeout(() => {
        document.querySelector('.brief-code-output')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch {
      // Error displayed via store
    }
  }, [currentBrief, generateCode]);

  const handleStatusChange = useCallback(async (status: string) => {
    if (currentBrief) {
      await updateBrief(currentBrief.id, { status });
    }
    setShowStatusMenu(false);
  }, [currentBrief, updateBrief]);

  const handleExport = useCallback(async () => {
    if (!currentBrief) return;
    try {
      const md = await exportBrief(currentBrief.id);
      const filename = `${currentBrief.title.replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]/g, '_')}.md`;
      downloadFile(md, filename, 'text/markdown');
    } catch {
      // Error handled in store
    }
  }, [currentBrief, exportBrief]);

  const handleCopyCode = useCallback(async (key: string, code: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }, []);

  const handleDownloadCode = useCallback((key: string, code: string) => {
    const ext = key === 'dbt_model' ? '.sql' : key === 'dbt_schema' ? '.yml' : '.sql';
    downloadFile(code, `${key}${ext}`);
  }, []);

  // Global keyboard shortcuts: Cmd+E to export
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault();
        handleExport();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [handleExport]);

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
          <div className="brief-status-wrapper" ref={statusRef}>
            <button
              className={`brief-status-badge clickable status-${currentBrief.status}`}
              onClick={() => setShowStatusMenu(!showStatusMenu)}
            >
              {currentBrief.status === 'draft' && '📝 草稿'}
              {currentBrief.status === 'review' && '👀 评审中'}
              {currentBrief.status === 'approved' && '✅ 已批准'}
              {currentBrief.status === 'exported' && '📤 已导出'}
            </button>
            {showStatusMenu && (
              <div className="brief-status-menu">
                {(['draft', 'review', 'approved', 'exported'] as const).map((s) => (
                  <button
                    key={s}
                    className={`brief-status-option ${s === currentBrief.status ? 'active' : ''}`}
                    onClick={() => handleStatusChange(s)}
                  >
                    {s === 'draft' && '📝 草稿'}
                    {s === 'review' && '👀 评审中'}
                    {s === 'approved' && '✅ 已批准'}
                    {s === 'exported' && '📤 已导出'}
                  </button>
                ))}
              </div>
            )}
          </div>
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
        {hasSections && !drafting && (
          <>
            <button
              className="brief-header-btn"
              onClick={() => setConfirmRedraftAll(true)}
              disabled={loading}
              aria-label="重新起草所有章节"
            >
              ✦ 重新起草
            </button>
            <button className="brief-header-btn" onClick={handleExport} disabled={loading} aria-label="导出 Markdown">
              📄 导出
            </button>
            <button className="brief-header-btn" onClick={handleGenerate} disabled={loading} aria-label="生成代码">
              {loading ? '生成中...' : '⚡ 生成代码'}
            </button>
          </>
        )}

        <button className="brief-header-icon-btn" onClick={() => navigate('/settings')} aria-label="AI 设置" title="AI 设置">
          ⚙
        </button>
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
          onAddSection={hasMetadata ? handleAddSection : undefined}
        />

        {/* Document */}
        <main className="brief-document">
          {/* Empty state: no metadata */}
          {!hasMetadata && !hasSections && (
            <div className="brief-empty-doc">
              <div className="brief-empty-icon">🗄</div>
              <h2>连接数据库开始建模</h2>
              <p>连接你的 PostgreSQL 数据库，AI 将自动分析表结构并生成 Kimball 维度模型（业务过程、粒度、维度、度量）。</p>
              <button
                className="brief-draft-btn"
                onClick={() => setShowConnect(true)}
              >
                🔌 连接数据库
              </button>
            </div>
          )}

          {/* Table selection for large schemas */}
          {hasMetadata && (
            <TableSelector
              tables={
                ((currentBrief.metadata_snapshot as Record<string, unknown>)
                  ?.tables as { name: string; row_count?: number; columns?: { name: string }[] }[]) || []
              }
              selectedTables={currentBrief.selected_tables ?? null}
              onSelectionChange={(tables) => {
                if (briefId) updateBrief(briefId, { selected_tables: tables });
              }}
            />
          )}

          {/* Empty state: has metadata but no sections */}
          {hasMetadata && !hasSections && !drafting && (
            <div className="brief-empty-doc">
              <div className="brief-empty-icon">✦</div>
              <h2>元数据已就绪</h2>
              <p>
                发现了{' '}
                {(currentBrief.metadata_snapshot as Record<string, unknown[]>)?.tables?.length || '?'}{' '}
                张表。AI 将依次分析业务过程 → 粒度 → 维度 → 度量，约需 1-2 分钟。
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
                <h3 className="brief-section-title">
                  生成的代码
                  <span className="brief-code-count">
                    {Object.keys(generatedCode).length} 个文件
                  </span>
                </h3>
                <div className="brief-code-global-actions">
                  <button
                    className="brief-action-btn"
                    onClick={() => {
                      const allCode = Object.entries(generatedCode)
                        .map(([k, v]) => `-- ${k.toUpperCase()}\n${typeof v === 'string' ? v : JSON.stringify(v, null, 2)}`)
                        .join('\n\n');
                      downloadFile(allCode, 'generated_code.sql');
                    }}
                    title="下载全部"
                  >
                    ⬇ 下载全部
                  </button>
                  <button
                    className="brief-action-btn"
                    onClick={() => setGeneratedCode(null)}
                  >
                    ✕ 关闭
                  </button>
                </div>
              </div>
              {Object.entries(generatedCode).map(([key, value]) => {
                const code = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
                const CODE_LABELS: Record<string, string> = {
                  ddl: 'DDL — 建表语句',
                  etl: 'ETL — 数据加载',
                  data_dictionary: '数据字典',
                };
                const label = CODE_LABELS[key] || key;
                const lang = key === 'data_dictionary' ? 'yaml' : key.endsWith('.yml') || key.endsWith('.yaml') ? 'yaml' : 'sql';
                return (
                  <div key={key} className="brief-code-block">
                    <div className="brief-code-block-header">
                      <div className="brief-code-label">{label}</div>
                      <div className="brief-code-block-actions">
                        <button
                          className="brief-code-btn"
                          onClick={() => handleCopyCode(key, code)}
                          title="复制"
                        >
                          {copiedKey === key ? '✓ 已复制' : '📋 复制'}
                        </button>
                        <button
                          className="brief-code-btn"
                          onClick={() => handleDownloadCode(key, code)}
                          title="下载"
                        >
                          ⬇ 下载
                        </button>
                      </div>
                    </div>
                    <CodeBlock code={code} language={lang} />
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* Re-draft all confirmation */}
      {confirmRedraftAll && (
        <div className="brief-dialog-overlay" onClick={() => setConfirmRedraftAll(false)}>
          <div className="brief-delete-dialog" onClick={(e) => e.stopPropagation()}>
            <p>重新起草将覆盖现有 {sections.length} 个章节内容，此操作不可撤销。确定继续？</p>
            <div className="brief-delete-actions">
              <button
                className="brief-delete-confirm"
                onClick={() => {
                  setConfirmRedraftAll(false);
                  handleDraft();
                }}
              >
                确定重新起草
              </button>
              <button className="brief-delete-cancel" onClick={() => setConfirmRedraftAll(false)}>
                取消
              </button>
            </div>
          </div>
        </div>
      )}

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
