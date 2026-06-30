import { api } from './api';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
  citations?: any[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export const chatApi = {
  getConversations: async (): Promise<Conversation[]> => {
    // const response = await api.get('/api/v1/chat/conversations');
    // return response.data;
    return []; // Mock until backend is fully hooked up
  },

  getConversationHistory: async (id: string): Promise<Message[]> => {
    // const response = await api.get(`/api/v1/chat/conversations/${id}/messages`);
    // return response.data;
    return [];
  },

  deleteConversation: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/chat/conversations/${id}`);
  },

  renameConversation: async (id: string, title: string): Promise<Conversation> => {
    const response = await api.patch(`/api/v1/chat/conversations/${id}`, { title });
    return response.data;
  },
};
