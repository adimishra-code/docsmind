import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import {
  DocumentMetadata, documentsApi, documentStatusLabel, isDocumentReady,
} from '@/services/documentsApi';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { format } from 'date-fns';
import { formatBytes, estimateReadingTime } from '@/utils';
import {
  Info, FileText, Layers, Hash, Clock, Languages, ScanText, Table2, Sparkles,
  Tags, Users, FileStack, ArrowUpRight,
} from 'lucide-react';

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English', es: 'Spanish', fr: 'French', de: 'German', it: 'Italian',
  pt: 'Portuguese', nl: 'Dutch', hi: 'Hindi', zh: 'Chinese', ja: 'Japanese',
  ko: 'Korean', ru: 'Russian', ar: 'Arabic',
};

function languageLabel(code?: string): string | null {
  if (!code) return null;
  const key = code.trim().toLowerCase();
  return LANGUAGE_NAMES[key] ?? code.toUpperCase();
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="font-medium text-right truncate">{value}</span>
    </div>
  );
}

function SectionHeader({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
      {icon} {children}
    </h3>
  );
}

function Chips({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((t) => (
        <span key={t} className="rounded-full border bg-muted/50 px-2 py-0.5 text-xs text-foreground/80">
          {t}
        </span>
      ))}
    </div>
  );
}

/** AI-generated insights — lazy, cached server-side; shown only when real. */
function IntelligenceSection({ documentId, fallbackKeywords }: { documentId: string; fallbackKeywords: string[] }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['doc-insights', documentId],
    queryFn: () => documentsApi.getInsights(documentId),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <section>
        <SectionHeader icon={<Sparkles className="h-3 w-3" />}>Intelligence</SectionHeader>
        <p className="text-xs text-muted-foreground mb-2">Analyzing document…</p>
        <div className="space-y-1.5">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-[85%]" />
          <Skeleton className="h-3 w-[60%]" />
        </div>
      </section>
    );
  }

  const available = !isError && data?.available;
  const topics = data?.topics ?? [];
  const entities = data?.entities ?? [];

  // Nothing real to show → fall back to heuristic keywords (also real) or hide.
  if (!available || (!data?.summary && topics.length === 0 && entities.length === 0)) {
    if (fallbackKeywords.length === 0) return null;
    return (
      <section>
        <SectionHeader icon={<Hash className="h-3 w-3" />}>Keywords</SectionHeader>
        <Chips items={fallbackKeywords} />
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div>
        <SectionHeader icon={<Sparkles className="h-3 w-3" />}>Summary</SectionHeader>
        {data?.summary
          ? <p className="text-sm leading-relaxed text-foreground/90">{data.summary}</p>
          : <p className="text-xs text-muted-foreground">No summary available.</p>}
      </div>
      {topics.length > 0 && (
        <div>
          <SectionHeader icon={<Tags className="h-3 w-3" />}>Topics</SectionHeader>
          <Chips items={topics} />
        </div>
      )}
      {entities.length > 0 && (
        <div>
          <SectionHeader icon={<Users className="h-3 w-3" />}>Entities</SectionHeader>
          <Chips items={entities} />
        </div>
      )}
    </section>
  );
}

/** Semantically similar documents (real embedding similarity), click to open. */
function RelatedSection({ documentId }: { documentId: string }) {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['doc-related', documentId],
    queryFn: () => documentsApi.getRelated(documentId),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  if (isLoading) {
    return (
      <section>
        <SectionHeader icon={<FileStack className="h-3 w-3" />}>Related documents</SectionHeader>
        <div className="space-y-1.5">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </section>
    );
  }

  if (!data || data.length === 0) return null;

  return (
    <section>
      <SectionHeader icon={<FileStack className="h-3 w-3" />}>Related documents</SectionHeader>
      <div className="flex flex-col gap-1">
        {data.map((r) => (
          <button
            key={r.document_id}
            onClick={() => navigate(`/documents/${r.document_id}`)}
            className="group flex items-center gap-2.5 rounded-md px-2 py-1.5 -mx-2 text-left text-sm hover:bg-accent transition-colors"
          >
            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate font-medium text-foreground flex-1">{r.filename}</span>
            <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
              {Math.round(Math.max(0, Math.min(1, r.similarity)) * 100)}%
            </span>
            <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </button>
        ))}
      </div>
    </section>
  );
}

export function MetadataPanel({ document }: { document: DocumentMetadata }) {
  const meta = document.doc_metadata ?? {};
  const language = languageLabel(meta.language);
  const pages = typeof meta.pages === 'number' && meta.pages > 0 ? meta.pages : null;
  const headingsCount = Array.isArray(meta.headings) ? meta.headings.length : 0;
  const tablesCount = Array.isArray(meta.tables) ? meta.tables.length : 0;
  const keywords = (meta.keywords ?? []).filter((k) => k && k.trim().length > 1);
  const readingMinutes = estimateReadingTime({ pages, chunkCount: document.chunk_count });
  const ready = isDocumentReady(document.status);

  const title = meta.title && meta.title.trim() && meta.title.trim() !== document.filename ? meta.title.trim() : null;

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b font-semibold flex items-center gap-2 text-sm">
        <Info className="h-4 w-4" /> Document Intelligence
      </div>
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6 text-sm">
          <section>
            <SectionHeader icon={<FileText className="h-3 w-3" />}>General</SectionHeader>
            <div className="space-y-0.5">
              <Row label="Title" value={title} />
              <Row label="Filename" value={<span className="truncate max-w-[160px] inline-block align-bottom">{document.filename}</span>} />
              <Row label="Type" value={<span className="uppercase">{document.file_type}</span>} />
              <Row label="Size" value={formatBytes(document.file_size)} />
              <Row label="Uploaded" value={format(new Date(document.created_at), 'PP')} />
              {language && <Row label="Language" value={<span className="inline-flex items-center gap-1"><Languages className="h-3 w-3 text-muted-foreground" />{language}</span>} />}
            </div>
          </section>

          <section>
            <SectionHeader icon={<Layers className="h-3 w-3" />}>Content</SectionHeader>
            <div className="space-y-0.5">
              <Row label="Pages" value={pages} />
              <Row label="Chunks" value={typeof document.chunk_count === 'number' ? document.chunk_count : null} />
              <Row label="Headings" value={headingsCount > 0 ? headingsCount : null} />
              <Row label="Tables" value={tablesCount > 0 ? <span className="inline-flex items-center gap-1"><Table2 className="h-3 w-3 text-muted-foreground" />{tablesCount}</span> : null} />
              <Row label="Reading time" value={readingMinutes ? <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3 text-muted-foreground" />~{readingMinutes} min</span> : null} />
              {meta.ocr_applied && <Row label="OCR" value={<span className="inline-flex items-center gap-1"><ScanText className="h-3 w-3 text-muted-foreground" />Applied</span>} />}
            </div>
          </section>

          {/* Real AI insights + related docs — only rendered once the document is
              indexed, and each hides itself when there's nothing genuine to show. */}
          {ready && <IntelligenceSection documentId={document.id} fallbackKeywords={keywords} />}
          {ready && <RelatedSection documentId={document.id} />}

          <section>
            <SectionHeader icon={<Sparkles className="h-3 w-3" />}>Indexing</SectionHeader>
            <div className="space-y-0.5">
              <Row label="Status" value={documentStatusLabel(document.status)} />
              <Row
                label="Embeddings"
                value={<span className={ready ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}>{ready ? 'Indexed' : 'Pending'}</span>}
              />
            </div>
          </section>
        </div>
      </ScrollArea>
    </div>
  );
}
