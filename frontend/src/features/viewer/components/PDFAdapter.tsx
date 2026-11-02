import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { PDFWrapper } from '@/components/documents/PDFWrapper';
import { useViewerStore } from '@/store/useViewerStore';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils';
import {
  ZoomIn, ZoomOut, ChevronLeft, ChevronRight,
  PanelRightClose, PanelRightOpen, History,
  MoveHorizontal, Maximize2,
} from 'lucide-react';

interface PDFAdapterProps {
  url: string;
}

export function PDFAdapter({ url }: PDFAdapterProps) {
  const {
    zoomLevel, setZoom,
    fitMode, setFitMode,
    currentPage, setPage,
    numPages, setNumPages,
    highlightText,
    isMetadataPanelOpen, toggleMetadataPanel,
    isTimelinePanelOpen, toggleTimelinePanel,
  } = useViewerStore();

  const canvasRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const measure = () => {
      const padding = el.clientWidth < 640 ? 16 : 48;
      setDims({
        width: Math.max(0, el.clientWidth - padding),
        height: Math.max(0, el.clientHeight - padding),
      });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Keyboard: ←/→ pages, +/- zoom
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.key === 'ArrowLeft' && currentPage > 1) setPage(currentPage - 1);
      else if (e.key === 'ArrowRight' && (!numPages || currentPage < numPages)) setPage(currentPage + 1);
      else if (e.key === '+' || e.key === '=') setZoom(zoomLevel + 0.15);
      else if (e.key === '-' || e.key === '_') setZoom(zoomLevel - 0.15);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [currentPage, numPages, zoomLevel, setPage, setZoom]);

  const zoomPercent = fitMode === 'actual' ? `${Math.round(zoomLevel * 100)}%` : 'Fit';

  return (
    <div className="flex flex-col h-full w-full">
      {/* Viewer toolbar — responsive, horizontally scrollable if needed */}
      <div className="flex items-center justify-between px-2 sm:px-3 h-12 border-b bg-background/80 backdrop-blur-sm z-10 gap-1 overflow-x-auto">
        {/* Page navigation */}
        <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setPage(currentPage - 1)}
            disabled={currentPage <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs sm:text-sm tabular-nums text-muted-foreground w-12 sm:w-16 text-center">
            {currentPage}/{numPages || '—'}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setPage(currentPage + 1)}
            disabled={!!numPages && currentPage >= numPages}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Fit + zoom */}
        <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
          <Button
            variant={fitMode === 'width' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 gap-1 px-1.5 sm:px-2 text-xs"
            onClick={() => setFitMode('width')}
            title="Fit width"
          >
            <MoveHorizontal className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Width</span>
          </Button>
          <Button
            variant={fitMode === 'page' ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 gap-1 px-1.5 sm:px-2 text-xs"
            onClick={() => setFitMode('page')}
            title="Fit page"
          >
            <Maximize2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Page</span>
          </Button>
          <div className="mx-0.5 sm:mx-1 h-4 w-px bg-border" />
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setZoom(zoomLevel - 0.15)}
            aria-label="Zoom out"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <span className="text-[11px] sm:text-xs tabular-nums w-8 sm:w-10 text-center text-muted-foreground">
            {zoomPercent}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setZoom(zoomLevel + 0.15)}
            aria-label="Zoom in"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Panels toggle */}
        <div className="flex items-center gap-0.5 sm:gap-1 border-l pl-1.5 sm:pl-2 shrink-0">
          <Button
            variant={isTimelinePanelOpen ? 'secondary' : 'ghost'}
            size="icon"
            className="h-8 w-8"
            onClick={toggleTimelinePanel}
            title="Activity timeline"
            aria-label="Toggle activity timeline"
          >
            <History className="h-4 w-4" />
          </Button>
          <Button
            variant={isMetadataPanelOpen ? 'secondary' : 'ghost'}
            size="icon"
            className="h-8 w-8"
            onClick={toggleMetadataPanel}
            title="Document properties"
            aria-label="Toggle document properties"
          >
            {isMetadataPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className={cn(
          'flex-1 overflow-auto bg-muted/30 p-2 sm:p-6 flex justify-center',
          fitMode === 'page' && 'items-center'
        )}
      >
        <PDFWrapper
          url={url}
          pageNumber={currentPage}
          onLoadSuccess={setNumPages}
          highlight={highlightText}
          fitMode={fitMode}
          zoomLevel={zoomLevel}
          containerWidth={dims.width}
          containerHeight={dims.height}
        />
      </div>
    </div>
  );
}
