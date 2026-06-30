import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { documentsApi, DocumentMetadata } from '@/services/documentsApi';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { Checkbox } from '@/components/ui/checkbox';

export function KnowledgeList() {
  const searchQuery = useWorkspaceStore((state) => state.searchQuery);
  const toggleSelection = useWorkspaceStore((state) => state.toggleDocumentSelection);
  const selectedIds = useWorkspaceStore((state) => state.selectedDocumentIds);

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', searchQuery],
    queryFn: () => documentsApi.getAll({ q: searchQuery }),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="border rounded-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12 text-center"></TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Size</TableHead>
            <TableHead className="text-right">Uploaded</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents?.map((doc: DocumentMetadata) => (
            <TableRow key={doc.id} className="cursor-pointer" onClick={() => toggleSelection(doc.id)}>
              <TableCell className="text-center">
                <Checkbox 
                  checked={selectedIds.includes(doc.id)} 
                  onCheckedChange={() => toggleSelection(doc.id)}
                />
              </TableCell>
              <TableCell className="font-medium">{doc.filename}</TableCell>
              <TableCell>
                <Badge variant={doc.status === 'ready' ? 'default' : doc.status === 'failed' ? 'destructive' : 'secondary'}>
                  {doc.status.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="uppercase text-xs">{doc.file_type}</TableCell>
              <TableCell>{(doc.size_bytes / (1024 * 1024)).toFixed(2)} MB</TableCell>
              <TableCell className="text-right">{format(new Date(doc.created_at), 'MMM d, yyyy')}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
