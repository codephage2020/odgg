// Step 1: Database connection form
import { useState } from 'react';

interface Props {
  onConnect: (url: string, schema: string) => void;
  loading: boolean;
}

export function ConnectStep({ onConnect, loading }: Props) {
  const [host, setHost] = useState('localhost');
  const [port, setPort] = useState('5432');
  const [database, setDatabase] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [schema, setSchema] = useState('public');

  const handleConnect = () => {
    const url = `postgresql+asyncpg://${username}:${password}@${host}:${port}/${database}`;
    onConnect(url, schema);
  };

  return (
    <div className="connect-step">
      <div className="form-grid">
        <div className="form-group">
          <label>主机</label>
          <input value={host} onChange={(e) => setHost(e.target.value)} />
        </div>
        <div className="form-group">
          <label>端口</label>
          <input value={port} onChange={(e) => setPort(e.target.value)} />
        </div>
        <div className="form-group">
          <label>数据库</label>
          <input
            value={database}
            onChange={(e) => setDatabase(e.target.value)}
            placeholder="tpch"
          />
        </div>
        <div className="form-group">
          <label>用户名</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="form-group">
          <label>密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Schema</label>
          <input value={schema} onChange={(e) => setSchema(e.target.value)} />
        </div>
      </div>

      <div className="connect-actions">
        <button
          className="btn btn-primary"
          onClick={handleConnect}
          disabled={loading || !database || !username}
        >
          {loading ? '连接中...' : '连接数据库'}
        </button>
        <p className="connect-hint">
          连接信息仅用于元数据发现，不会持久化存储
        </p>
      </div>
    </div>
  );
}
