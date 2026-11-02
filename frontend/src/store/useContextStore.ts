import { create } from 'zustand';
import { DocumentMetadata } from '@/services/documentsApi';

/** Panel open/closed preferences are remembered across sessions. Kept in a tiny
 *  localStorage helper (not a full persist middleware) so only these two booleans
 *  are stored and the rest of the store stays in-memory/session-scoped. */
const PANEL_PREFS_KEY = 'docsmind:panels';

interface PanelPrefs {
  context: boolean;
  conversations: boolean;
}

function loadPanelPrefs(): PanelPrefs {
  const defaults: PanelPrefs = { context: true, conversations: true };
  try {
    const raw = localStorage.getItem(PANEL_PREFS_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return {
      context: typeof parsed.context === 'boolean' ? parsed.context : defaults.context,
      conversations:
        typeof parsed.conversations === 'boolean' ? parsed.conversations : defaults.conversations,
    };
  } catch {
    return defaults;
  }
}

function savePanelPrefs(prefs: PanelPrefs): void {
  try {
    localStorage.setItem(PANEL_PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* storage unavailable (private mode) — preferences simply won't persist */
  }
}

interface ContextState {
  pinnedDocuments: DocumentMetadata[];
  isContextPanelOpen: boolean;
  /** Whether the left-hand conversation list panel is expanded. */
  isConversationPanelOpen: boolean;
  /** Mobile-only slide-over drawer states (never auto-open on load/resize) */
  isMobileChatsOpen: boolean;
  isMobileContextOpen: boolean;

  pinDocument: (doc: DocumentMetadata) => void;
  unpinDocument: (id: string) => void;
  clearContext: () => void;
  toggleContextPanel: () => void;
  setContextPanelOpen: (isOpen: boolean) => void;
  toggleConversationPanel: () => void;
  setConversationPanelOpen: (isOpen: boolean) => void;
  setMobileChatsOpen: (isOpen: boolean) => void;
  setMobileContextOpen: (isOpen: boolean) => void;
  toggleMobileChats: () => void;
  toggleMobileContext: () => void;
}

const initialPrefs = loadPanelPrefs();

export const useContextStore = create<ContextState>((set, get) => ({
  pinnedDocuments: [],
  isContextPanelOpen: initialPrefs.context,
  isConversationPanelOpen: initialPrefs.conversations,
  isMobileChatsOpen: false,
  isMobileContextOpen: false,

  pinDocument: (doc) => set((state) => {
    if (state.pinnedDocuments.some(d => d.id === doc.id)) return state;
    return { pinnedDocuments: [...state.pinnedDocuments, doc] };
  }),
  unpinDocument: (id) => set((state) => ({
    pinnedDocuments: state.pinnedDocuments.filter(d => d.id !== id)
  })),
  clearContext: () => set({ pinnedDocuments: [] }),

  toggleContextPanel: () => set((state) => {
    const next = !state.isContextPanelOpen;
    savePanelPrefs({ context: next, conversations: state.isConversationPanelOpen });
    return { isContextPanelOpen: next };
  }),
  setContextPanelOpen: (isOpen) => {
    savePanelPrefs({ context: isOpen, conversations: get().isConversationPanelOpen });
    set({ isContextPanelOpen: isOpen });
  },

  toggleConversationPanel: () => set((state) => {
    const next = !state.isConversationPanelOpen;
    savePanelPrefs({ context: state.isContextPanelOpen, conversations: next });
    return { isConversationPanelOpen: next };
  }),
  setConversationPanelOpen: (isOpen) => {
    savePanelPrefs({ context: get().isContextPanelOpen, conversations: isOpen });
    set({ isConversationPanelOpen: isOpen });
  },

  setMobileChatsOpen: (isOpen) => set({ isMobileChatsOpen: isOpen }),
  setMobileContextOpen: (isOpen) => set({ isMobileContextOpen: isOpen }),
  toggleMobileChats: () => set((state) => ({ isMobileChatsOpen: !state.isMobileChatsOpen })),
  toggleMobileContext: () => set((state) => ({ isMobileContextOpen: !state.isMobileContextOpen })),
}));
