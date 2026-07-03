import { api, refreshAccessToken } from './api';
import { useAuthStore } from '@/store/useAuthStore';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
  citations?: any[];
}

export interface ChatSession {
  id: string;
  title: string;
  user_id: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: Message[];
}

export interface ChatSessionListResponse {
  items: ChatSession[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const chatApi = {
  getSessions: async (params?: { skip?: number; limit?: number }): Promise<ChatSessionListResponse> => {
    const { data } = await api.get<ChatSessionListResponse>('/api/v1/chat/sessions', { params });
    return data;
  },

  createSession: async (title: string): Promise<ChatSession> => {
    const { data } = await api.post<ChatSession>('/api/v1/chat/sessions', { title });
    return data;
  },

  getSession: async (id: string): Promise<ChatSessionDetail> => {
    const { data } = await api.get<ChatSessionDetail>(`/api/v1/chat/sessions/${id}`);
    return data;
  },

  updateSession: async (id: string, updates: { title?: string; is_pinned?: boolean }): Promise<ChatSession> => {
    const { data } = await api.patch<ChatSession>(`/api/v1/chat/sessions/${id}`, updates);
    return data;
  },

  deleteSession: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/chat/sessions/${id}`);
  },

  sendMessage: async (sessionId: string, content: string, options?: {
    document_ids?: string[];
    multi_query?: boolean;
    expand_context?: boolean;
  }): Promise<Response> => {
    const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8006'}/api/v1/chat/sessions/${sessionId}/messages`;
    const body = JSON.stringify({ content, ...options });

    const doFetch = (token: string | null) =>
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body,
      });

    // The SSE stream uses raw fetch(), so it bypasses the axios 401-refresh
    // interceptor. Handle an expired access token here: refresh once and retry.
    let response = await doFetch(useAuthStore.getState().accessToken);
    if (response.status === 401) {
      try {
        const newToken = await refreshAccessToken();
        response = await doFetch(newToken);
      } catch {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
        return response;
      }
    }
    return response;
  },
};
