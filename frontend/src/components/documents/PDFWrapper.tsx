import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/utils';
import type { FitMode } from '@/store/useViewerStore';
import { buildHighlightMatcher, escapeHtml } from '@/features/viewer/highlightMatch';

import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

// Configure worker for react-pdf
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PDFWrapperProps {
  url: string;
  pageNumber?: number;
  onLoadSuccess?: (numPages: number) => void;
  className?: string;
  /** Cited passage to highlight in the rendered text layer (if present). */
  highlight?: string | null;
  fitMode?: FitMode;
  zoomLevel?: number;
  /** Available canvas size, used for fit-width / fit-page sizing. */
  containerWidth?: number;
  containerHeight?: number;
}

export function PDFWrapper({
  url,
  pageNumber = 1,
  onLoadSuccess,
  className,
  highlight,
  fitMode = 'width',
  zoomLevel = 1,
  containerWidth = 0,
  containerHeight = 0,
}: PDFWrapperProps) {
  const [loading, setLoading] = useState(true);
  const rootRef = useRef<HTMLDivElement>(null);

  const handleLoadSuccess = ({ numPages }: { numPages: number }) => {
    setLoading(false);
    onLoadSuccess?.(numPages);
  };

  // Size the page: fit-width uses the container width, fit-page uses its height,
  // and "actual" renders at the chosen zoom scale. Only pass one dimension so
  // react-pdf keeps the page's true aspect ratio (crisp — no CSS transform).
  const sizeProps = useMemo(() => {
    if (fitMode === 'width' && containerWidth > 0) return { width: containerWidth };
    if (fitMode === 'page' && containerHeight > 0) return { height: containerHeight };
    if (fitMode === 'actual') return { scale: zoomLevel };
    return { scale: 1 };
  }, [fitMode, containerWidth, containerHeight, zoomLevel]);

  // Highlight the cited passage by marking matching text-layer items. Returning
  // escaped HTML keeps the layer safe; a no-op matcher returns the plain text.
  const match = useMemo(() => buildHighlightMatcher(highlight), [highlight]);
  const customTextRenderer = useCallback(
    ({ str }: { str: string }) =>
      match(str) ? `<mark class="rag-highlight">${escapeHtml(str)}</mark>` : escapeHtml(str),
    [match],
  );

  // Once the text layer is drawn, scroll the first highlight into view so the
  // cited passage is centered without the user hunting for it.
  const handleTextLayerRender = useCallback(() => {
    if (!highlight) return;
    // Defer to the next frame so layout is settled before we measure/scroll.
    requestAnimationFrame(() => {
      rootRef.current?.querySelector('.rag-highlight')?.scrollIntoView({
        block: 'center',
        behavior: 'smooth',
      });
    });
  }, [highlight]);

  return (
    <div ref={rootRef} className={cn('relative flex items-start justify-center', className)}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background">
          <Skeleton className="w-[80%] h-[90%] rounded-md" />
        </div>
      )}
      <Document
        file={url}
        onLoadSuccess={handleLoadSuccess}
        className="flex justify-center"
        loading={<Skeleton className="w-[600px] h-[800px]" />}
      >
        <Page
          // Remount on page / fit-mode / highlight change (so the text layer
          // re-renders and re-scrolls to the passage), but NOT on plain resize —
          // react-pdf re-renders width changes in place, keeping resizing smooth.
          key={`${pageNumber}-${fitMode}-${highlight ? highlight.slice(0, 24) : 'x'}`}
          pageNumber={pageNumber}
          renderTextLayer
          renderAnnotationLayer
          customTextRenderer={highlight ? customTextRenderer : undefined}
          onRenderTextLayerSuccess={handleTextLayerRender}
          className="bg-white shadow-xl rounded-sm overflow-hidden"
          {...sizeProps}
        />
      </Document>
    </div>
  );
}
