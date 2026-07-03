import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css'; // or any highlight style you prefer
import { Message } from '@/services/chatApi';
import { cn } from '@/utils';
import { Bot, User, Copy, Check, RefreshCw, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CitationCard, type CitationProps } from './CitationCard';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  /** When provided, renders a "Regenerate" action (used for the latest reply). */
  onRegenerate?: () => void;
}

type Citation = CitationProps['citation'];

export function MessageBubble({ message, isStreaming = false, onRegenerate }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const citations = (message.citations as Citation[] | undefined) ?? undefined;

  // The model emits bare `[1]` markers as plain text, which react-markdown will
  // not turn into anchors. Deterministically rewrite valid markers into links
  // (`[1](#cite-1)`) so the anchor renderer below can swap them for badges.
  const renderedContent = useMemo(() => {
    let content = message.content;
    if (citations?.length) {
      content = content.replace(/\[(\d+)\](?!\()/g, (match, digits) => {
        const idx = Number(digits) - 1;
        return idx >= 0 && idx < citations.length ? `[${digits}](#cite-${digits})` : match;
      });
    }
    return content + (isStreaming ? ' ▍' : '');
  }, [message.content, citations, isStreaming]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable (e.g. insecure context) — silently no-op.
    }
  };

  const showActions = !isUser && !isStreaming && message.content.length > 0;
  const showSources = !isUser && !isStreaming && !!citations?.length;

  return (
    <div className={cn("group flex w-full py-6", isUser ? "bg-background" : "bg-muted/30")}>
      <div className="max-w-4xl mx-auto w-full flex gap-4 px-4">
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              <User className="h-5 w-5" />
            </div>
          ) : (
            <div className="h-8 w-8 rounded-md bg-secondary border flex items-center justify-center text-secondary-foreground">
              <Bot className="h-5 w-5" />
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="prose prose-neutral dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={{
                a: ({ node: _node, href, ...props }) => {
                  if (href?.startsWith('#cite-') && citations) {
                    const index = parseInt(href.slice('#cite-'.length), 10);
                    const citation = citations[index - 1];
                    if (citation) {
                      return <CitationCard citation={citation} index={index} />;
                    }
                  }
                  return <a {...props} href={href} target="_blank" rel="noreferrer" className="text-primary hover:underline" />;
                }
              }}
            >
              {renderedContent}
            </ReactMarkdown>
          </div>

          {showSources && <CitationSources citations={citations!} />}

          {showActions && (
            <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
                aria-label="Copy message"
              >
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
              {onRegenerate && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onRegenerate}
                  className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
                  aria-label="Regenerate response"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Regenerate
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Premium, honest "Sources" list rendered under an assistant answer. */
function CitationSources({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-4 border-t pt-3">
      <p className="text-xs font-medium text-muted-foreground mb-2">
        Sources · {citations.length}
      </p>
      <div className="flex flex-col gap-1">
        {citations.map((c, i) => (
          <a
            key={`${c.document_id}-${c.chunk_id ?? i}`}
            href={`/documents/${c.document_id}?page=${c.page_number ?? 1}`}
            target="_blank"
            rel="noreferrer"
            className="group/src flex items-center gap-2.5 rounded-md px-2 py-1.5 -mx-2 text-sm hover:bg-accent transition-colors"
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-muted text-[10px] font-semibold text-muted-foreground">
              {i + 1}
            </span>
            <span className="truncate font-medium text-foreground">{c.document_name}</span>
            {c.page_number ? (
              <span className="shrink-0 text-xs text-muted-foreground">p.{c.page_number}</span>
            ) : null}
            <ExternalLink className="ml-auto h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover/src:opacity-100" />
          </a>
        ))}
      </div>
    </div>
  );
}
