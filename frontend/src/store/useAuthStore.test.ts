import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './useAuthStore';

const mockUser = {
  id: 'u1',
  email: 'a@b.com',
  full_name: 'Test User',
  avatar_url: null,
  is_active: true,
  is_admin: false,
  email_verified: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, user: null, isAuthenticated: false });
  });

  it('starts unauthenticated', () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it('setAuth sets token, user, and isAuthenticated', () => {
    useAuthStore.getState().setAuth('tok1', 'refresh1', mockUser);
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('tok1');
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it('clearAuth resets to initial state', () => {
    useAuthStore.getState().setAuth('tok1', 'refresh1', mockUser);
    useAuthStore.getState().clearAuth();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('setAccessToken updates token only', () => {
    useAuthStore.getState().setAuth('tok1', 'refresh1', mockUser);
    useAuthStore.getState().setAccessToken('tok2');
    expect(useAuthStore.getState().accessToken).toBe('tok2');
    expect(useAuthStore.getState().user).toEqual(mockUser);
  });
});
