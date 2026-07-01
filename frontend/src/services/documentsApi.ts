import { api } from './api';

export interface DocumentMetadata {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: 'queued' | 'uploading' | 'processing' | 'parsing' | 'embedding' | 'ready' | 'failed';
  created_at: string;
  updated_at: string;
  checksum?: string;
  chunk_count?: number;
  error_message?: string;
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
