// Datasource CRUD panel — save/load database connections
import { useState } from 'react';
import { useDatasourceStore } from '../store/datasourceStore';
import type { SavedDatasource } from '../types/datasource';

interface Props {
  onConnect: (url: string, schema: string) => void;
  loading: boolean;
}

export function DatasourceManager({ onConnect, loading }: Props) {
  const { datasources, activeId, addDatasource, removeDatasource, setActive, buildConnectionUrl } =
    useDatasourceStore();
  const [showForm, setShowForm] = useState(false);
  const [password, setPassword] = useState('');
  const [form, setForm] = useState({
    name: '',
    host: import.meta.env.VITE_DB_HOST || 'localhost',
    port: import.meta.env.VITE_DB_PORT || '5435',
    database: '',
    username: '',
    schema: 'public',
    dbType: 'postgresql',
  });

  const handleSaveAndConnect = () => {
    const ds = addDatasource(form);
    setActive(ds.id);
    const url = buildConnectionUrl(ds.id, password);
    onConnect(url, form.schema);
    setShowForm(false);
    setPassword('');
    setForm({ ...form, name: '', database: '', username: '' });
  };

  const handleConnect = (ds: SavedDatasource) => {
    if (!password) return;
    setActive(ds.id);
    const url = buildConnectionUrl(ds.id, password);
    onConnect(url, ds.schema);
  };

  return (
    <div className="ds-manager">
      <div className="ds-header">
        <span className="ds-title">数据源</span>
        <button className="btn btn-sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? '取消' : '+'}
        </button>
      </div>

      {showForm && (
        <div className="ds-form">
          <input
            placeholder="连接名称"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            aria-label="连接名称"
          />
          <div className="ds-form-row">
            <input
              placeholder="主机"
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
              aria-label="主机"
            />
            <input
              placeholder="端口"
              value={form.port}
              onChange={(e) => setForm({ ...form, port: e.target.value })}
              style={{ width: 70 }}
              aria-label="端口"
            />
          </div>
          <input
            placeholder="数据库"
            value={form.database}
            onChange={(e) => setForm({ ...form, database: e.target.value })}
            aria-label="数据库"
          />
          <input
            placeholder="用户名"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            aria-label="用户名"
          />
          <input
            type="password"
            placeholder="密码（不保存）"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-label="密码"
          />
          <input
            placeholder="Schema"
            value={form.schema}
            onChange={(e) => setForm({ ...form, schema: e.target.value })}
            aria-label="Schema"
          />
          <button
            className="btn btn-primary btn-sm ds-connect-btn"
            onClick={handleSaveAndConnect}
            disabled={loading || !form.database || !form.username || !form.name}
          >
            {loading ? '连接中...' : '保存并连接'}
          </button>
        </div>
      )}

      <div className="ds-list">
        {datasources.length === 0 && !showForm && (
          <p className="ds-empty">点击 + 添加数据源</p>
        )}
        {datasources.map((ds) => (
          <div
            key={ds.id}
            className={`ds-item ${ds.id === activeId ? 'ds-active' : ''}`}
          >
            <div className="ds-item-info" onClick={() => setActive(ds.id)}>
              <span className="ds-item-name">{ds.name}</span>
              <span className="ds-item-meta">
                {ds.host}:{ds.port}/{ds.database}
              </span>
            </div>
            <div className="ds-item-actions">
              {ds.id !== activeId && (
                <>
                  <input
                    type="password"
                    placeholder="密码"
                    className="ds-pw-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleConnect(ds)}
                    aria-label={`${ds.name} 密码`}
                  />
                  <button
                    className="btn btn-sm"
                    onClick={() => handleConnect(ds)}
                    disabled={loading || !password}
                  >
                    连接
                  </button>
                </>
              )}
              {ds.id === activeId && (
                <span className="ds-connected-badge">已连接</span>
              )}
              <button
                className="btn btn-sm ds-delete"
                onClick={() => removeDatasource(ds.id)}
                title="删除"
                aria-label={`删除 ${ds.name}`}
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
