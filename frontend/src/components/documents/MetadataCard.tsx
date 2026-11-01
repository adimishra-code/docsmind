import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { FileText, FileSpreadsheet, FileCode, FileImage, Loader2 } from 'lucide-react';
import { cn, formatBytes } from '@/utils';
import { documentStatusLabel, documentStatusVariant, isDocumentProcessing } from '@/services/documentsApi';

interface MetadataCardProps {
  filename: string;
  fileType: string;
  sizeBytes: number;
  createdAt: string;
  status: string;
  className?: string;
}

/** Map file extension to an icon + accent colour. */
function fileTypeIcon(type: string): { Icon: React.ElementType; bg: string; fg: string } {
  const t = (type || '').toLowerCase();
  if (t === 'pdf')  return { Icon: FileText,        bg: 'bg-red-50    dark:bg-red-950/30',    fg: 'text-red-500' };
  if (t === 'csv' || t === 'xlsx' || t === 'xls')
                    return { Icon: FileSpreadsheet,  bg: 'bg-emerald-50 dark:bg-emerald-950/30', fg: 'text-emerald-600' };
  if (t === 'md' || t === 'mdx' || t === 'txt')
                    return { Icon: FileCode,         bg: 'bg-violet-50  dark:bg-violet-950/30', fg: 'text-violet-500' };
  if (t === 'png' || t === 'jpg' || t === 'jpeg' || t === 'webp')
                    return { Icon: FileImage,        bg: 'bg-sky-50     dark:bg-sky-950/30',   fg: 'text-sky-500' };
  return { Icon: FileText, bg: 'bg-muted', fg: 'text-muted-foreground' };
}

export function MetadataCard({
  filename,
  fileType,
  sizeBytes,
  createdAt,
  status,
  className,
}: MetadataCardProps) {
  const size = formatBytes(sizeBytes);
  const processing = isDocumentProcessing(status);
  const { Icon, bg, fg } = fileTypeIcon(fileType);

  let dateLabel = '';
  try {
    dateLabel = format(new Date(createdAt), 'MMM d, yyyy');
  } catch {
    dateLabel = '—';
  }

  return (
    <Card className={cn('flex flex-col gap-3 p-4 rounded-xl', className)}>
      {/* Icon + name row */}
      <div className="flex items-start gap-3">
        <div className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
          bg,
        )}>
          <Icon className={cn('h-4.5 w-4.5', fg)} />
        </div>
        <div className="min-w-0 flex-1 pt-0.5">
          <p
            className="truncate text-[13px] font-medium leading-snug text-foreground"
            title={filename}
          >
            {filename}
          </p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground/70">
            {fileType || 'file'}
          </p>
        </div>
      </div>

      {/* Status + size/date row */}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <Badge variant={documentStatusVariant(status)} className="gap-1 text-[10px] px-1.5 py-0.5">
          {processing && <Loader2 className="h-2.5 w-2.5 animate-spin" />}
          {documentStatusLabel(status)}
        </Badge>
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground tabular-nums">
          <span>{size}</span>
          <span className="text-border select-none">·</span>
          <span>{dateLabel}</span>
        </div>
      </div>
    </Card>
  );
}
