import React, { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { documentsApi, DocumentMetadata, isDocumentReady, isDocumentProcessing, isDocumentFailed, documentStatusLabel, documentStatusVariant } from '@/services/documentsApi';
import { useWorkspaceStore, sortDocuments } from '@/store/useWorkspaceStore';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { RenameDialog, DeleteDocumentDialog } from '@/components/documents/DocumentActionModal';
import { format } from 'date-fns';
import { formatBytes } from '@/utils';
import { MoreHorizontal, Eye, Download, Pencil, Trash2, FileText, MessageSquarePlus, RefreshCw } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';
import { useAddToContext } from '../hooks/useAddToContext';
import { useReprocessDocument } from '../hooks/useReprocessDocument';

export function KnowledgeList() {
  const searchQuery = useWorkspaceStore((state) => state.searchQuery);
  const toggleSelection = useWorkspaceStore((state) => state.toggleDocumentSelection);
  const selectedIds = useWorkspaceStore((state) => state.selectedDocumentIds);
  const sortKey = useWorkspaceStore((state) => state.sortKey);
  const sortDir = useWorkspaceStore((state) => state.sortDir);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [renameTarget, setRenameTarget] = useState<DocumentMetadata | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentMetadata | null>(null);
  const { addToContext, isPinned } = useAddToContext();
  const reprocess = useReprocessDocument();

  const { data: response, isLoading } = useQuery({
    queryKey: ['documents', searchQuery],
    queryFn: () => documentsApi.getAll({ q: searchQuery }),
    // Live-refresh while any document is still being ingested so its status
    // transitions to Ready/Failed without a manual reload.
    refetchInterval: (query) =>
      (query.state.data?.items ?? []).some((d) => isDocumentProcessing(d.status)) ? 4000 : false,
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => documentsApi.rename(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({ title: 'Document renamed' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({ title: 'Document deleted' });
    },
  });

  const documents = useMemo(
    () => sortDocuments(response?.items ?? [], sortKey, sortDir),
    [response?.items, sortKey, sortDir],
  );

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <FileText className="h-12 w-12 text-muted-foreground/40 mb-4" />
        <h3 className="text-lg font-medium">{searchQuery ? 'No results' : 'No documents yet'}</h3>
        <p className="text-muted-foreground text-sm mt-1">
          {searchQuery ? 'Try a different search term.' : 'Upload a document to get started.'}
        </p>
      </div>
    );
  }

  return (
    <>
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
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((doc: DocumentMetadata) => (
              <TableRow key={doc.id} className="cursor-pointer hover:bg-accent/50">
                <TableCell className="text-center" onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selectedIds.includes(doc.id)}
                    onCheckedChange={() => toggleSelection(doc.id)}
                    aria-label={`Select ${doc.filename}`}
                  />
                </TableCell>
                <TableCell className="font-medium" onClick={() => navigate(`/documents/${doc.id}`)}>
                  {doc.filename}
                </TableCell>
                <TableCell>
                  <Badge variant={documentStatusVariant(doc.status)}>
                    {documentStatusLabel(doc.status).toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="uppercase text-xs font-mono">{doc.file_type}</TableCell>
                <TableCell className="text-muted-foreground text-sm tabular-nums">{formatBytes(doc.file_size)}</TableCell>
                <TableCell className="text-right text-muted-foreground text-sm">
                  {(() => {
                    try {
                      return format(new Date(doc.created_at), 'MMM d, yyyy');
                    } catch {
                      return '—';
                    }
                  })()}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Document options">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-44">
                      <DropdownMenuItem onClick={() => navigate(`/documents/${doc.id}`)}>
                        <Eye className="mr-2 h-4 w-4" /> Open
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        disabled={!isDocumentReady(doc.status) || isPinned(doc.id)}
                        onClick={() => addToContext(doc)}
                      >
                        <MessageSquarePlus className="mr-2 h-4 w-4" />
                        {isPinned(doc.id) ? 'In chat context' : 'Add to chat context'}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => documentsApi.download(doc.id, doc.filename)}>
                        <Download className="mr-2 h-4 w-4" /> Download
                      </DropdownMenuItem>
                      {isDocumentFailed(doc.status) && (
                        <DropdownMenuItem
                          disabled={reprocess.isPending}
                          onClick={() => reprocess.mutate(doc.id)}
                        >
                          <RefreshCw className="mr-2 h-4 w-4" /> Retry processing
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => setRenameTarget(doc)}>
                        <Pencil className="mr-2 h-4 w-4" /> Rename...
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => setDeleteTarget(doc)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <RenameDialog
        open={!!renameTarget}
        onOpenChange={(open) => !open && setRenameTarget(null)}
        currentName={renameTarget?.filename ?? ''}
        onRename={async (name) => {
          if (renameTarget) await renameMutation.mutateAsync({ id: renameTarget.id, name });
        }}
      />

      <DeleteDocumentDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        filename={deleteTarget?.filename ?? ''}
        onDelete={async () => {
          if (deleteTarget) await deleteMutation.mutateAsync(deleteTarget.id);
        }}
      />
    </>
  );
}
