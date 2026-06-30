import { create } from 'zustand';

interface WorkspaceState {
  viewMode: 'grid' | 'list';
  activeFolderId: string | null;
  selectedDocumentIds: string[];
  searchQuery: string;
  setViewMode: (mode: 'grid' | 'list') => void;
  setActiveFolder: (id: string | null) => void;
  toggleDocumentSelection: (id: string) => void;
  clearSelection: () => void;
  setSearchQuery: (query: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  viewMode: 'grid',
  activeFolderId: null,
  selectedDocumentIds: [],
  searchQuery: '',
  setViewMode: (mode) => set({ viewMode: mode }),
  setActiveFolder: (id) => set({ activeFolderId: id, selectedDocumentIds: [] }),
  toggleDocumentSelection: (id) => set((state) => {
    const isSelected = state.selectedDocumentIds.includes(id);
    return {
      selectedDocumentIds: isSelected 
        ? state.selectedDocumentIds.filter(dId => dId !== id)
        : [...state.selectedDocumentIds, id]
    };
  }),
  clearSelection: () => set({ selectedDocumentIds: [] }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
