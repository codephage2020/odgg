// Brief editor state management with Zustand
import { create } from 'zustand';
import type { Brief, BriefListItem, BriefSection } from '../types/brief';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

async function parseApiError(resp: Response): Promise<string> {
  const text = await resp.text();
  try {
    const json = JSON.parse(text);
    return json.detail || json.message || json.error || text;
  } catch {
    return text || `请求失败 (${resp.status})`;
  }
}

// SSE event callback types
export interface DraftCallbacks {
  onDrafting?: (section: string) => void;
  onSectionReady?: (section: string, data: BriefSection) => void;
  onDone?: (count: number) => void;
  onError?: (error: string) => void;
}

interface BriefState {
  // Data
  briefs: BriefListItem[];
  currentBrief: Brief | null;

  // UI state
  loading: boolean;
  drafting: boolean;
  draftingSection: string | null;
  error: string | null;

  // Actions
  listBriefs: () => Promise<void>;
  createBrief: (title?: string, dbName?: string, snapshot?: Record<string, unknown>) => Promise<Brief>;
  fetchBrief: (id: string) => Promise<void>;
  updateBrief: (id: string, data: { title?: string; status?: string; selected_tables?: string[] }) => Promise<void>;
  deleteBrief: (id: string) => Promise<void>;

  // Section actions
  createSection: (briefId: string, data: Partial<BriefSection> & { section_type: string }) => Promise<BriefSection>;
  updateSection: (briefId: string, sectionId: string, data: Partial<BriefSection>) => Promise<void>;
  deleteSection: (briefId: string, sectionId: string) => Promise<void>;
  regenerateSection: (briefId: string, sectionId: string) => Promise<void>;

  // Cascade drafting
  draftSections: (briefId: string, callbacks?: DraftCallbacks) => Promise<void>;
  draftSectionsSync: (briefId: string) => Promise<void>;

  // Code generation
  generateCode: (briefId: string) => Promise<Record<string, string>>;

  // Export
  exportBrief: (briefId: string) => Promise<string>;

  // Utility
  clearError: () => void;
}

