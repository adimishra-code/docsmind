import React, { useEffect } from 'react';
import { useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '@/services/documentsApi';
import { useViewerStore } from '@/store/useViewerStore';
import { PDFAdapter } from './PDFAdapter';
// import { MarkdownAdapter } from './MarkdownAdapter'; // Placeholder
import { MetadataPanel } from './MetadataPanel';
import { ActivityTimeline } from './ActivityTimeline';
import { Skeleton } from '@/components/ui/skeleton';
import { ResizablePanel, ResizablePanelGroup, ResizableHandle } from '@/components/ui/resizable';

export function KnowledgeEngine() {
  const { id } = useParams<{ id: string }>();
  const setActiveDocument = useViewerStore((state) => state.setActiveDocument);
  const { isMetadataPanelOpen, isTimelinePanelOpen } = useViewerStore();

  useEffect(() => {
    if (id) setActiveDocument(id);
    return () => setActiveDocument(null);
  }, [id, setActiveDocument]);

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.getById(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-full"><Skeleton className="w-[80%] h-[90%]" /></div>;
  }

  if (!document) {
    return <div className="flex items-center justify-center h-full">Document not found</div>;
  }

  const renderAdapter = () => {
    if (document.file_type === 'pdf') {
      // Use mock URL for now if backend doesn't serve actual file URL, or build it
      const fileUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/documents/${id}/download`;
      return <PDFAdapter url={fileUrl} />;
    }
    // Fallback or other adapters
    return <div className="p-8 text-center">Adapter for {document.file_type} not yet implemented</div>;
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-muted/10">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={100} className="relative flex-1">
          {renderAdapter()}
        </ResizablePanel>
        
        {(isMetadataPanelOpen || isTimelinePanelOpen) && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={25} minSize={20} maxSize={40} className="border-l bg-background">
              {isMetadataPanelOpen && <MetadataPanel document={document} />}
              {isTimelinePanelOpen && <ActivityTimeline document={document} />}
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  );
}
