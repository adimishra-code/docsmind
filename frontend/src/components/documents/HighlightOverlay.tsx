import React from 'react';
import { cn } from '@/utils';

interface HighlightOverlayProps {
  rects: { top: number; left: number; width: number; height: number }[];
  containerWidth: number;
  containerHeight: number;
  className?: string;
}

export function HighlightOverlay({ rects, containerWidth, containerHeight, className }: HighlightOverlayProps) {
  return (
    <div 
      className={cn("absolute top-0 left-0 pointer-events-none mix-blend-multiply", className)}
      style={{ width: containerWidth, height: containerHeight }}
    >
      {rects.map((rect, i) => (
        <div
          key={i}
          className="absolute bg-accent/40"
          style={{
            top: `${rect.top}%`,
            left: `${rect.left}%`,
            width: `${rect.width}%`,
            height: `${rect.height}%`,
          }}
        />
      ))}
    </div>
  );
}
