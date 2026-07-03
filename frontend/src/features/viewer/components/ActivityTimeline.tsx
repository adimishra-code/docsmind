import React from 'react';
import { DocumentMetadata, isDocumentReady, isDocumentFailed } from '@/services/documentsApi';
import { ScrollArea } from '@/components/ui/scroll-area';
import { format } from 'date-fns';
import { History, Upload, FileSearch, SplitSquareHorizontal, BrainCircuit, CheckCircle2 } from 'lucide-react';
import { cn } from '@/utils';

export function ActivityTimeline({ document }: { document: DocumentMetadata }) {
  // Derived from the document's real status. The backend reports coarse states
  // (pending → processing → completed/failed), so the processing stages are
  // marked complete only once ingestion has finished.
  const ready = isDocumentReady(document.status);
  const failed = isDocumentFailed(document.status);
  const events = [
    { id: 1, title: 'Document Uploaded', time: document.created_at, icon: Upload, done: true },
    { id: 2, title: 'OCR & Text Extraction', time: document.updated_at, icon: FileSearch, done: ready },
    { id: 3, title: 'Semantic Chunking', time: document.updated_at, icon: SplitSquareHorizontal, done: ready },
    { id: 4, title: 'Vector Embedding', time: document.updated_at, icon: BrainCircuit, done: ready },
    { id: 5, title: 'Indexed for Search', time: document.updated_at, icon: CheckCircle2, done: ready },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b font-semibold flex items-center gap-2">
        <History className="h-4 w-4" /> Activity Timeline
      </div>
      <ScrollArea className="flex-1 p-4">
        {failed && (
          <div className="mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm">
            <span className="text-destructive font-medium">Processing failed.</span>
            <span className="text-muted-foreground">
              {document.error_message || 'This document could not be indexed. Try deleting and re-uploading it.'}
            </span>
          </div>
        )}
        <div className="relative border-l border-muted ml-3 space-y-8 py-2">
          {events.map((event, index) => {
            const Icon = event.icon;
            return (
              <div key={event.id} className={cn("relative pl-6", !event.done && "opacity-50")}>
                <div className={cn(
                  "absolute -left-3.5 top-0 h-7 w-7 rounded-full border-2 bg-background flex items-center justify-center",
                  event.done ? "border-primary text-primary" : "border-muted text-muted-foreground"
                )}>
                  <Icon className="h-3 w-3" />
                </div>
                <div className="flex flex-col pt-1">
                  <span className="text-sm font-medium">{event.title}</span>
                  {event.done && (
                    <span className="text-xs text-muted-foreground mt-0.5">
                      {format(new Date(event.time), 'MMM d, h:mm a')}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
