import React from 'react';
import { FileText, ArrowUpRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

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

export function CitationCard({ citation, index }: CitationProps) {
  const handleOpenCitation = () => {
    // Navigate to the Knowledge Engine view for this document,
    // ideally appending a hash or query param to auto-scroll to the page/chunk
    window.open(`/documents/${citation.document_id}?page=${citation.page_number || 1}`, '_blank');
  };

  return (
    <span className="inline-flex items-center align-middle mx-1">
      <Button 
        variant="outline" 
        size="sm" 
        onClick={handleOpenCitation}
        className="h-5 px-1.5 py-0 text-[10px] font-bold rounded bg-muted/50 hover:bg-primary/10 hover:text-primary transition-colors border-muted-foreground/30"
        title={`${citation.document_name} (Page ${citation.page_number || '?'})`}
      >
        <span className="text-primary">{index}</span>
      </Button>
    </span>
  );
}
