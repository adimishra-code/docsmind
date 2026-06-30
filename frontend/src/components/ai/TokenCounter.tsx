import React from 'react';
import { cn } from '@/utils';

interface TokenCounterProps {
  count: number;
  limit?: number;
  className?: string;
}

export function TokenCounter({ count, limit = 4096, className }: TokenCounterProps) {
  const percentage = (count / limit) * 100;
  
  let statusClass = "text-muted-foreground";
  if (percentage > 90) statusClass = "text-destructive";
  else if (percentage > 75) statusClass = "text-warning";

  return (
    <div className={cn("flex items-center space-x-2 text-xs", statusClass, className)}>
      <span>{count.toLocaleString()} / {limit.toLocaleString()} tokens</span>
    </div>
  );
}
