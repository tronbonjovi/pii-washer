import { create } from 'zustand';

export type TabId = 'input' | 'review' | 'response' | 'results';

interface SessionStore {
  activeSessionId: string | null;
  setActiveSession: (sessionId: string) => void;
  clearActiveSession: () => void;

  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;

  focusedDetectionId: string | null;
  setFocusedDetection: (id: string | null) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  activeSessionId: null,
  setActiveSession: (sessionId) => set({ activeSessionId: sessionId }),
  clearActiveSession: () => set({ activeSessionId: null, activeTab: 'input', focusedDetectionId: null }),

  activeTab: 'input',
  setActiveTab: (tab) => set({ activeTab: tab }),

  focusedDetectionId: null,
  setFocusedDetection: (id) => set({ focusedDetectionId: id }),
}));
