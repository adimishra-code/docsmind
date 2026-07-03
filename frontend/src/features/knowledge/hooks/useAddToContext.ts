import { useContextStore } from '@/store/useContextStore';
import type { DocumentMetadata } from '@/services/documentsApi';
import { toast } from '@/components/ui/use-toast';

/**
 * Pins a document into the chat Context panel so that subsequent chat
 * questions are scoped (grounded) to it. Shared by the grid and list views.
 */
export function useAddToContext() {
  const pinDocument = useContextStore((s) => s.pinDocument);
  const pinnedDocuments = useContextStore((s) => s.pinnedDocuments);
  const pinnedIds = new Set(pinnedDocuments.map((d) => d.id));

  const addToContext = (doc: DocumentMetadata) => {
    if (pinnedIds.has(doc.id)) return;
    pinDocument(doc);
    toast({
      title: 'Added to chat context',
      description: `“${doc.filename}” will be used to ground answers in Chat.`,
    });
  };

  return { addToContext, isPinned: (id: string) => pinnedIds.has(id) };
}
