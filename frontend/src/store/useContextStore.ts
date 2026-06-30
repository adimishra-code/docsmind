import { create } from 'zustand';
import { DocumentMetadata } from '@/services/documentsApi';

interface ContextState {
  pinnedDocuments: DocumentMetadata[];
  isContextPanelOpen: boolean;
  
  pinDocument: (doc: DocumentMetadata) => void;
  unpinDocument: (id: string) => void;
  clearContext: () => void;
  toggleContextPanel: () => void;
  setContextPanelOpen: (isOpen: boolean) => void;
}

export const useContextStore = create<ContextState>((set) => ({
  pinnedDocuments: [],
  isContextPanelOpen: true,

  pinDocument: (doc) => set((state) => {
    if (state.pinnedDocuments.some(d => d.id === doc.id)) return state;
    return { pinnedDocuments: [...state.pinnedDocuments, doc] };
  }),
  unpinDocument: (id) => set((state) => ({
    pinnedDocuments: state.pinnedDocuments.filter(d => d.id !== id)
  })),
  clearContext: () => set({ pinnedDocuments: [] }),
  toggleContextPanel: () => set((state) => ({ isContextPanelOpen: !state.isContextPanelOpen })),
  setContextPanelOpen: (isOpen) => set({ isContextPanelOpen: isOpen }),
}));
