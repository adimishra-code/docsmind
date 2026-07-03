import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { documentStatusLabel, documentStatusVariant } from '@/services/documentsApi';

interface MetadataCardProps {
  filename: string;
  fileType: string;
  sizeBytes: number;
  createdAt: string;
  status: string;
  className?: string;
}

export function MetadataCard({ filename, fileType, sizeBytes, createdAt, status, className }: MetadataCardProps) {
  const sizeMb = (sizeBytes / (1024 * 1024)).toFixed(2);
  const dateFormatted = format(new Date(createdAt), 'PPP');

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-medium break-all">{filename}</CardTitle>
        <div className="flex space-x-2 mt-2">
          <Badge variant={documentStatusVariant(status)}>
            {documentStatusLabel(status).toUpperCase()}
          </Badge>
          <Badge variant="outline">{fileType.toUpperCase()}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground mt-4">
          <div>Size</div>
          <div className="text-right font-medium text-foreground">{sizeMb} MB</div>
          
          <div>Uploaded</div>
          <div className="text-right font-medium text-foreground">{dateFormatted}</div>
        </div>
      </CardContent>
    </Card>
  );
}
