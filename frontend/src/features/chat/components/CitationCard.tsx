import React from 'react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { FileText, ExternalLink } from 'lucide-react';

export interface CitationProps {
  citation: {
    document_id: string;
    document_name: string;
    page_number?: number;
    chunk_id?: string;
    confidence_score?: number;
    supporting_excerpt?: string;
  };
  index: number;
}

/** Inline citation badge — rendered inside the answer text for each [N] marker.
 *  Hover shows the document and exact supporting excerpt used.
 *  Clicking deep-links to the relevant page in the document viewer. */
export function CitationCard({ citation, index }: CitationProps) {
  const handleOpenCitation = (e: React.MouseEvent) => {
    e.stopPropagation();
    const params = new URLSearchParams({ page: String(citation.page_number || 1) });
    if (citation.supporting_excerpt) params.set('highlight', citation.supporting_excerpt);
    window.open(`/documents/${citation.document_id}?${params.toString()}`, '_blank');
  };

  const cleanExcerpt = citation.supporting_excerpt
    ?.replace(/^\[Document:[^\]]+\]\s*/i, '')
    .trim();

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={handleOpenCitation}
            aria-label={`View source ${index}: ${citation.document_name}`}
            className="
              inline-flex items-center justify-center align-middle
              mx-0.5 h-[18px] min-w-[18px] px-1.5
              rounded-[4px] border border-primary/30
              bg-primary/15 hover:bg-primary/25
              text-[10px] font-bold text-primary
              transition-colors duration-100
              cursor-pointer select-none
              shadow-sm hover:shadow
            "
          >
            {index}
          </button>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          align="center"
          className="max-w-xs sm:max-w-sm p-3 bg-popover text-popover-foreground border shadow-lg text-left"
        >
          <div className="flex items-center gap-1.5 font-semibold text-xs text-foreground mb-1">
            <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
            <span className="truncate">{citation.document_name}</span>
            {citation.page_number && (
              <span className="text-muted-foreground font-normal text-[11px] shrink-0">
                (p. {citation.page_number})
              </span>
            )}
            <ExternalLink className="h-3 w-3 ml-auto text-muted-foreground shrink-0" />
          </div>
          {cleanExcerpt && (
            <p className="text-[11px] text-muted-foreground line-clamp-3 italic bg-muted/50 p-1.5 rounded border border-border/50">
              "{cleanExcerpt}"
            </p>
          )}
          <span className="text-[9px] text-primary/80 mt-1 block font-medium">Click to open source page ↗</span>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
