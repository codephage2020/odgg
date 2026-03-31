import { useState, useMemo } from 'react';

const MAX_AUTO_SELECT = 50;

interface TableInfo {
  name: string;
  row_count?: number | null;
  columns?: { name: string }[];
}

interface TableSelectorProps {
  tables: TableInfo[];
  selectedTables: string[] | null;
  onSelectionChange: (tables: string[]) => void;
}

export default function TableSelector({
  tables,
  selectedTables,
  onSelectionChange,
}: TableSelectorProps) {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState(false);

  // Default: select first MAX_AUTO_SELECT tables if no selection exists
  const selected = useMemo(() => {
    if (selectedTables) return new Set(selectedTables);
    return new Set(tables.slice(0, MAX_AUTO_SELECT).map((t) => t.name));
  }, [selectedTables, tables]);

  const filtered = useMemo(() => {
    if (!search) return tables;
    const q = search.toLowerCase();
    return tables.filter((t) => t.name.toLowerCase().includes(q));
  }, [tables, search]);

  const toggle = (name: string) => {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    onSelectionChange([...next]);
  };

  const selectAll = () => {
    // When filtering, select filtered + keep existing; otherwise select all
    if (search) {
      const next = new Set(selected);
      filtered.forEach((t) => next.add(t.name));
      onSelectionChange([...next]);
    } else {
      onSelectionChange(tables.map((t) => t.name));
    }
  };
  const selectNone = () => {
    if (search) {
      const next = new Set(selected);
      filtered.forEach((t) => next.delete(t.name));
      onSelectionChange([...next]);
    } else {
      onSelectionChange([]);
    }
  };

  if (tables.length <= MAX_AUTO_SELECT && !selectedTables) {
    // Small schema, no need for selection UI
    return null;
  }

  return (
    <div className="table-selector">
      <div
        className="table-selector-header"
        onClick={() => setExpanded(!expanded)}
        role="button"
        aria-expanded={expanded}
        aria-label={`表选择器，${selected.size} / ${tables.length} 张表已选`}
      >
        <span className="table-selector-icon">{expanded ? '▾' : '▸'}</span>
        <span className="table-selector-label">
          📋 {selected.size} / {tables.length} 张表已选
        </span>
        {tables.length > MAX_AUTO_SELECT && !selectedTables && (
          <span className="table-selector-warn">
            ⚠ 大 schema — 已自动选择前 {MAX_AUTO_SELECT} 张表
          </span>
        )}
      </div>

      {expanded && (
        <div className="table-selector-body">
          <div className="table-selector-controls">
            <input
              type="text"
              placeholder="搜索表名..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="table-selector-search"
              aria-label="搜索表名"
            />
            <button onClick={selectAll} className="table-selector-btn" aria-label="全选表">
              {search ? '选中匹配' : '全选'}
            </button>
            <button onClick={selectNone} className="table-selector-btn" aria-label="取消全选">
              {search ? '取消匹配' : '全不选'}
            </button>
          </div>
          <div className="table-selector-list">
            {filtered.map((t) => (
              <label key={t.name} className="table-selector-item">
                <input
                  type="checkbox"
                  checked={selected.has(t.name)}
                  onChange={() => toggle(t.name)}
                />
                <span className="table-selector-name">{t.name}</span>
                {t.row_count != null && (
                  <span className="table-selector-rows">
                    ~{t.row_count.toLocaleString()} rows
                  </span>
                )}
                {t.columns && (
                  <span className="table-selector-cols">
                    {t.columns.length} cols
                  </span>
                )}
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
