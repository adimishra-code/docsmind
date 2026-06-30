import React from 'react';
import { DocumentMetadata } from '@/services/documentsApi';
import { ScrollArea } from '@/components/ui/scroll-area';
import { format } from 'date-fns';
import { History, Upload, FileSearch, SplitSquareHorizontal, BrainCircuit, CheckCircle2 } from 'lucide-react';
import { cn } from '@/utils';

export function ActivityTimeline({ document }: { document: DocumentMetadata }) {
  // Mock timeline events based on the current status
  // In a real app, these would come from an audit log API
  const events = [
    { id: 1, title: 'Document Uploaded', time: document.created_at, icon: Upload, done: true },
    { id: 2, title: 'OCR & Text Extraction', time: document.created_at, icon: FileSearch, done: ['parsing', 'chunking', 'embedding', 'ready'].includes(document.status) },
    { id: 3, title: 'Semantic Chunking', time: document.updated_at, icon: SplitSquareHorizontal, done: ['chunking', 'embedding', 'ready'].includes(document.status) },
    { id: 4, title: 'Vector Embedding', time: document.updated_at, icon: BrainCircuit, done: ['embedding', 'ready'].includes(document.status) },
    { id: 5, title: 'Indexed for Search', time: document.updated_at, icon: CheckCircle2, done: document.status === 'ready' },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b font-semibold flex items-center gap-2">
        <History className="h-4 w-4" /> Activity Timeline
      </div>
      <ScrollArea className="flex-1 p-4">
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
