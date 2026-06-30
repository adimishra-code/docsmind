import React from 'react';
import { useContextStore } from '@/store/useContextStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X, FileText, Settings2 } from 'lucide-react';
import { formatBytes } from '@/utils'; // Will implement or use inline

export function ContextManager() {
  const { pinnedDocuments, unpinDocument, clearContext } = useContextStore();

  // Rough estimate: 1 char ~= 0.25 tokens. Assuming 1 byte ~= 1 char for plain text roughly.
  // In reality backend provides real chunk counts and vector tokens.
  const estimatedTokens = pinnedDocuments.reduce((acc, doc) => acc + (doc.size_bytes * 0.25), 0);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b flex items-center justify-between bg-background">
        <div className="flex items-center gap-2 font-semibold">
          <Settings2 className="h-4 w-4" /> Context Manager
        </div>
        {pinnedDocuments.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearContext} className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground">
            Clear All
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1 p-4">
        {pinnedDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center mt-10 space-y-3">
            <FileText className="h-10 w-10 text-muted-foreground/30" />
            <div className="text-sm text-muted-foreground max-w-[200px]">
              Pin documents from the Knowledge Workspace to add them as context for this conversation.
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {pinnedDocuments.map(doc => (
              <div key={doc.id} className="flex items-center justify-between p-3 rounded-md border bg-card text-card-foreground shadow-sm group">
                <div className="flex items-center gap-3 overflow-hidden">
                  <FileText className="h-4 w-4 text-primary flex-shrink-0" />
                  <div className="flex flex-col overflow-hidden">
                    <span className="text-sm font-medium truncate">{doc.filename}</span>
                    <span className="text-xs text-muted-foreground uppercase">{doc.file_type} • {Math.round(doc.size_bytes / 1024)} KB</span>
                  </div>
                </div>
                <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8" onClick={() => unpinDocument(doc.id)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      <div className="p-4 border-t bg-background">
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>Estimated Context Size</span>
          <span>{Math.round(estimatedTokens).toLocaleString()} tokens</span>
        </div>
        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
          <div 
            className="h-full bg-primary" 
            style={{ width: `${Math.min((estimatedTokens / 128000) * 100, 100)}%` }} // Assume 128k context window
          />
        </div>
      </div>
    </div>
  );
}
