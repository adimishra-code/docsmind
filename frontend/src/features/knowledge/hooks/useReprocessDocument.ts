import { useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/services/documentsApi';
import { toast } from '@/components/ui/use-toast';

/**
 * Re-queues a document for ingestion (used to recover from a failed upload).
 * Invalidates the document list and the single-document view so the UI reflects
 * the reset "pending" status immediately.
 */
export function useReprocessDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.reprocess(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', id] });
      toast({
        title: 'Re-processing started',
        description: 'The document was re-queued for ingestion.',
      });
    },
    onError: () =>
      toast({
        title: 'Retry failed',
        variant: 'destructive',
        description: 'Could not re-queue the document. Please try again.',
      }),
  });
}
