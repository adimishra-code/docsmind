import { create } from 'zustand';

export type FitMode = 'width' | 'page' | 'actual';

interface ViewerState {
  activeDocumentId: string | null;
  zoomLevel: number;
  fitMode: FitMode;
  currentPage: number;
  numPages: number | null;
  /** Cited passage text to highlight on the current page (from a chat citation). */
  highlightText: string | null;
  isMetadataPanelOpen: boolean;
  isTimelinePanelOpen: boolean;

  setActiveDocument: (id: string | null) => void;
  setZoom: (zoom: number) => void;
  setFitMode: (mode: FitMode) => void;
  setPage: (page: number) => void;
  setNumPages: (num: number | null) => void;
  setHighlight: (text: string | null) => void;
  /** Jump straight to a page (and optionally highlight a passage) — used when a
   *  chat citation deep-links into the document via ?page=&highlight=. */
  jumpTo: (page: number, highlight?: string | null) => void;
  toggleMetadataPanel: () => void;
  toggleTimelinePanel: () => void;
}

export const useViewerStore = create<ViewerState>((set) => ({
  activeDocumentId: null,
  zoomLevel: 1.0,
  // Fit-to-width is the calm default — the page fills the canvas without the
  // user hunting for a zoom level or fighting horizontal scroll.
  fitMode: 'width',
  currentPage: 1,
  numPages: null,
  highlightText: null,
  // Intelligence panel open by default so the viewer reads as a knowledge
  // workspace (insights + related docs), not a bare file preview. Insights are
  // generated once and cached server-side, so re-opens are instant.
  isMetadataPanelOpen: true,
  isTimelinePanelOpen: false,

  setActiveDocument: (id) =>
    set({ activeDocumentId: id, currentPage: 1, zoomLevel: 1.0, fitMode: 'width', highlightText: null }),
  setZoom: (zoom) => set({ zoomLevel: Math.max(0.5, Math.min(zoom, 3.0)), fitMode: 'actual' }),
  setFitMode: (mode) => set({ fitMode: mode }),
  setPage: (page) => set({ currentPage: Math.max(1, page) }),
  setNumPages: (num) => set({ numPages: num }),
  setHighlight: (text) => set({ highlightText: text || null }),
  jumpTo: (page, highlight) =>
    set({ currentPage: Math.max(1, page || 1), highlightText: highlight || null }),
  toggleMetadataPanel: () => set((state) => ({ isMetadataPanelOpen: !state.isMetadataPanelOpen, isTimelinePanelOpen: false })),
  toggleTimelinePanel: () => set((state) => ({ isTimelinePanelOpen: !state.isTimelinePanelOpen, isMetadataPanelOpen: false })),
}));
