import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from './adminApi';
import { api } from './api';

vi.mock('./api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

describe('adminApi', () => {
  beforeEach(() => vi.clearAllMocks());

  it('lists users with search params', async () => {
    (api.get as any).mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 50, total_pages: 1 },
    });
    const res = await adminApi.listUsers({ q: 'jane', limit: 100 });
    expect(api.get).toHaveBeenCalledWith('/api/v1/admin/users', { params: { q: 'jane', limit: 100 } });
    expect(res.total).toBe(0);
  });

  it('promotes a user by email', async () => {
    (api.post as any).mockResolvedValue({ data: { email: 'x@y.com', is_admin: true } });
    const u = await adminApi.promote('x@y.com');
    expect(api.post).toHaveBeenCalledWith('/api/v1/admin/users/promote', { email: 'x@y.com' });
    expect(u.is_admin).toBe(true);
  });

  it('demotes a user by email', async () => {
    (api.post as any).mockResolvedValue({ data: { email: 'x@y.com', is_admin: false } });
    const u = await adminApi.demote('x@y.com');
    expect(api.post).toHaveBeenCalledWith('/api/v1/admin/users/demote', { email: 'x@y.com' });
    expect(u.is_admin).toBe(false);
  });

  it('fetches real platform stats', async () => {
    (api.get as any).mockResolvedValue({
      data: { total_users: 3, total_admins: 1, active_users: 3, total_documents: 5, total_chats: 2 },
    });
    const s = await adminApi.getStats();
    expect(api.get).toHaveBeenCalledWith('/api/v1/admin/stats');
    expect(s.total_admins).toBe(1);
  });
});
