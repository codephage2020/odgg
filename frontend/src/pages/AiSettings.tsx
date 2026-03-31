// ODGG — AI Settings page for LLM configuration
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAiSettingsStore } from '../store/aiSettingsStore';
import type { AiPreset } from '../store/aiSettingsStore';
import { ThemeToggle } from '../components/ThemeToggle';
import './AiSettings.css';

export function AiSettings() {
  const navigate = useNavigate();
  const {
    settings,
    presets,
    loading,
    saving,
    testing,
    testResult,
    error,
    fetchSettings,
    fetchPresets,
    updateSettings,
    testConnection,
    resetToDefaults,
    clearError,
    clearTestResult,
  } = useAiSettingsStore();

  // Local form state (editable before save)
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [timeout, setTimeout_] = useState(120);
  const [showKey, setShowKey] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Load settings and presets on mount
  useEffect(() => {
    fetchSettings();
    fetchPresets();
  }, [fetchSettings, fetchPresets]);

  // Sync local form state when settings load from API
  const syncFormFromSettings = useCallback((s: typeof settings) => {
    if (!s) return;
    setProvider(s.provider);
    setModel(s.model);
    setBaseUrl(s.base_url);
    setTimeout_(s.timeout);
    setApiKey('');
    setDirty(false);
  }, []);

  useEffect(() => {
    syncFormFromSettings(settings); // eslint-disable-line react-hooks/set-state-in-effect -- sync form from API response
  }, [settings, syncFormFromSettings]);

  const markDirty = useCallback(() => setDirty(true), []);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const handlePreset = useCallback(
    (preset: AiPreset) => {
      setProvider(preset.provider);
      setModel(preset.model);
      setBaseUrl(preset.base_url);
      setDirty(true);
      clearTestResult();
    },
    [clearTestResult]
  );

  const handleSave = useCallback(async () => {
    const data: Record<string, string | number> = {
      provider,
      model,
      base_url: baseUrl,
      timeout,
    };
    // Only send api_key when user explicitly typed one
    if (apiKey) {
      data.api_key = apiKey;
    }
    await updateSettings(data);
    setApiKey('');
    setDirty(false);
  }, [provider, model, apiKey, baseUrl, timeout, updateSettings]);

  const handleTest = useCallback(async () => {
    const data: Record<string, string | number> = {
      provider,
      model,
      base_url: baseUrl,
      timeout,
    };
    if (apiKey) {
      data.api_key = apiKey;
    }
    await testConnection(data);
  }, [provider, model, apiKey, baseUrl, timeout, testConnection]);

  const handleReset = useCallback(async () => {
    if (confirm('确定恢复默认设置？将使用环境变量中的配置。')) {
      await resetToDefaults();
    }
  }, [resetToDefaults]);

  const sourceLabel = (field: string) => {
    if (!settings?.sources) return null;
    const src = settings.sources[field];
    if (src === 'user') return <span className="ai-source-badge user">自定义</span>;
    return <span className="ai-source-badge env">环境变量</span>;
  };

  if (loading && !settings) {
    return (
      <div className="ai-settings-page">
        <header className="ai-settings-header">
          <button className="brief-back" onClick={() => navigate('/brief')}>
            ← 返回
          </button>
          <h1>AI 设置</h1>
          <div className="brief-header-spacer" />
          <ThemeToggle />
        </header>
        <main className="ai-settings-main">
          <div className="ai-settings-loading">
            <div className="spinner" />
            <p>加载设置...</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="ai-settings-page">
      <header className="ai-settings-header">
        <button className="brief-back" onClick={() => navigate('/brief')}>
          ← 返回
        </button>
        <h1>AI 设置</h1>
        <div className="brief-header-spacer" />
        <ThemeToggle />
      </header>

      <main className="ai-settings-main">
        {error && (
          <div className="wb-error ai-settings-error">
            <span>{error}</span>
            <button onClick={clearError}>×</button>
          </div>
        )}

        {/* Current model summary */}
        {settings && (
          <div className="ai-settings-summary">
            当前模型：
            <strong>
              {settings.provider}/{settings.model}
            </strong>
            {settings.api_key_set && (
              <span className="ai-key-badge">🔑 {settings.api_key_hint}</span>
            )}
          </div>
        )}

        {/* Presets */}
        <section className="ai-settings-section">
          <h2>预设方案</h2>
          <div className="ai-presets-grid">
            {presets.map((preset) => (
              <button
                key={preset.label}
                className={`ai-preset-card ${
                  preset.provider === provider && preset.model === model
                    ? 'active'
                    : ''
                }`}
                onClick={() => handlePreset(preset)}
              >
                <span className="ai-preset-label">{preset.label}</span>
                <span className="ai-preset-detail">
                  {preset.provider}/{preset.model}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* Configuration form */}
        <section className="ai-settings-section">
          <h2>模型配置</h2>
          <div className="ai-settings-form">
            <div className="ai-field">
              <label>
                Provider {sourceLabel('provider')}
              </label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  markDirty();
                }}
              >
                <option value="openai">openai</option>
                <option value="anthropic">anthropic</option>
                <option value="ollama">ollama</option>
              </select>
            </div>

            <div className="ai-field">
              <label>
                Model {sourceLabel('model')}
              </label>
              <input
                type="text"
                value={model}
                onChange={(e) => {
                  setModel(e.target.value);
                  markDirty();
                }}
                placeholder="gpt-4o"
              />
            </div>

            <div className="ai-field">
              <label>
                Base URL {sourceLabel('base_url')}
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => {
                  setBaseUrl(e.target.value);
                  markDirty();
                }}
                placeholder="留空使用默认值"
              />
              <span className="ai-field-hint">
                Ollama: http://localhost:11434 | DeepSeek: https://api.deepseek.com
              </span>
            </div>

            <div className="ai-field">
              <label>
                API Key {sourceLabel('api_key')}
              </label>
              <div className="ai-key-input-group">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    markDirty();
                  }}
                  placeholder={
                    settings?.api_key_set
                      ? `已设置 (${settings.api_key_hint})`
                      : '输入 API Key'
                  }
                />
                <button
                  className="ai-key-toggle"
                  onClick={() => setShowKey(!showKey)}
                  type="button"
                >
                  {showKey ? '🙈' : '👁'}
                </button>
              </div>
              <span className="ai-field-hint">
                留空保持现有 Key 不变
              </span>
            </div>

            <div className="ai-field">
              <label>
                Timeout (秒) {sourceLabel('timeout')}
              </label>
              <input
                type="number"
                value={timeout}
                onChange={(e) => {
                  setTimeout_(parseInt(e.target.value) || 30);
                  markDirty();
                }}
                min={10}
                max={600}
              />
            </div>
          </div>
        </section>

        {/* Test result */}
        {testResult && (
          <div
            className={`ai-test-result ${testResult.ok ? 'success' : 'failure'}`}
          >
            <span className="ai-test-icon">
              {testResult.ok ? '✅' : '❌'}
            </span>
            <span className="ai-test-message">{testResult.message}</span>
            {testResult.latency_ms != null && (
              <span className="ai-test-latency">{testResult.latency_ms}ms</span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <section className="ai-settings-actions">
          <button
            className="ai-action-btn test"
            onClick={handleTest}
            disabled={testing || !model}
          >
            {testing ? '测试中...' : '🔌 测试连接'}
          </button>
          <button
            className="ai-action-btn save"
            onClick={handleSave}
            disabled={saving || !dirty}
          >
            {saving ? '保存中...' : '💾 保存设置'}
          </button>
          <button
            className="ai-action-btn reset"
            onClick={handleReset}
            disabled={saving}
          >
            🔄 恢复默认
          </button>
        </section>
      </main>
    </div>
  );
}
