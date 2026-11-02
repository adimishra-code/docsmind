import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '@/services/adminApi';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from '@/components/ui/use-toast';
import { format } from 'date-fns';
import { ShieldCheck, ShieldPlus, ShieldMinus, Users, FileText, MessageSquare, LogOut, Search, UserPlus } from 'lucide-react';

function StatCard({ icon: Icon, label, value, loading }: { icon: any; label: string; value?: number; loading: boolean }) {
  return (
    <div className="rounded-xl border bg-card p-3 sm:p-4">
      <div className="flex items-center gap-1.5 sm:gap-2 text-[11px] sm:text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5" /> {label}
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-16" />
      ) : (
        <p className="mt-1 text-xl sm:text-2xl font-semibold tabular-nums">{value ?? 0}</p>
      )}
    </div>
  );
}

export function AdminPanel() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const [search, setSearch] = useState('');
  const [promoteEmail, setPromoteEmail] = useState('');

  const stats = useQuery({ queryKey: ['admin-stats'], queryFn: adminApi.getStats });
  const users = useQuery({
    queryKey: ['admin-users', search],
    queryFn: () => adminApi.listUsers({ q: search || undefined, limit: 100 }),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
  };

  const promoteMutation = useMutation({
    mutationFn: (email: string) => adminApi.promote(email),
    onSuccess: (u) => {
      toast({ title: 'Admin granted', description: `${u.email} is now an administrator.` });
      setPromoteEmail('');
      refresh();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.response?.data?.error || 'Could not promote that user.';
      toast({ title: 'Promotion failed', variant: 'destructive', description: msg });
    },
  });

  const demoteMutation = useMutation({
    mutationFn: (email: string) => adminApi.demote(email),
    onSuccess: (u) => {
      toast({ title: 'Admin revoked', description: `${u.email} is no longer an administrator.` });
      refresh();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.response?.data?.error || 'Could not revoke admin.';
      toast({ title: 'Action failed', variant: 'destructive', description: msg });
    },
  });

  const handlePromoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const email = promoteEmail.trim().toLowerCase();
    if (email) promoteMutation.mutate(email);
  };

  const items = users.data?.items ?? [];

  return (
    <div className="min-h-screen bg-muted/20">
      {/* Header */}
      <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b bg-background px-4 sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-foreground text-background">
            <ShieldCheck className="h-3.5 w-3.5" />
          </div>
          <span className="text-[15px] font-semibold tracking-tight">Admin Console</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="hidden text-sm text-muted-foreground md:inline">{currentUser?.email}</span>
          <Button variant="outline" size="sm" onClick={() => navigate('/dashboard')} className="text-xs sm:text-sm">
            Back to app
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => { clearAuth(); navigate('/admin/login'); }}
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">Manage users and administrator access.</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5 sm:gap-3">
          <StatCard icon={Users} label="Users" value={stats.data?.total_users} loading={stats.isLoading} />
          <StatCard icon={ShieldCheck} label="Admins" value={stats.data?.total_admins} loading={stats.isLoading} />
          <StatCard icon={Users} label="Active" value={stats.data?.active_users} loading={stats.isLoading} />
          <StatCard icon={FileText} label="Documents" value={stats.data?.total_documents} loading={stats.isLoading} />
          <StatCard icon={MessageSquare} label="Chats" value={stats.data?.total_chats} loading={stats.isLoading} />
        </div>

        {/* Promote by email */}
        <div className="rounded-xl border bg-card p-4">
          <div className="mb-3 flex items-center gap-2">
            <UserPlus className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-medium">Grant administrator access</h2>
          </div>
          <form onSubmit={handlePromoteSubmit} className="flex flex-col gap-2 sm:flex-row">
            <Input
              type="email"
              value={promoteEmail}
              onChange={(e) => setPromoteEmail(e.target.value)}
              placeholder="Enter a user's email address…"
              className="sm:max-w-sm"
            />
            <Button type="submit" className="gap-1.5" disabled={!promoteEmail.trim() || promoteMutation.isPending}>
              <ShieldPlus className="h-4 w-4" /> Make admin
            </Button>
          </form>
          <p className="mt-2 text-xs text-muted-foreground">
            The person must already have a DocsMind account. They gain admin access immediately.
          </p>
        </div>

        {/* Users table */}
        <div className="space-y-3">
          <div className="relative sm:max-w-xs">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search users…"
              className="pl-8"
            />
          </div>

          <div className="rounded-xl border bg-card overflow-x-auto w-full">
            <Table className="min-w-full">
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="hidden sm:table-cell">Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.isLoading ? (
                  [0, 1, 2, 3].map((i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={4}><Skeleton className="h-8 w-full" /></TableCell>
                    </TableRow>
                  ))
                ) : items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-10 text-center text-sm text-muted-foreground">
                      No users found.
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((u) => {
                    const isSelf = u.id === currentUser?.id;
                    return (
                      <TableRow key={u.id}>
                        <TableCell className="max-w-[160px] sm:max-w-none">
                          <div className="font-medium truncate">{u.full_name || '—'}</div>
                          <div className="text-xs text-muted-foreground truncate">{u.email}</div>
                        </TableCell>
                        <TableCell>
                          {u.is_admin ? (
                            <Badge className="gap-1 text-[11px] sm:text-xs"><ShieldCheck className="h-3 w-3" /> Admin</Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[11px] sm:text-xs">Member</Badge>
                          )}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                          {(() => {
                            try { return format(new Date(u.created_at), 'MMM d, yyyy'); } catch { return '—'; }
                          })()}
                        </TableCell>
                        <TableCell className="text-right">
                          {u.is_admin ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="gap-1.5 text-xs text-muted-foreground hover:text-destructive"
                              disabled={isSelf || demoteMutation.isPending}
                              title={isSelf ? "You can't revoke your own access" : 'Revoke admin'}
                              onClick={() => demoteMutation.mutate(u.email)}
                            >
                              <ShieldMinus className="h-3.5 w-3.5" />
                              <span className="hidden sm:inline">Revoke</span>
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="gap-1.5 text-xs"
                              disabled={promoteMutation.isPending}
                              onClick={() => promoteMutation.mutate(u.email)}
                            >
                              <ShieldPlus className="h-3.5 w-3.5" />
                              <span className="hidden sm:inline">Make admin</span>
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </div>
  );
}
