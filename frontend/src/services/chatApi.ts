import { api, refreshAccessToken } from './api';
import { useAuthStore } from '@/store/useAuthStore';

/** Real, per-response grounding metadata. Every field is optional — the UI
 *  only renders what the backend/stream actually provided (never fabricated). */
export interface MessageMeta {
  model?: string;
  provider?: string;
  confidence?: number;   // 0..1, from the verifier node
  chunkCount?: number;   // retrieved chunks considered
  tokenCount?: number;   // prompt + completion tokens
  ttftMs?: number;       // time to first streamed token (client-measured)
  totalMs?: number;      // total wall-clock time (client-measured during stream; server-measured on reload)
  latencyMs?: number;    // server-measured backend processing time (persisted in DB meta)
  cached?: boolean;      // served from the RAG cache
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
  citations?: any[];
  meta?: MessageMeta;
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
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register') && !window.location.pathname.startsWith('/forgot-password')) {
          window.location.href = '/login';
        }
        return response;
      }
    }
    return response;
  },
};
