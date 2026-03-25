// Database info panel in sidebar
import type { MetadataSnapshot } from '../types';

interface Props {
  metadata: MetadataSnapshot | null;
}

export function DBInfoPanel({ metadata }: Props) {
  if (!metadata) {
    return (
      <div className="db-info-panel">
        <h3>数据源</h3>
        <p className="empty-text">未连接</p>
      </div>
    );
  }

  const fkCount = metadata.relationships.filter((r) => !r.is_inferred).length;
  const inferredCount = metadata.relationships.filter((r) => r.is_inferred).length;
  const totalRows = metadata.tables.reduce(
    (sum, t) => sum + (t.row_count || 0),
    0
  );

  return (
    <div className="db-info-panel">
      <h3>数据源</h3>
      <div className="db-info-item">
        <span className="label">数据库</span>
        <span className="value">{metadata.database_name}</span>
      </div>
      <div className="db-info-item">
        <span className="label">类型</span>
        <span className="value">{metadata.database_type}</span>
      </div>
      <div className="db-info-item">
        <span className="label">表数量</span>
        <span className="value">{metadata.tables.length}</span>
      </div>
      <div className="db-info-item">
        <span className="label">外键关系</span>
        <span className="value">{fkCount}</span>
      </div>
      {inferredCount > 0 && (
        <div className="db-info-item">
          <span className="label">推断关系</span>
          <span className="value inferred">{inferredCount}</span>
        </div>
      )}
      <div className="db-info-item">
        <span className="label">总行数</span>
        <span className="value">~{totalRows.toLocaleString()}</span>
      </div>
    </div>
  );
}