export const useBriefStore = create<BriefState>((set, get) => ({
  briefs: [],
  currentBrief: null,
  loading: false,
  drafting: false,
  draftingSection: null,
  error: null,

  clearError: () => set({ error: null }),

  // --- Brief CRUD ---

  listBriefs: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/briefs`);
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const data: BriefListItem[] = await resp.json();
      set({ briefs: data, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  createBrief: async (title = 'Untitled Brief', dbName = '', snapshot) => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/briefs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          database_name: dbName,
          metadata_snapshot: snapshot,
        }),
      });
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const brief: Brief = await resp.json();
      set({ currentBrief: brief, loading: false });
      return brief;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  fetchBrief: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/briefs/${id}`);
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const brief: Brief = await resp.json();
      set({ currentBrief: brief, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  updateBrief: async (id: string, data) => {
    try {
      const resp = await fetch(`${API_BASE}/briefs/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const brief: Brief = await resp.json();
      set({ currentBrief: brief });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  deleteBrief: async (id: string) => {
    try {
      const resp = await fetch(`${API_BASE}/briefs/${id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(await parseApiError(resp));
      set((state) => ({
        briefs: state.briefs.filter((b) => b.id !== id),
        currentBrief: state.currentBrief?.id === id ? null : state.currentBrief,
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  // --- Section CRUD ---

  createSection: async (briefId, data) => {
    const resp = await fetch(`${API_BASE}/briefs/${briefId}/sections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(await parseApiError(resp));
    const section: BriefSection = await resp.json();
    // Update current brief's sections
    const brief = get().currentBrief;
    if (brief && brief.id === briefId) {
      set({ currentBrief: { ...brief, sections: [...brief.sections, section] } });
    }
    return section;
  },

  updateSection: async (briefId, sectionId, data) => {
    const resp = await fetch(`${API_BASE}/briefs/${briefId}/sections/${sectionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(await parseApiError(resp));
    const updated: BriefSection = await resp.json();
    const brief = get().currentBrief;
    if (brief && brief.id === briefId) {
      set({
        currentBrief: {
          ...brief,
          sections: brief.sections.map((s) => (s.id === sectionId ? updated : s)),
        },
      });
    }
  },

  deleteSection: async (briefId, sectionId) => {
    const resp = await fetch(`${API_BASE}/briefs/${briefId}/sections/${sectionId}`, {
      method: 'DELETE',
    });
    if (!resp.ok) throw new Error(await parseApiError(resp));
    const brief = get().currentBrief;
    if (brief && brief.id === briefId) {
      set({
        currentBrief: {
          ...brief,
          sections: brief.sections.filter((s) => s.id !== sectionId),
        },
      });
    }
  },

  regenerateSection: async (briefId, sectionId) => {
    set({ loading: true });
    try {
      const resp = await fetch(
        `${API_BASE}/briefs/${briefId}/sections/${sectionId}/regenerate`,
        { method: 'POST' }
      );
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const updated: BriefSection = await resp.json();
      const brief = get().currentBrief;
      if (brief && brief.id === briefId) {
        set({
          currentBrief: {
            ...brief,
            sections: brief.sections.map((s) => (s.id === sectionId ? updated : s)),
          },
          loading: false,
        });
      }
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  // --- Cascade Drafting ---

  draftSections: async (briefId, callbacks) => {
    set({ drafting: true, draftingSection: null, error: null });
    try {
      const eventSource = new EventSource(`${API_BASE}/briefs/${briefId}/draft?stream=true`);

      await new Promise<void>((resolve, reject) => {
        eventSource.addEventListener('drafting', (e) => {
          const data = JSON.parse(e.data);
          set({ draftingSection: data.section });
          callbacks?.onDrafting?.(data.section);
        });

        eventSource.addEventListener('section_ready', (e) => {
          const data = JSON.parse(e.data);
          callbacks?.onSectionReady?.(data.section, data.data);
          // Update brief sections progressively
          const brief = get().currentBrief;
          if (brief && brief.id === briefId) {
            set({
              currentBrief: {
                ...brief,
                sections: [...brief.sections, data.data],
              },
            });
          }
        });

        eventSource.addEventListener('done', (e) => {
          const data = JSON.parse(e.data);
          callbacks?.onDone?.(data.sections_created);
          eventSource.close();
          resolve();
        });

        eventSource.addEventListener('error', (e) => {
          let errorMsg = 'AI 起草失败';
          try {
            const data = JSON.parse((e as MessageEvent).data);
            errorMsg = data.error || errorMsg;
          } catch {
            // SSE error without data
          }
          callbacks?.onError?.(errorMsg);
          eventSource.close();
          reject(new Error(errorMsg));
        });

        eventSource.onerror = () => {
          eventSource.close();
          reject(new Error('SSE 连接断开'));
        };
      });

      set({ drafting: false, draftingSection: null });
    } catch (e) {
      set({ drafting: false, draftingSection: null, error: (e as Error).message });
    }
  },

  draftSectionsSync: async (briefId) => {
    set({ drafting: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/briefs/${briefId}/draft?stream=false`, {
        method: 'POST',
      });
      if (!resp.ok) throw new Error(await parseApiError(resp));
      // Refresh the brief to get all sections
      await get().fetchBrief(briefId);
      set({ drafting: false });
    } catch (e) {
      set({ drafting: false, error: (e as Error).message });
    }
  },

  // --- Code Generation ---

  generateCode: async (briefId) => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/briefs/${briefId}/generate`, {
        method: 'POST',
      });
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const code = await resp.json();
      set({ loading: false });
      return code;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  // --- Export ---

  exportBrief: async (briefId) => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/briefs/${briefId}/export`);
      if (!resp.ok) throw new Error(await parseApiError(resp));
      const markdown = await resp.text();
      set({ loading: false });
      return markdown;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },
}));
