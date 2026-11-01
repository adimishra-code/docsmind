import React from 'react';
import type { Message, MessageMeta } from '@/services/chatApi';

/**
 * Compact grounding strip shown under every grounded assistant reply.
 * Renders only when real data is present — never fabricates values.
 * Deliberately omits chunk count and raw token count as those are
 * technical internals; the strip stays scannable at a glance.
 */

interface Citation {
  document_id?: string;
  document_name?: string;
  page_number?: number | null;
}

function confidenceLabel(c: number): { text: string; color: string } {
  if (c >= 0.75) return { text: 'High confidence', color: 'text-success' };
  if (c >= 0.5)  return { text: 'Medium confidence', color: 'text-warning' };
  return           { text: 'Low confidence', color: 'text-destructive' };
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function Dot() {
  return <span className="text-border/60 select-none" aria-hidden>·</span>;
}

export function ResponseMeta({ message }: { message: Message }) {
  const meta: MessageMeta = message.meta ?? {};
  const citations = (message.citations as Citation[] | undefined) ?? [];

  const docIds = new Set(citations.map((c) => c.document_id).filter(Boolean));

  // Only show for grounded answers; keeps small-talk replies clean.
  if (docIds.size === 0) return null;

  const pages = Array.from(
    new Set(
      citations
        .map((c) => c.page_number)
        .filter((p): p is number => typeof p === 'number' && p > 0),
    ),
  ).sort((a, b) => a - b);

  const modelLabel =
    meta.provider === 'local'   ? 'Local model'
    : meta.provider === 'ollama' ? 'Ollama'
    : meta.model                 ? meta.model
    : null;

  const items: React.ReactNode[] = [];

  // Document count
  items.push(
    <span key="docs">
      {docIds.size === 1
        ? 'Grounded in 1 document'
        : `Grounded in ${docIds.size} documents`}
    </span>,
  );

  // Page references
  if (pages.length > 0) {
    items.push(
      <span key="pages">
        {pages.length === 1 ? 'p.' : 'pp.'} {pages.join(', ')}
      </span>,
    );
  }

  // Confidence — with a muted color hint so it reads as a quality signal
  if (typeof meta.confidence === 'number') {
    const { text, color } = confidenceLabel(meta.confidence);
    items.push(
      <span key="conf" className={color}>
        {text}
      </span>,
    );
  }

  // Generation time
  const displayMs = typeof meta.totalMs === 'number'  ? meta.totalMs
    : typeof meta.latencyMs === 'number' ? meta.latencyMs
    : undefined;
  if (typeof displayMs === 'number') {
    items.push(
      <span
        key="time"
        title={meta.ttftMs != null ? `${formatDuration(meta.ttftMs)} to first token` : undefined}
      >
        {formatDuration(displayMs)}
      </span>,
    );
  }

  // Cache badge — only when answer was served from cache
  if (meta.cached) {
    items.push(
      <span key="cached" className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide">
        cached
      </span>,
    );
  }

  // Model / provider label
  if (modelLabel) {
    items.push(<span key="model" className="font-medium">{modelLabel}</span>);
  }

  if (items.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] leading-none text-muted-foreground/70">
      {items.map((item, i) => (
        <React.Fragment key={i}>
          {i > 0 && <Dot />}
          {item}
        </React.Fragment>
      ))}
    </div>
  );
}
