// Step 8: Code output display with tabs for DDL/ETL/dbt/Dictionary
import { useState } from 'react';

interface Props {
  ddl: string;
  etl: string;
  dbt: Record<string, string>;
  dataDictionary: string;
  loading: boolean;
}

type Tab = 'ddl' | 'etl' | 'dbt' | 'dictionary';

export function CodeOutput({ ddl, etl, dbt, dataDictionary, loading }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('ddl');
  const [selectedDbtFile, setSelectedDbtFile] = useState<string>(
    Object.keys(dbt)[0] || ''
  );
  const [copied, setCopied] = useState(false);

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: 'ddl', label: 'DDL' },
    { key: 'etl', label: 'ETL SQL' },
    { key: 'dbt', label: 'dbt Models', count: Object.keys(dbt).length },
    { key: 'dictionary', label: '数据字典' },
  ];

  const getContent = () => {
    switch (activeTab) {
      case 'ddl': return ddl;
      case 'etl': return etl;
      case 'dbt': return dbt[selectedDbtFile] || '选择一个 dbt 文件';
      case 'dictionary': return dataDictionary;
    }
  };

  const getFilename = () => {
    switch (activeTab) {
      case 'ddl': return 'schema.sql';
      case 'etl': return 'etl.sql';
      case 'dbt': return selectedDbtFile || 'dbt_model.sql';
      case 'dictionary': return 'data_dictionary.md';
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(getContent());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([getContent()], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = getFilename();
    a.click();
    URL.revokeObjectURL(url);
  };

  const content = getContent();

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
            {tab.count != null && <span className="tab-count">{tab.count}</span>}
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
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      )}

      <div className="code-block-wrapper">
        <div className="code-block-toolbar">
          <span className="code-filename">{getFilename()}</span>
          <div className="code-block-actions">
            <button className="btn btn-sm" onClick={handleCopy} disabled={loading || !content}>
              {copied ? '已复制' : '复制'}
            </button>
            <button className="btn btn-sm" onClick={handleDownload} disabled={loading || !content}>
              下载
            </button>
          </div>
        </div>
        <pre className="code-block">
          <code>{content || '(空)'}</code>
        </pre>
      </div>

      <div className="code-stats">
        <span>{content?.split('\n').length || 0} 行</span>
        <span>{content?.length || 0} 字符</span>
      </div>
    </div>
  );
}
