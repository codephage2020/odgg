// AI settings store — fetches/updates LLM config from backend
import { create } from 'zustand';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export interface AiSettings {
  provider: string;
  model: string;
  api_key_set: boolean;
  api_key_hint: string;
  base_url: string;
  timeout: number;
  sources: Record<string, 'env' | 'user'>;
}

export interface AiPreset {
  label: string;
  provider: string;
  model: string;
  base_url: string;
}

export interface TestResult {
  ok: boolean;
  message: string;
  latency_ms?: number;
}

interface AiSettingsStore {
  settings: AiSettings | null;
  presets: AiPreset[];
  loading: boolean;
  saving: boolean;
  testing: boolean;
  testResult: TestResult | null;
  error: string | null;

  fetchSettings: () => Promise<void>;
  fetchPresets: () => Promise<void>;
  updateSettings: (data: {
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
    timeout?: number;
  }) => Promise<void>;
  testConnection: (data: {
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
    timeout?: number;
  }) => Promise<void>;
  resetToDefaults: () => Promise<void>;
  clearError: () => void;
  clearTestResult: () => void;
}

export const useAiSettingsStore = create<AiSettingsStore>()((set) => ({
  settings: null,
  presets: [],
  loading: false,
  saving: false,
  testing: false,
  testResult: null,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/config/ai`);
      if (!resp.ok) throw new Error(`Failed to fetch settings (${resp.status})`);
      const data = await resp.json();
      set({ settings: data, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchPresets: async () => {
    try {
      const resp = await fetch(`${API_BASE}/config/ai/presets`);
      if (!resp.ok) return;
      const data = await resp.json();
      set({ presets: data });
    } catch {
      // Presets are non-critical
    }
  },

  updateSettings: async (data) => {
    set({ saving: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/config/ai`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!resp.ok) throw new Error(`Failed to save settings (${resp.status})`);
      const updated = await resp.json();
      set({ settings: updated, saving: false });
    } catch (e) {
      set({ error: (e as Error).message, saving: false });
    }
  },

  testConnection: async (data) => {
    set({ testing: true, testResult: null, error: null });
    try {
      const resp = await fetch(`${API_BASE}/config/ai/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!resp.ok) throw new Error(`Test request failed (${resp.status})`);
      const result = await resp.json();
      set({ testResult: result, testing: false });
    } catch (e) {
      set({
        testResult: { ok: false, message: (e as Error).message },
        testing: false,
      });
    }
  },

  resetToDefaults: async () => {
    set({ saving: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/config/ai`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`Failed to reset settings (${resp.status})`);
      const data = await resp.json();
      set({ settings: data, saving: false, testResult: null });
    } catch (e) {
      set({ error: (e as Error).message, saving: false });
    }
  },

  clearError: () => set({ error: null }),
  clearTestResult: () => set({ testResult: null }),
}));
