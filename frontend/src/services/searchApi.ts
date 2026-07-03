import { api } from './api';

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number?: number | null;
  score: number;
  excerpt: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResultItem[];
}

export const searchApi = {
  search: async (q: string, limit = 10): Promise<SearchResponse> => {
    const { data } = await api.get<SearchResponse>('/api/v1/search', {
      params: { q, limit },
    });
    return data;
  },
};
