import { api } from './api';
import type { UserProfile } from './authApi';

export interface AdminUserListResponse {
  items: UserProfile[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminStats {
  total_users: number;
  total_admins: number;
  active_users: number;
  total_documents: number;
  total_chats: number;
}

export const adminApi = {
  listUsers: async (params?: { q?: string; skip?: number; limit?: number }): Promise<AdminUserListResponse> => {
    const { data } = await api.get<AdminUserListResponse>('/api/v1/admin/users', { params });
    return data;
  },

  getStats: async (): Promise<AdminStats> => {
    const { data } = await api.get<AdminStats>('/api/v1/admin/stats');
    return data;
  },

  promote: async (email: string): Promise<UserProfile> => {
    const { data } = await api.post<UserProfile>('/api/v1/admin/users/promote', { email });
    return data;
  },

  demote: async (email: string): Promise<UserProfile> => {
    const { data } = await api.post<UserProfile>('/api/v1/admin/users/demote', { email });
    return data;
  },
};
