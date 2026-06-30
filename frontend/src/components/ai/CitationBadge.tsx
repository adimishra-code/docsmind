import React from 'react';
import { cn } from '@/utils';

interface CitationBadgeProps {
  id: string;
  onClick?: () => void;
  className?: string;
}

export function CitationBadge({ id, onClick, className }: CitationBadgeProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center justify-center h-4 min-w-4 px-1 mx-0.5",
        "text-[10px] font-bold rounded-sm cursor-pointer",
        "bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground",
        "transition-colors duration-200 align-super",
        className
      )}
      title={`View citation ${id}`}
      aria-label={`Citation ${id}`}
    >
      {id}
    </button>
  );
}
