import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { authApi } from '@/services/authApi';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ShieldCheck, Eye, EyeOff, AlertTriangle } from 'lucide-react';

/**
 * Dedicated admin sign-in. Uses the same credential system as the app, then
 * requires the account to actually be an administrator — a non-admin who signs
 * in here is told they lack access rather than being let into the console.
 */
export function AdminLogin() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const tokens = await authApi.login({ email, password });
      useAuthStore.getState().setAccessToken(tokens.access_token);
      const user = await authApi.getMe();
      if (!user.is_admin) {
        useAuthStore.getState().clearAuth();
        setError('This account does not have administrator access.');
        return;
      }
      setAuth(tokens.access_token, tokens.refresh_token, user);
      navigate('/admin', { replace: true });
    } catch (err: any) {
      const data = err?.response?.data;
      setError(data?.error || data?.detail || 'Sign-in failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-foreground text-background">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">Admin Console</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign in with an administrator account.</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl border bg-card p-6 shadow-sm"
        >
          {error && (
            <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              <span className="text-foreground">{error}</span>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="admin-email">Email</Label>
            <Input
              id="admin-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@company.com"
              required
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="admin-password">Password</Label>
            <div className="relative">
              <Input
                id="admin-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <Button type="submit" className="w-full gap-2" disabled={isLoading || !email || !password}>
            {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign in to console
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Not an admin?{' '}
          <button onClick={() => navigate('/login')} className="font-medium text-foreground hover:underline">
            Go to the app
          </button>
        </p>
      </div>
    </div>
  );
}
