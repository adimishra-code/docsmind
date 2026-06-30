import React from 'react';
import { DocumentMetadata } from '@/services/documentsApi';
import { ScrollArea } from '@/components/ui/scroll-area';
import { format } from 'date-fns';
import { FileText, Database, Info } from 'lucide-react';

export function MetadataPanel({ document }: { document: DocumentMetadata }) {
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b font-semibold flex items-center gap-2">
        <Info className="h-4 w-4" /> Document Properties
      </div>
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6">
          <section>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">General</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Filename</span>
                <span className="font-medium truncate max-w-[150px]">{document.filename}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium uppercase">{document.file_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Size</span>
                <span className="font-medium">{(document.size_bytes / (1024 * 1024)).toFixed(2)} MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Uploaded</span>
                <span className="font-medium">{format(new Date(document.created_at), 'PPP')}</span>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1">
              <Database className="h-3 w-3" /> Processing Engine
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <span className="font-medium capitalize">{document.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Chunks</span>
                <span className="font-medium">{document.chunk_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Embedding Model</span>
                <span className="font-medium">OpenAI text-embedding-3-small</span>
              </div>
            </div>
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
