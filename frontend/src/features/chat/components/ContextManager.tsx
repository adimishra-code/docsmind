import React from 'react';
import { useContextStore } from '@/store/useContextStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X, FileText } from 'lucide-react';

export function ContextManager() {
  const { pinnedDocuments, unpinDocument, clearContext } = useContextStore();
  const estimatedTokens = pinnedDocuments.reduce((acc, doc) => acc + (doc.size_bytes * 0.25), 0);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="text-sm font-medium">Context</h3>
        {pinnedDocuments.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearContext} className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground">
            Clear
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1 p-4">
        {pinnedDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center mt-12 space-y-2">
            <FileText className="h-8 w-8 text-muted-foreground/30" />
            <p className="text-xs text-muted-foreground max-w-[180px]">
              Pin documents from the workspace to add context.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {pinnedDocuments.map(doc => (
              <div key={doc.id} className="flex items-center justify-between p-2.5 rounded-lg border bg-card group hover:border-muted-foreground/30 transition-colors">
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate">{doc.filename}</p>
                    <p className="text-[10px] text-muted-foreground uppercase">{doc.file_type} · {Math.round(doc.size_bytes / 1024)} KB</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 shrink-0"
                  onClick={() => unpinDocument(doc.id)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {pinnedDocuments.length > 0 && (
        <div className="p-4 border-t">
          <div className="flex justify-between text-[10px] text-muted-foreground mb-1.5">
            <span title="Rough estimate (~0.25 tokens per byte), not an exact count">Estimated tokens</span>
            <span>~{Math.round(estimatedTokens).toLocaleString()}</span>
          </div>
          <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${Math.min((estimatedTokens / 128000) * 100, 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
