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

export const documentsApi = {
  getAll: async (params?: any): Promise<DocumentMetadata[]> => {
    // For now returning mock data or hitting actual backend
    const response = await api.get('/api/v1/documents', { params });
    return response.data;
  },

  getById: async (id: string): Promise<DocumentMetadata> => {
    const response = await api.get(`/api/v1/documents/${id}`);
    return response.data;
  },

  getStatus: async (id: string): Promise<{ status: string; progress: number }> => {
    const response = await api.get(`/api/v1/documents/${id}/status`);
    return response.data;
  },

  upload: async (file: File, onUploadProgress?: (progressEvent: any) => void): Promise<DocumentMetadata> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/v1/documents/upload', formData, {
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
    const response = await api.patch(`/api/v1/documents/${id}`, { filename: newName });
    return response.data;
  },
};
