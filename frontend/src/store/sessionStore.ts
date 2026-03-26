// Session state management with Zustand
import { create } from 'zustand';
import type { SessionState, StepState, MetadataSnapshot } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1';

interface SessionStore {
  session: SessionState | null;
  loading: boolean;
  error: string | null;

  // Actions
  createSession: (dbType?: string) => Promise<void>;
  fetchSession: (id: string) => Promise<void>;
  confirmStep: (stepNumber: number, userInput?: Record<string, unknown>) => Promise<void>;
  rollbackToStep: (stepNumber: number) => Promise<void>;
  getSuggestion: (stepNumber: number) => Promise<Record<string, unknown>>;
  discoverMetadata: (connectionUrl: string, schema?: string) => Promise<MetadataSnapshot>;
  generateCode: (mode?: string, includeDbt?: boolean) => Promise<Record<string, unknown>>;
  clearError: () => void;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  session: null,
  loading: false,
  error: null,

  createSession: async (dbType = 'postgresql') => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_db_type: dbType }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      set({ session: data.state, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchSession: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/sessions/${id}`);
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      set({ session: data, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  confirmStep: async (stepNumber: number, userInput?: Record<string, unknown>) => {
    const { session } = get();
    if (!session) return;

    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/sessions/${session.session_id}/steps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_number: stepNumber,
          action: 'confirm',
          user_input: userInput,
          version: session.version,
        }),
      });
      if (!resp.ok) {
        if (resp.status === 409) {
          throw new Error('会话已被修改，请刷新页面');
        }
        throw new Error(await resp.text());
      }
      const data = await resp.json();
      set({ session: data, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  rollbackToStep: async (stepNumber: number) => {
    const { session } = get();
    if (!session) return;

    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/sessions/${session.session_id}/steps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_number: stepNumber,
          action: 'rollback',
          version: session.version,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      set({ session: data, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  getSuggestion: async (stepNumber: number) => {
    const { session } = get();
    if (!session) throw new Error('No session');

    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/modeling/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          step_number: stepNumber,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      set({ loading: false });
      return data;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  discoverMetadata: async (connectionUrl: string, schema = 'public') => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/metadata/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_url: connectionUrl, schema_name: schema }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      set({ loading: false });
      return data;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  generateCode: async (mode = 'full', includeDbt = true) => {
    const { session } = get();
    if (!session) throw new Error('No session');

    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/modeling/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          mode,
          include_dbt: includeDbt,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      set({ loading: false });
      return data;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  clearError: () => set({ error: null }),
}));
