import { create } from 'zustand';
import type { DocumentMetadata } from '@/services/documentsApi';

export type SortKey = 'name' | 'date' | 'size';
export type SortDir = 'asc' | 'desc';

interface WorkspaceState {
  viewMode: 'grid' | 'list';
  activeFolderId: string | null;
  selectedDocumentIds: string[];
  searchQuery: string;
  sortKey: SortKey;
  sortDir: SortDir;
  setViewMode: (mode: 'grid' | 'list') => void;
  setActiveFolder: (id: string | null) => void;
  toggleDocumentSelection: (id: string) => void;
  clearSelection: () => void;
  setSearchQuery: (query: string) => void;
  setSortKey: (key: SortKey) => void;
  setSortDir: (dir: SortDir) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  viewMode: 'grid',
  activeFolderId: null,
  selectedDocumentIds: [],
  searchQuery: '',
  sortKey: 'date',
  sortDir: 'desc',
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
  setSortKey: (key) => set({ sortKey: key }),
  setSortDir: (dir) => set({ sortDir: dir }),
}));

/** Pure, stable sort of documents by the chosen key/direction. Does not mutate input. */
export function sortDocuments(
  docs: DocumentMetadata[],
  key: SortKey,
  dir: SortDir,
): DocumentMetadata[] {
  const factor = dir === 'asc' ? 1 : -1;
  return [...docs].sort((a, b) => {
    let cmp = 0;
    if (key === 'name') {
      cmp = a.filename.localeCompare(b.filename, undefined, { sensitivity: 'base' });
    } else if (key === 'size') {
      cmp = (a.file_size ?? 0) - (b.file_size ?? 0);
    } else {
      cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    }
    return cmp * factor;
  });
}
