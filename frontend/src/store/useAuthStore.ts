import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserProfile } from '@/services/authApi';

interface AuthState {
  accessToken: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  setAuth: (accessToken: string, refreshToken: string, user: UserProfile) => void;
  clearAuth: () => void;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: UserProfile) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,

      setAuth: (accessToken, refreshToken, user) => {
        // Store refresh token in localStorage separately (not in Zustand persist)
        localStorage.setItem('docsmind-refresh-token', refreshToken);
        set({ accessToken, user, isAuthenticated: true });
      },

      clearAuth: () => {
        localStorage.removeItem('docsmind-refresh-token');
        set({ accessToken: null, user: null, isAuthenticated: false });
      },

      setAccessToken: (accessToken) => set({ accessToken }),

      setUser: (user) => set({ user }),
    }),
    {
      name: 'docsmind-auth-storage',
      // Only persist accessToken and user (not refresh token — stored separately)
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
