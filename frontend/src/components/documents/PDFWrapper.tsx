import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/utils';

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
}

export function PDFWrapper({ url, pageNumber = 1, onLoadSuccess, className }: PDFWrapperProps) {
  const [loading, setLoading] = useState(true);

  const handleLoadSuccess = ({ numPages }: { numPages: number }) => {
    setLoading(false);
    onLoadSuccess?.(numPages);
  };

  return (
    <div className={cn("relative flex items-center justify-center bg-muted/30 rounded-lg overflow-hidden border", className)}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background">
          <Skeleton className="w-[80%] h-[90%] rounded-md" />
        </div>
      )}
      <Document
        file={url}
        onLoadSuccess={handleLoadSuccess}
        className="flex justify-center shadow-lg"
        loading={<Skeleton className="w-[600px] h-[800px]" />}
      >
        <Page
          pageNumber={pageNumber}
          renderTextLayer={true}
          renderAnnotationLayer={true}
          className="bg-white"
        />
      </Document>
    </div>
  );
}
