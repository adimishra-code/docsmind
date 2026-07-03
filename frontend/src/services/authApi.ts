import { api } from './api';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_admin: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  message: string;
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const { data } = await api.post<TokenResponse>('/api/v1/auth/login', credentials);
    return data;
  },

  register: async (credentials: RegisterCredentials): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>('/api/v1/auth/register', credentials);
    return data;
  },

  logout: async (refreshToken: string): Promise<void> => {
    await api.post('/api/v1/auth/logout', { refresh_token: refreshToken });
  },

  getMe: async (): Promise<UserProfile> => {
    const { data } = await api.get<UserProfile>('/api/v1/auth/me');
    return data;
  },

  updateMe: async (fullName: string | null): Promise<UserProfile> => {
    const { data } = await api.patch<UserProfile>('/api/v1/auth/me', { full_name: fullName });
    return data;
  },

  deleteMe: async (): Promise<void> => {
    await api.delete('/api/v1/auth/me');
  },

  resendVerification: async (email: string): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>('/api/v1/auth/resend-verification', { email });
    return data;
  },

  forgotPassword: async (email: string): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>('/api/v1/auth/forgot-password', { email });
    return data;
  },

  verifyResetToken: async (token: string): Promise<MessageResponse> => {
    const { data } = await api.get<MessageResponse>('/api/v1/auth/reset-password/verify', { params: { token } });
    return data;
  },

  resetPassword: async (token: string, newPassword: string): Promise<MessageResponse> => {
    const { data } = await api.post<MessageResponse>('/api/v1/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return data;
  },

  getGoogleOAuthUrl: (): string => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8006';
    return `${baseUrl}/api/v1/auth/google`;
  },
};
