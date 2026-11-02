import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { Message } from '@/services/chatApi';
import { cn } from '@/utils';
import { Bot, User, Copy, Check, RefreshCw, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CitationCard, type CitationProps } from './CitationCard';
import { ResponseMeta } from './ResponseMeta';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  onRegenerate?: () => void;
}

type Citation = CitationProps['citation'];

export function MessageBubble({ message, isStreaming = false, onRegenerate }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const citations = (message.citations as Citation[] | undefined) ?? undefined;

  const renderedContent = useMemo(() => {
    let content = message.content;
    if (citations?.length) {
      content = content.replace(/\[(\d+)\](?!\()/g, (match, digits) => {
        const digitNum = Number(digits);
        const exists = citations.some((c: any) =>
          c.citation_index === digitNum || c.index === digitNum
        ) || (digitNum >= 1 && digitNum <= citations.length);
        return exists ? `[${digits}](#cite-${digits})` : match;
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
      // Clipboard unavailable — silently no-op.
    }
  };

  const showActions = !isUser && !isStreaming && message.content.length > 0;
  const showSources = !isUser && !isStreaming && !!citations?.length;

  return (
    <div className={cn(
      "group flex w-full py-5",
      // User messages: clean white card stands out from the warm page background.
      // Assistant messages: warm muted band provides visual rhythm and anchors the answer.
      isUser ? "bg-card/80" : "bg-muted/40",
    )}>
      <div className="max-w-3xl mx-auto w-full flex gap-3 sm:gap-4 px-3 sm:px-4">
        {/* Avatar */}
        <div className="flex-shrink-0 mt-0.5">
          {isUser ? (
            <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center text-primary-foreground ring-2 ring-primary/10">
              <User className="h-4 w-4" />
            </div>
          ) : (
            <div className="h-7 w-7 rounded-md bg-secondary border border-border flex items-center justify-center text-secondary-foreground">
              <Bot className="h-4 w-4" />
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          {/* Role label */}
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1.5 select-none">
            {isUser ? 'You' : 'DocsMind'}
          </p>

          {/* Content — prose-sm keeps chat-appropriate 14px base text */}
          <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none leading-relaxed break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={{
                a: ({ node: _node, href, ...props }) => {
                  if (href?.startsWith('#cite-') && citations) {
                    const citeNum = parseInt(href.slice('#cite-'.length), 10);
                    const citation = citations.find((c: any) =>
                      c.citation_index === citeNum || c.index === citeNum
                    ) || citations[citeNum - 1];
                    if (citation) {
                      return <CitationCard citation={citation} index={citeNum} />;
                    }
                  }
                  return (
                    <a
                      {...props}
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary hover:underline"
                    />
                  );
                },
              }}
            >
              {renderedContent}
            </ReactMarkdown>
          </div>

          {/* Grounding metadata strip — only for grounded assistant replies */}
          {!isUser && !isStreaming && <ResponseMeta message={message} />}

          {/* Sources bibliography */}
          {showSources && <CitationSources citations={citations!} />}

          {/* Copy / Regenerate actions */}
          {showActions && (
            <div className="mt-2 flex items-center gap-1 opacity-100 sm:opacity-0 transition-opacity duration-150 sm:group-hover:opacity-100 focus-within:opacity-100">
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

/** Compress a sorted list of unique page numbers into ranges. */
export function formatPageRanges(pages: number[]): string {
  if (pages.length === 0) return '';
  const sorted = [...new Set(pages)].sort((a, b) => a - b);
  const parts: string[] = [];
  let start = sorted[0];
  let prev = sorted[0];
  for (let i = 1; i <= sorted.length; i++) {
    const cur = sorted[i];
    if (cur === prev + 1) { prev = cur; continue; }
    parts.push(start === prev ? `${start}` : `${start}–${prev}`);
    start = cur; prev = cur;
  }
  return parts.join(', ');
}

interface GroupedSource {
  documentId?: string;
  documentName: string;
  pages: number[];
  firstIndex: number;
  excerpt?: string;
}

export function groupCitations(citations: Citation[]): GroupedSource[] {
  const byDoc = new Map<string, GroupedSource>();
  citations.forEach((c, i) => {
    const key = c.document_id ?? c.document_name ?? String(i);
    const existing = byDoc.get(key);
    const page = typeof c.page_number === 'number' && c.page_number > 0 ? c.page_number : undefined;
    if (existing) {
      if (page) existing.pages.push(page);
      if (!existing.excerpt && c.supporting_excerpt) existing.excerpt = c.supporting_excerpt;
    } else {
      byDoc.set(key, {
        documentId: c.document_id,
        documentName: c.document_name ?? 'Untitled document',
        pages: page ? [page] : [],
        firstIndex: i,
        excerpt: c.supporting_excerpt,
      });
    }
  });
  return [...byDoc.values()].sort((a, b) => a.firstIndex - b.firstIndex);
}

function CitationSources({ citations }: { citations: Citation[] }) {
  const [expanded, setExpanded] = useState(false);
  const visibleCitations = expanded ? citations : citations.slice(0, 3);

  return (
    <div className="mt-4 border-t border-border/60 pt-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] font-semibold text-muted-foreground/80 uppercase tracking-wider">
          {citations.length === 1 ? '1 Cited Source' : `${citations.length} Cited Sources`}
        </p>
        {citations.length > 3 && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-primary hover:underline font-medium cursor-pointer"
          >
            {expanded ? 'Show fewer' : `Show all ${citations.length} sources`}
          </button>
        )}
      </div>

      <div className="space-y-2">
        {visibleCitations.map((c, i) => {
          const excerpt = c.supporting_excerpt
            ?.replace(/^\[Document:[^\]]+\]\s*/i, '')
            .trim();
          const params = new URLSearchParams({ page: String(c.page_number || 1) });
          if (excerpt) params.set('highlight', excerpt);
          const badgeNum = (c as any).citation_index ?? (c as any).index ?? (i + 1);

          return (
            <div
              key={`${c.document_id || c.document_name}-${badgeNum}-${i}`}
              className="group/src rounded-lg border border-border/60 bg-card/50 p-2.5 text-xs transition-colors hover:border-primary/40 hover:bg-card"
            >
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary/15 text-[10px] font-bold text-primary">
                  {badgeNum}
                </span>
                <a
                  href={`/documents/${c.document_id}?${params.toString()}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-foreground hover:text-primary hover:underline flex items-center gap-1 truncate"
                >
                  <span className="truncate">{c.document_name}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 opacity-70" />
                </a>
                {c.page_number ? (
                  <span className="text-[11px] text-muted-foreground shrink-0 ml-auto">
                    p. {c.page_number}
                  </span>
                ) : null}
              </div>
              {excerpt ? (
                <div className="text-muted-foreground pl-7 text-[11px] leading-relaxed line-clamp-3 italic border-l-2 border-primary/40 ml-2 mt-1.5 pt-0.5">
                  "{excerpt}"
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
