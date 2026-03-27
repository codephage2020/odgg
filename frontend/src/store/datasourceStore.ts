// Datasource management with localStorage persistence
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SavedDatasource } from '../types/datasource';

interface DatasourceStore {
  datasources: SavedDatasource[];
  activeId: string | null;

  addDatasource: (ds: Omit<SavedDatasource, 'id' | 'createdAt' | 'lastUsedAt'>) => SavedDatasource;
  updateDatasource: (id: string, patch: Partial<SavedDatasource>) => void;
  removeDatasource: (id: string) => void;
  setActive: (id: string | null) => void;
  getActive: () => SavedDatasource | null;
  buildConnectionUrl: (id: string, password: string) => string;
}

export const useDatasourceStore = create<DatasourceStore>()(
  persist(
    (set, get) => ({
      datasources: [],
      activeId: null,

      addDatasource: (ds) => {
        const newDs: SavedDatasource = {
          ...ds,
          id: crypto.randomUUID(),
          createdAt: new Date().toISOString(),
          lastUsedAt: new Date().toISOString(),
        };
        set((s) => ({ datasources: [...s.datasources, newDs] }));
        return newDs;
      },

      updateDatasource: (id, patch) => {
        set((s) => ({
          datasources: s.datasources.map((d) =>
            d.id === id ? { ...d, ...patch } : d
          ),
        }));
      },

      removeDatasource: (id) => {
        set((s) => ({
          datasources: s.datasources.filter((d) => d.id !== id),
          activeId: s.activeId === id ? null : s.activeId,
        }));
      },

      setActive: (id) => {
        if (id) {
          set((s) => ({
            activeId: id,
            datasources: s.datasources.map((d) =>
              d.id === id ? { ...d, lastUsedAt: new Date().toISOString() } : d
            ),
          }));
        } else {
          set({ activeId: null });
        }
      },

      getActive: () => {
        const { datasources, activeId } = get();
        return datasources.find((d) => d.id === activeId) || null;
      },

      buildConnectionUrl: (id, password) => {
        const ds = get().datasources.find((d) => d.id === id);
        if (!ds) return '';
        return `postgresql+asyncpg://${ds.username}:${password}@${ds.host}:${ds.port}/${ds.database}`;
      },
    }),
    { name: 'odgg-datasources' }
  )
);
