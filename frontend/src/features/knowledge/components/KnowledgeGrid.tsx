import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { documentsApi, DocumentMetadata } from '@/services/documentsApi';
import { MetadataCard } from '@/components/documents/MetadataCard';
import { Skeleton } from '@/components/ui/skeleton';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { RenameDialog, DeleteDocumentDialog } from '@/components/documents/DocumentActionModal';
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from '@/components/ui/context-menu';
import { Eye, Download, Pencil, Trash2, FileText } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';

export function KnowledgeGrid() {
  const searchQuery = useWorkspaceStore((state) => state.searchQuery);
  const toggleSelection = useWorkspaceStore((state) => state.toggleDocumentSelection);
  const selectedIds = useWorkspaceStore((state) => state.selectedDocumentIds);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [renameTarget, setRenameTarget] = useState<DocumentMetadata | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentMetadata | null>(null);

  const { data: response, isLoading, isError } = useQuery({
    queryKey: ['documents', searchQuery],
    queryFn: () => documentsApi.getAll({ q: searchQuery }),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => documentsApi.rename(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({ title: 'Document renamed', description: 'The document name has been updated.' });
    },
    onError: () => toast({ title: 'Rename failed', variant: 'destructive', description: 'Could not rename the document.' }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast({ title: 'Document deleted', description: 'The document has been removed.' });
    },
    onError: () => toast({ title: 'Delete failed', variant: 'destructive', description: 'Could not delete the document.' }),
  });

  const handleDownload = async (doc: DocumentMetadata) => {
    try {
      await documentsApi.download(doc.id, doc.filename);
    } catch {
      toast({ title: 'Download failed', variant: 'destructive', description: 'Could not download the file.' });
    }
  };

  const documents = response?.items ?? [];

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} className="h-32 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <FileText className="h-12 w-12 text-muted-foreground/40 mb-4" />
        <h3 className="text-lg font-medium">Failed to load documents</h3>
        <p className="text-muted-foreground text-sm mt-1">Please check your connection and try again.</p>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="h-16 w-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
          <FileText className="h-8 w-8 text-muted-foreground/50" />
        </div>
        <h3 className="text-lg font-medium">
          {searchQuery ? 'No results found' : 'No documents yet'}
        </h3>
        <p className="text-muted-foreground text-sm mt-1">
          {searchQuery ? 'Try a different search term.' : 'Upload a document to get started.'}
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {documents.map((doc) => (
          <ContextMenu key={doc.id}>
            <ContextMenuTrigger asChild>
              <div
                onClick={() => toggleSelection(doc.id)}
                className={`cursor-pointer transition-all duration-200 border-2 rounded-xl ${
                  selectedIds.includes(doc.id)
                    ? 'border-primary shadow-md ring-2 ring-primary/20'
                    : 'border-transparent hover:border-muted-foreground/30'
                }`}
                role="checkbox"
                aria-checked={selectedIds.includes(doc.id)}
                aria-label={`Select ${doc.filename}`}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && toggleSelection(doc.id)}
              >
                <MetadataCard
                  filename={doc.filename}
                  fileType={doc.file_type}
                  sizeBytes={doc.size_bytes}
                  createdAt={doc.created_at}
                  status={doc.status as any}
                  className="shadow-sm hover:shadow-md transition-shadow h-full"
                />
              </div>
            </ContextMenuTrigger>
            <ContextMenuContent className="w-52">
              <ContextMenuItem onClick={() => navigate(`/documents/${doc.id}`)}>
                <Eye className="mr-2 h-4 w-4" /> Open Preview
              </ContextMenuItem>
              <ContextMenuItem onClick={() => handleDownload(doc)}>
                <Download className="mr-2 h-4 w-4" /> Download
              </ContextMenuItem>
              <ContextMenuSeparator />
              <ContextMenuItem onClick={() => setRenameTarget(doc)}>
                <Pencil className="mr-2 h-4 w-4" /> Rename...
              </ContextMenuItem>
              <ContextMenuSeparator />
              <ContextMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => setDeleteTarget(doc)}
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </ContextMenuItem>
            </ContextMenuContent>
          </ContextMenu>
        ))}
      </div>

      {/* Rename Dialog */}
      <RenameDialog
        open={!!renameTarget}
        onOpenChange={(open) => !open && setRenameTarget(null)}
        currentName={renameTarget?.filename ?? ''}
        onRename={async (name) => {
          if (renameTarget) await renameMutation.mutateAsync({ id: renameTarget.id, name });
        }}
      />

      {/* Delete Dialog */}
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
