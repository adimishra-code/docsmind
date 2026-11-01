import React, { useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import {
  documentsApi,
  type DocumentMetadata,
  isDocumentProcessing,
  isDocumentFailed,
  documentStatusLabel,
} from '@/services/documentsApi';
import { useViewerStore } from '@/store/useViewerStore';
import { useReprocessDocument } from '@/features/knowledge/hooks/useReprocessDocument';
import { PDFAdapter } from './PDFAdapter';
import { MetadataPanel } from './MetadataPanel';
import { ActivityTimeline } from './ActivityTimeline';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { ResizablePanel, ResizablePanelGroup, ResizableHandle } from '@/components/ui/resizable';
import { FileText, Download, Loader2, AlertTriangle, RefreshCw } from 'lucide-react';

export function KnowledgeEngine() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const setActiveDocument = useViewerStore((state) => state.setActiveDocument);
  const jumpTo = useViewerStore((state) => state.jumpTo);
  const { isMetadataPanelOpen, isTimelinePanelOpen } = useViewerStore();

  useEffect(() => {
    if (id) setActiveDocument(id);
    return () => setActiveDocument(null);
  }, [id, setActiveDocument]);

  // Deep-link from a chat citation: `?page=26&highlight=<cited passage>`. Runs
  // after setActiveDocument (which resets to page 1) so the cited page wins.
  useEffect(() => {
    const page = Number(searchParams.get('page'));
    const highlight = searchParams.get('highlight');
    if (page && !Number.isNaN(page)) {
      jumpTo(page, highlight);
    } else if (highlight) {
      jumpTo(1, highlight);
    }
  }, [searchParams, jumpTo, id]);

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentsApi.getById(id!),
    enabled: !!id,
    // Live-refresh while the document is still being ingested; stop once it
    // reaches a terminal state (completed | failed). Mirrors the workspace grid.
    refetchInterval: (query) =>
      query.state.data && isDocumentProcessing(query.state.data.status) ? 4000 : false,
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-full"><Skeleton className="w-[80%] h-[90%]" /></div>;
  }

  if (!document) {
    return <div className="flex items-center justify-center h-full">Document not found</div>;
  }

  const renderAdapter = () => {
    // The document is the single source of truth: gate the preview on its
    // lifecycle status before attempting to render any file adapter.
    if (isDocumentFailed(document.status)) {
      return <FailedState document={document} />;
    }
    if (isDocumentProcessing(document.status)) {
      return <ProcessingState document={document} />;
    }
    if (document.file_type === 'pdf') {
      // Points at the real backend download endpoint; react-pdf streams from it.
      const fileUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8006'}/api/v1/documents/${id}/download`;
      return <PDFAdapter url={fileUrl} />;
    }
    // Inline preview currently only supports PDFs — offer a download instead of a dead end.
    return <UnsupportedPreview document={document} />;
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-muted/10">
      <ResizablePanelGroup orientation="horizontal">
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

/** Terminal-failure state: surface the backend error and offer a retry. */
function FailedState({ document }: { document: DocumentMetadata }) {
  const reprocess = useReprocessDocument();
  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center">
      <Alert variant="destructive" className="max-w-md text-left">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Processing failed</AlertTitle>
        <AlertDescription>
          {document.error_message
            ? document.error_message
            : 'The document could not be indexed. You can retry the ingestion pipeline.'}
        </AlertDescription>
      </Alert>
      <Button
        className="mt-5 gap-2"
        disabled={reprocess.isPending}
        onClick={() => reprocess.mutate(document.id)}
      >
        {reprocess.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Retry processing
      </Button>
    </div>
  );
}

/** In-flight ingestion state: spinner + live status while indexing runs. */
function ProcessingState({ document }: { document: DocumentMetadata }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground/70" />
      </div>
      <h3 className="mt-4 text-base font-medium">{documentStatusLabel(document.status)}…</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        We're parsing, chunking, and indexing this document so it becomes fully
        searchable. This view will update automatically when it's ready.
      </p>
    </div>
  );
}

function UnsupportedPreview({ document }: { document: DocumentMetadata }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
        <FileText className="h-8 w-8 text-muted-foreground/60" />
      </div>
      <h3 className="mt-4 text-base font-medium">Inline preview isn’t available for this file</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        Preview currently supports PDFs. This{' '}
        <span className="font-medium uppercase">{document.file_type}</span> file has been
        indexed and is fully searchable — you can download the original to view it.
      </p>
      <Button
        className="mt-5 gap-2"
        onClick={() => documentsApi.download(document.id, document.filename)}
      >
        <Download className="h-4 w-4" />
        Download original
      </Button>
    </div>
  );
}
