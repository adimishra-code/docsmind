import React from 'react';
import { useContextStore } from '@/store/useContextStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { formatBytes, cn } from '@/utils';
import { X, FileText, BookOpen, PanelRightClose, Files } from 'lucide-react';

const CONTEXT_WINDOW_TOKENS = 128_000;

interface ContextManagerProps {
  hideCloseButton?: boolean;
}

export function ContextManager({ hideCloseButton = false }: ContextManagerProps) {
  const { pinnedDocuments, unpinDocument, clearContext, toggleContextPanel } = useContextStore();
  const estimatedTokens = pinnedDocuments.reduce(
    (acc, doc) => acc + ((doc.file_size ?? 0) * 0.25),
    0,
  );
  const usagePct = Math.min((estimatedTokens / CONTEXT_WINDOW_TOKENS) * 100, 100);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className={cn(
        "flex items-center justify-between px-4 h-14 border-b shrink-0",
        hideCloseButton && "pr-12"
      )}>
        <div className="flex items-center gap-2">
          <BookOpen className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
          <span className="text-sm font-medium">Context</span>
          {pinnedDocuments.length > 0 && (
            <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary/15 px-1 text-[10px] font-semibold text-primary tabular-nums">
              {pinnedDocuments.length}
            </span>
          )}
        </div>
        <div className="flex items-center">
          {pinnedDocuments.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearContext}
              className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground mr-1"
            >
              Clear all
            </Button>
          )}
          {!hideCloseButton && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleContextPanel}
              className="h-8 w-8 text-muted-foreground hover:text-foreground -mr-2"
              aria-label="Close context panel"
            >
              <PanelRightClose className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Document list */}
      <ScrollArea className="flex-1 px-3 py-3">
        {pinnedDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center py-10 px-2 space-y-3">
            <div className="h-10 w-10 rounded-xl bg-muted/50 border border-border/50 flex items-center justify-center">
              <Files className="h-4 w-4 text-muted-foreground/60" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-medium text-foreground/80">No context pinned</p>
              <p className="text-[11px] text-muted-foreground leading-relaxed max-w-[160px]">
                Right-click a document to add it to the chat context.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {pinnedDocuments.map((doc) => (
              <div
                key={doc.id}
                className="group flex items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5 hover:border-muted-foreground/25 transition-colors duration-100"
              >
                <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium truncate leading-snug" title={doc.filename}>
                    {doc.filename}
                  </p>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide mt-0.5">
                    {doc.file_type} · {formatBytes(doc.file_size)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 transition-opacity duration-100 h-6 w-6 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={() => unpinDocument(doc.id)}
                  aria-label={`Remove ${doc.filename} from context`}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Token usage estimate — only shown when documents are pinned */}
      {pinnedDocuments.length > 0 && (
        <div className="px-4 py-3 border-t shrink-0 space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
            <span title="Estimated at ~0.25 tokens per byte — approximate only">
              Est. context usage
            </span>
            <span className="tabular-nums font-medium">
              {Math.round(estimatedTokens).toLocaleString()} / {CONTEXT_WINDOW_TOKENS.toLocaleString()}
            </span>
          </div>
          <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${usagePct}%`,
                backgroundColor: usagePct > 80
                  ? 'hsl(var(--destructive))'
                  : usagePct > 50
                  ? 'hsl(var(--warning))'
                  : 'hsl(var(--primary))',
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
