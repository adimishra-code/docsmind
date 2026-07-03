import { api } from './api';

/**
 * Document lifecycle statuses.
 *
 * The backend worker (app/workers/tasks.py) is the source of truth and emits:
 *   pending → processing → completed | failed
 *
 * `uploading` is a client-only state used while bytes are in flight, before the
 * server has acknowledged the document. Older aspirational values are tolerated
 * so the UI never breaks if the backend vocabulary is extended.
 */
export type DocumentStatus =
  | 'pending'
  | 'uploading'
  | 'queued'
  | 'processing'
  | 'parsing'
  | 'embedding'
  | 'completed'
  | 'ready'
  | 'failed';

export interface DocumentMetadata {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  checksum?: string;
  chunk_count?: number;
  error_message?: string;
}

/** Terminal success — the document is fully indexed and ready to use. */
export function isDocumentReady(status: string): boolean {
  return status === 'completed' || status === 'ready';
}

/** Terminal failure. */
export function isDocumentFailed(status: string): boolean {
  return status === 'failed';
}

/** Still in the ingestion pipeline (not yet terminal). */
export function isDocumentProcessing(status: string): boolean {
  return !isDocumentReady(status) && !isDocumentFailed(status);
}

/** Badge variant for a document status. */
export function documentStatusVariant(status: string): 'default' | 'secondary' | 'destructive' {
  if (isDocumentReady(status)) return 'default';
  if (isDocumentFailed(status)) return 'destructive';
  return 'secondary';
}

/** Human-facing label — normalizes the backend's "completed" to "Ready". */
export function documentStatusLabel(status: string): string {
  if (isDocumentReady(status)) return 'Ready';
  if (isDocumentProcessing(status)) return 'Processing';
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export interface DocumentListResponse {
  items: DocumentMetadata[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const documentsApi = {
  getAll: async (params?: { q?: string; skip?: number; limit?: number }): Promise<DocumentListResponse> => {
    const response = await api.get<DocumentListResponse>('/api/v1/documents', { params });
    return response.data;
  },

  getById: async (id: string): Promise<DocumentMetadata> => {
    const response = await api.get<DocumentMetadata>(`/api/v1/documents/${id}`);
    return response.data;
  },

  getStatus: async (id: string): Promise<DocumentMetadata> => {
    const response = await api.get<DocumentMetadata>(`/api/v1/documents/${id}/status`);
    return response.data;
  },

  reprocess: async (id: string): Promise<DocumentMetadata> => {
    const response = await api.post<DocumentMetadata>(`/api/v1/documents/${id}/reprocess`);
    return response.data;
  },

  upload: async (file: File, onUploadProgress?: (progressEvent: any) => void): Promise<DocumentMetadata> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<DocumentMetadata>('/api/v1/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/documents/${id}`);
  },

  rename: async (id: string, newName: string): Promise<DocumentMetadata> => {
    const { data } = await api.patch<DocumentMetadata>(`/api/v1/documents/${id}`, { filename: newName });
    return data;
  },

  download: async (id: string, filename: string): Promise<void> => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8006';
    const { useAuthStore } = await import('@/store/useAuthStore');
    const token = useAuthStore.getState().accessToken;
    const response = await fetch(`${baseUrl}/api/v1/documents/${id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error('Download failed');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};
