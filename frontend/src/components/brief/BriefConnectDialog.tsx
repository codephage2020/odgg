// Database connection dialog for Brief Editor
import { useState } from 'react';

interface BriefConnectDialogProps {
  briefId: string;
  onConnected: (snapshot: Record<string, unknown>) => void;
  onClose: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export function BriefConnectDialog({ briefId, onConnected, onClose }: BriefConnectDialogProps) {
  const [host, setHost] = useState(import.meta.env.VITE_DB_HOST || 'localhost');
  const [port, setPort] = useState(import.meta.env.VITE_DB_PORT || '5435');
  const [database, setDatabase] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [schema, setSchema] = useState('public');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleConnect = async () => {
    setLoading(true);
    setError('');
    try {
      const url = `postgresql+asyncpg://${username}:${password}@${host}:${port}/${database}`;
      const resp = await fetch(`${API_BASE}/metadata/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_url: url,
          schema_name: schema,
          brief_id: briefId,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `连接失败 (${resp.status})`);
      }
      const snapshot = await resp.json();
      onConnected(snapshot);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="brief-dialog-overlay" onClick={onClose}>
      <div className="brief-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="brief-dialog-header">
          <h3>连接数据库</h3>
          <button className="brief-dialog-close" onClick={onClose}>×</button>
        </div>

        <div className="brief-connect-form">
          <div className="brief-form-grid">
            <div className="brief-form-group">
              <label>主机</label>
              <input value={host} onChange={(e) => setHost(e.target.value)} />
            </div>
            <div className="brief-form-group">
              <label>端口</label>
              <input value={port} onChange={(e) => setPort(e.target.value)} />
            </div>
            <div className="brief-form-group">
              <label>数据库</label>
              <input
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                placeholder="tpch"
              />
            </div>
            <div className="brief-form-group">
              <label>用户名</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="brief-form-group">
              <label>密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="brief-form-group">
              <label>Schema</label>
              <input value={schema} onChange={(e) => setSchema(e.target.value)} />
            </div>
          </div>

          {error && <div className="brief-connect-error">{error}</div>}

          <div className="brief-connect-actions">
            <button
              className="brief-draft-btn"
              onClick={handleConnect}
              disabled={loading || !database || !username}
            >
              {loading ? '连接中...' : '连接并发现元数据'}
            </button>
            <p className="brief-hint">连接信息仅用于元数据发现，不会持久化存储</p>
          </div>
        </div>
      </div>
    </div>
  );
}
