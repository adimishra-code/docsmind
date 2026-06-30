import React from 'react';
import { PDFWrapper } from '@/components/documents/PDFWrapper';
import { useViewerStore } from '@/store/useViewerStore';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight, PanelRightClose, PanelRightOpen, History } from 'lucide-react';

interface PDFAdapterProps {
  url: string;
}

export function PDFAdapter({ url }: PDFAdapterProps) {
  const { 
    zoomLevel, setZoom, 
    currentPage, setPage, 
    numPages, setNumPages,
    isMetadataPanelOpen, toggleMetadataPanel,
    isTimelinePanelOpen, toggleTimelinePanel
  } = useViewerStore();

  return (
    <div className="flex flex-col h-full w-full">
      {/* Viewer Toolbar */}
      <div className="flex items-center justify-between p-2 border-b bg-background shadow-sm z-10">
        <div className="flex items-center space-x-2">
          <Button variant="ghost" size="icon" onClick={() => setPage(currentPage - 1)} disabled={currentPage <= 1}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium w-20 text-center">
            {currentPage} / {numPages || '?'}
          </span>
          <Button variant="ghost" size="icon" onClick={() => setPage(currentPage + 1)} disabled={!!numPages && currentPage >= numPages}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button variant="ghost" size="icon" onClick={() => setZoom(zoomLevel - 0.25)}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm w-12 text-center">{Math.round(zoomLevel * 100)}%</span>
          <Button variant="ghost" size="icon" onClick={() => setZoom(zoomLevel + 0.25)}>
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center space-x-2 border-l pl-2">
          <Button 
            variant={isTimelinePanelOpen ? "secondary" : "ghost"} 
            size="icon" 
            onClick={toggleTimelinePanel}
            title="Activity Timeline"
          >
            <History className="h-4 w-4" />
          </Button>
          <Button 
            variant={isMetadataPanelOpen ? "secondary" : "ghost"} 
            size="icon" 
            onClick={toggleMetadataPanel}
            title="Metadata Panel"
          >
            {isMetadataPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      
      {/* Canvas Area */}
      <div className="flex-1 overflow-auto bg-muted/30 p-4 flex justify-center" style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}>
        <PDFWrapper 
          url={url} 
          pageNumber={currentPage} 
          onLoadSuccess={setNumPages} 
          className="shadow-xl"
        />
      </div>
    </div>
  );
}
