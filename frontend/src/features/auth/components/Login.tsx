import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { authApi } from '@/services/authApi';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Eye, EyeOff } from 'lucide-react';

export function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setAuth } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSent, setResendSent] = useState(false);

  useEffect(() => {
    const verified = searchParams.get('verified');
    const oauthError = searchParams.get('error');
    if (verified === 'true') {
      setSuccessMsg('Email verified successfully. You can now log in.');
    }
    if (oauthError === 'google_oauth_cancelled') {
      setError('Google sign-in was cancelled. Please try again.');
    } else if (oauthError === 'google_oauth_failed') {
      setError('Google sign-in failed. Please try again or use email/password.');
    } else if (oauthError === 'invalid_token') {
      setError('Verification link is invalid or expired. Please request a new one.');
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setUnverifiedEmail(null);
    setIsLoading(true);

    try {
      const tokens = await authApi.login({ email, password });
      const user = await authApi.getMe();
      setAuth(tokens.access_token, tokens.refresh_token, user);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const errorData = err?.response?.data;
      const code = errorData?.code;
      const message = errorData?.error || 'Login failed. Please try again.';

      if (code === 'email_not_verified') {
        setUnverifiedEmail(email);
        setError(message);
      } else {
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!unverifiedEmail) return;
    setResendLoading(true);
    try {
      await authApi.resendVerification(unverifiedEmail);
      setResendSent(true);
    } catch {
      setError('Failed to resend verification email. Please try again.');
    } finally {
      setResendLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = authApi.getGoogleOAuthUrl();
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-[400px] flex flex-col">
        <div className="mb-8 flex flex-col items-center">
          <div className="h-10 w-10 bg-primary text-primary-foreground rounded-lg flex items-center justify-center mb-4 font-semibold text-sm">
            DM
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Sign in to DocsMind</h1>
          <p className="text-sm text-muted-foreground mt-1">Welcome back to your workspace</p>
        </div>

        <div className="bg-card border shadow-sm rounded-xl p-6 sm:p-8">
          {successMsg && (
            <div className="mb-6 p-3 rounded-md bg-success/10 border border-success/20 text-success text-sm font-medium">
              {successMsg}
            </div>
          )}

          {error && (
            <div className="mb-6 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
              {error}
              {unverifiedEmail && !resendSent && (
                <button
                  onClick={handleResendVerification}
                  disabled={resendLoading}
                  className="mt-2 block text-xs underline hover:text-destructive/80"
                >
                  {resendLoading ? 'Sending...' : 'Resend verification email'}
                </button>
              )}
              {resendSent && (
                <div className="mt-2 text-xs text-success">
                  Verification email sent. Check your inbox.
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="login-password">Password</Label>
                <Link to="/forgot-password" className="text-xs text-primary hover:underline font-medium">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={isLoading}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button type="submit" className="w-full mt-2" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sign In
            </Button>
          </form>

          <div className="my-6 flex items-center">
            <div className="flex-1 border-t"></div>
            <span className="px-3 text-xs text-muted-foreground uppercase tracking-wider">Or</span>
            <div className="flex-1 border-t"></div>
          </div>

          <Button 
            type="button" 
            variant="outline" 
            className="w-full font-normal" 
            onClick={handleGoogleLogin}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </Button>
        </div>

        <p className="mt-8 text-center text-sm text-muted-foreground">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary hover:underline font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
