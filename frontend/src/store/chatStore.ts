// AI chat store for conversational model editing
import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai' | 'system';
  content: string;
  stepNumber?: number;
  suggestion?: Record<string, unknown>;
  timestamp: string;
  status: 'complete' | 'streaming' | 'error';
}

interface ChatStore {
  messages: ChatMessage[];
  isStreaming: boolean;

  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,

  addMessage: (msg) => {
    const id = crypto.randomUUID();
    const message: ChatMessage = {
      ...msg,
      id,
      timestamp: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, message] }));
    return id;
  },

  updateMessage: (id, patch) => {
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    }));
  },

  clearMessages: () => set({ messages: [] }),
}));
