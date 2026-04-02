import { create } from 'zustand';

export type TabId = 'input' | 'review' | 'response' | 'results';

interface SessionStore {
  activeSessionId: string | null;
  setActiveSession: (sessionId: string) => void;

  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;

  focusedDetectionId: string | null;
  setFocusedDetection: (id: string | null) => void;

  resetSession: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  activeSessionId: null,
  setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),

  activeTab: 'input',
  setActiveTab: (tab) => set({ activeTab: tab }),

  focusedDetectionId: null,
  setFocusedDetection: (id) => set({ focusedDetectionId: id }),

  resetSession: () => set({ activeSessionId: null, activeTab: 'input', focusedDetectionId: null }),
}));
