import { create } from 'zustand';

interface ViewerState {
  activeDocumentId: string | null;
  zoomLevel: number;
  currentPage: number;
  numPages: number | null;
  isMetadataPanelOpen: boolean;
  isTimelinePanelOpen: boolean;
  
  setActiveDocument: (id: string | null) => void;
  setZoom: (zoom: number) => void;
  setPage: (page: number) => void;
  setNumPages: (num: number | null) => void;
  toggleMetadataPanel: () => void;
  toggleTimelinePanel: () => void;
}

export const useViewerStore = create<ViewerState>((set) => ({
  activeDocumentId: null,
  zoomLevel: 1.0,
  currentPage: 1,
  numPages: null,
  isMetadataPanelOpen: false,
  isTimelinePanelOpen: false,

  setActiveDocument: (id) => set({ activeDocumentId: id, currentPage: 1, zoomLevel: 1.0 }),
  setZoom: (zoom) => set({ zoomLevel: Math.max(0.5, Math.min(zoom, 3.0)) }),
  setPage: (page) => set({ currentPage: Math.max(1, page) }),
  setNumPages: (num) => set({ numPages: num }),
  toggleMetadataPanel: () => set((state) => ({ isMetadataPanelOpen: !state.isMetadataPanelOpen, isTimelinePanelOpen: false })),
  toggleTimelinePanel: () => set((state) => ({ isTimelinePanelOpen: !state.isTimelinePanelOpen, isMetadataPanelOpen: false })),
}));
