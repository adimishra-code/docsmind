import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '@/services/documentsApi';
import { MetadataCard } from '@/components/documents/MetadataCard';
import { Skeleton } from '@/components/ui/skeleton';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from '@/components/ui/context-menu';

export function KnowledgeGrid() {
  const searchQuery = useWorkspaceStore((state) => state.searchQuery);
  const toggleSelection = useWorkspaceStore((state) => state.toggleDocumentSelection);
  const selectedIds = useWorkspaceStore((state) => state.selectedDocumentIds);

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents', searchQuery],
    queryFn: () => documentsApi.getAll({ q: searchQuery }),
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} className="h-32 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (!documents?.length) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <h3 className="text-lg font-medium">No knowledge found</h3>
        <p className="text-muted-foreground text-sm mt-1">Upload a document to get started or adjust your search.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {documents.map((doc) => (
        <ContextMenu key={doc.id}>
          <ContextMenuTrigger>
            <div 
              onClick={() => toggleSelection(doc.id)}
              className={`cursor-pointer transition-all duration-200 border-2 rounded-xl ${selectedIds.includes(doc.id) ? 'border-primary shadow-md' : 'border-transparent hover:border-muted-foreground/30'}`}
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
          <ContextMenuContent className="w-48">
            <ContextMenuItem onClick={() => window.open(`/documents/${doc.id}`, '_blank')}>
              Open Preview
            </ContextMenuItem>
            <ContextMenuItem>Rename...</ContextMenuItem>
            <ContextMenuItem>Pin to Top</ContextMenuItem>
            <ContextMenuItem>Add to Favorites</ContextMenuItem>
            <ContextMenuItem className="text-destructive">Delete</ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      ))}
    </div>
  );
}
