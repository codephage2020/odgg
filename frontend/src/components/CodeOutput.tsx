// Step 8: Code output display with tabs for DDL/ETL/dbt
import { useState } from 'react';

interface Props {
  ddl: string;
  etl: string;
  dbt: Record<string, string>;
  dataDictionary: string;
  onExecute: () => void;
  loading: boolean;
}

type Tab = 'ddl' | 'etl' | 'dbt' | 'dictionary';

export function CodeOutput({ ddl, etl, dbt, dataDictionary, onExecute, loading }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('ddl');
  const [selectedDbtFile, setSelectedDbtFile] = useState<string>(
    Object.keys(dbt)[0] || ''
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: 'ddl', label: 'DDL' },
    { key: 'etl', label: 'ETL SQL' },
    { key: 'dbt', label: 'dbt Models' },
    { key: 'dictionary', label: '数据字典' },
  ];

  const getContent = () => {
    switch (activeTab) {
      case 'ddl':
        return ddl;
      case 'etl':
        return etl;
      case 'dbt':
        return dbt[selectedDbtFile] || '选择一个 dbt 文件';
      case 'dictionary':
        return dataDictionary;
    }
  };

  return (
    <div className="code-output">
      <div className="code-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? 'tab-active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'dbt' && Object.keys(dbt).length > 0 && (
        <div className="dbt-file-select">
          <select
            value={selectedDbtFile}
            onChange={(e) => setSelectedDbtFile(e.target.value)}
          >
            {Object.keys(dbt).map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>
      )}

      <pre className="code-block">
        <code>{getContent()}</code>
      </pre>

      <div className="code-actions">
        <button className="btn btn-primary" onClick={onExecute} disabled={loading}>
          {loading ? '执行中...' : '一键建表'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => {
            const blob = new Blob([getContent()], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = activeTab === 'dictionary' ? 'data_dictionary.md' : `${activeTab}.sql`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          导出
        </button>
      </div>
    </div>
  );
}
