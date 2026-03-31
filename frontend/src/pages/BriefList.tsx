// ODGG — Brief list / home page
import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBriefStore } from '../store/briefStore';
import { ThemeToggle } from '../components/ThemeToggle';
import './BriefList.css';

const STATUS_LABELS: Record<string, string> = {
  draft: '📝 草稿',
  review: '👀 评审中',
  approved: '✅ 已批准',
  exported: '📤 已导出',
};

type SortKey = 'updated' | 'title' | 'status';

export function BriefList() {
  const navigate = useNavigate();
  const { briefs, loading, error, listBriefs, createBrief, deleteBrief, clearError } =
    useBriefStore();
  const [creating, setCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<SortKey>('updated');

  const filtered = useMemo(() => {
    let list = briefs;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((b) =>
        b.title.toLowerCase().includes(q) ||
        (b.database_name && b.database_name.toLowerCase().includes(q))
      );
    }
    if (statusFilter !== 'all') {
      list = list.filter((b) => b.status === statusFilter);
    }
    const sorted = [...list];
    switch (sortBy) {
      case 'title':
        sorted.sort((a, b) => a.title.localeCompare(b.title));
        break;
      case 'status':
        sorted.sort((a, b) => a.status.localeCompare(b.status));
        break;
      case 'updated':
      default:
        sorted.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
        break;
    }
    return sorted;
  }, [briefs, search, statusFilter, sortBy]);

  useEffect(() => {
    listBriefs();
  }, [listBriefs]);

  // Auto-dismiss error after 5 seconds
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(clearError, 5000);
    return () => clearTimeout(timer);
  }, [error, clearError]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const brief = await createBrief();
      navigate(`/brief/${brief.id}`);
    } catch {
      // Error handled in store
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="brief-list-page">
      <header className="brief-list-header">
        <h1>ODGG</h1>
        <span className="wb-subtitle">Modeling Brief Editor</span>
        <div className="brief-header-spacer" />
        <button className="brief-nav-link" onClick={() => navigate('/settings')}>
          ⚙ AI 设置
        </button>
        <button className="brief-nav-link" onClick={() => navigate('/wizard')}>
          打开向导 →
        </button>
        <ThemeToggle />
      </header>

      <main className="brief-list-main">
        <div className="brief-list-toolbar">
          <h2>我的 Briefs</h2>
          <button
            className="brief-create-btn"
            onClick={handleCreate}
            disabled={creating}
          >
            {creating ? '创建中...' : '+ 新建 Brief'}
          </button>
        </div>

        {briefs.length > 0 && (
          <div className="brief-list-filters">
            <input
              type="text"
              placeholder="搜索标题或数据库..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="brief-search-input"
              aria-label="搜索 Briefs"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="brief-filter-select"
              aria-label="按状态筛选"
            >
              <option value="all">全部状态</option>
              <option value="draft">草稿</option>
              <option value="review">评审中</option>
              <option value="approved">已批准</option>
              <option value="exported">已导出</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="brief-filter-select"
              aria-label="排序"
            >
              <option value="updated">最近更新</option>
              <option value="title">按标题</option>
              <option value="status">按状态</option>
            </select>
          </div>
        )}

        {error && (
          <div className="wb-error brief-list-error">
            <span>{error}</span>
            <button onClick={clearError}>×</button>
          </div>
        )}

        {loading && briefs.length === 0 && (
          <div className="brief-list-loading">
            <div className="spinner" />
            <p>加载中...</p>
          </div>
        )}

        {!loading && briefs.length === 0 && (
          <div className="brief-list-empty">
            <p>还没有 Briefs。点击上方按钮创建第一个。</p>
          </div>
        )}

        {briefs.length > 0 && filtered.length === 0 && (
          <div className="brief-list-empty">
            <p>没有匹配的 Briefs。</p>
          </div>
        )}

        <div className="brief-list-grid">
          {filtered.map((brief) => (
            <div
              key={brief.id}
              className="brief-list-card"
              onClick={() => navigate(`/brief/${brief.id}`)}
            >
              <h3>{brief.title}</h3>
              <div className="brief-card-meta">
                <span className={`brief-card-status status-${brief.status}`}>
                  {STATUS_LABELS[brief.status] || brief.status}
                </span>
                {brief.database_name && (
                  <span className="brief-card-db">{brief.database_name}</span>
                )}
                <span className="brief-card-sections">
                  {brief.section_count} 章节
                </span>
              </div>
              <div className="brief-card-date">
                更新于 {new Date(brief.updated_at).toLocaleDateString('zh-CN')}
              </div>
              <button
                className="brief-card-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  setDeleteTarget(brief.id);
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>

        {/* Delete confirmation dialog */}
        {deleteTarget && (
          <div className="brief-dialog-overlay" onClick={() => setDeleteTarget(null)}>
            <div className="brief-delete-dialog" onClick={(e) => e.stopPropagation()}>
              <p>确定删除这个 Brief？此操作不可撤销。</p>
              <div className="brief-delete-actions">
                <button
                  className="brief-delete-confirm"
                  onClick={() => {
                    deleteBrief(deleteTarget);
                    setDeleteTarget(null);
                  }}
                >
                  删除
                </button>
                <button
                  className="brief-delete-cancel"
                  onClick={() => setDeleteTarget(null)}
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
