import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router';
import { useAuthStore } from '@/store/useAuthStore';
import { authApi } from '@/services/authApi';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

export function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Completing sign-in...');

  useEffect(() => {
    const processCallback = async () => {
      const accessToken = searchParams.get('access_token');
      const refreshToken = searchParams.get('refresh_token');
      const error = searchParams.get('error');

      if (error || !accessToken || !refreshToken) {
        setStatus('error');
        setMessage('Authentication failed. Redirecting to login...');
        setTimeout(() => navigate('/login?error=google_oauth_failed', { replace: true }), 2000);
        return;
      }

      try {
        useAuthStore.getState().setAccessToken(accessToken);
        localStorage.setItem('docsmind-refresh-token', refreshToken);

        const user = await authApi.getMe();
        setAuth(accessToken, refreshToken, user);

        setStatus('success');
        setMessage(`Welcome, ${user.full_name || user.email}! Redirecting...`);
        setTimeout(() => navigate('/dashboard', { replace: true }), 1500);
      } catch {
        setStatus('error');
        setMessage('Failed to load your profile. Please try again.');
        setTimeout(() => navigate('/login?error=google_oauth_failed', { replace: true }), 2000);
      }
    };

    processCallback();
  }, []);

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30">
      <div className="text-center max-w-[360px] p-6">
        {status === 'loading' && (
          <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <Loader2 className="h-12 w-12 text-primary animate-spin mb-6" />
            <h2 className="text-xl font-semibold text-foreground mb-2">Signing you in</h2>
            <p className="text-muted-foreground text-sm">{message}</p>
          </div>
        )}
        {status === 'success' && (
          <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <CheckCircle2 className="h-12 w-12 text-success mb-6" />
            <h2 className="text-xl font-semibold text-foreground mb-2">Signed in!</h2>
            <p className="text-success text-sm">{message}</p>
          </div>
        )}
        {status === 'error' && (
          <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <XCircle className="h-12 w-12 text-destructive mb-6" />
            <h2 className="text-xl font-semibold text-foreground mb-2">Sign-in failed</h2>
            <p className="text-destructive text-sm">{message}</p>
          </div>
        )}
      </div>
    </div>
  );
}
