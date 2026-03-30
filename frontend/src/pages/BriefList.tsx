// ODGG — Brief list / home page
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBriefStore } from '../store/briefStore';
import { ThemeToggle } from '../components/ThemeToggle';
import './BriefList.css';

export function BriefList() {
  const navigate = useNavigate();
  const { briefs, loading, error, listBriefs, createBrief, deleteBrief, clearError } =
    useBriefStore();
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listBriefs();
  }, [listBriefs]);

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

        <div className="brief-list-grid">
          {briefs.map((brief) => (
            <div
              key={brief.id}
              className="brief-list-card"
              onClick={() => navigate(`/brief/${brief.id}`)}
            >
              <h3>{brief.title}</h3>
              <div className="brief-card-meta">
                <span className="brief-card-status">{brief.status}</span>
                {brief.database_name && (
                  <span className="brief-card-db">{brief.database_name}</span>
                )}
                <span className="brief-card-sections">
                  {brief.section_count} 章节
                </span>
              </div>
              <div className="brief-card-date">
                {new Date(brief.created_at).toLocaleDateString('zh-CN')}
              </div>
              <button
                className="brief-card-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('确定删除这个 Brief？')) {
                    deleteBrief(brief.id);
                  }
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
