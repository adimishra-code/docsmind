import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { authApi } from '@/services/authApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Eye, EyeOff, ArrowLeft, ShieldCheck, AlertCircle } from 'lucide-react';

type TokenState = 'verifying' | 'valid' | 'invalid' | 'expired';

export function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [tokenState, setTokenState] = useState<TokenState>('verifying');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Verify the token on mount
  useEffect(() => {
    if (!token) {
      setTokenState('invalid');
      return;
    }
    authApi.verifyResetToken(token)
      .then(() => setTokenState('valid'))
      .catch((err: any) => {
        const code = err?.response?.data?.code;
        setTokenState(code === 'token_expired' ? 'expired' : 'invalid');
      });
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
      // Auto-redirect to login after 3 seconds
      setTimeout(() => navigate('/login', { replace: true }), 3000);
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Failed to reset password. Please request a new link.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const renderContent = () => {
    if (tokenState === 'verifying') {
      return (
        <div className="flex flex-col items-center py-8 space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Verifying reset link...</p>
        </div>
      );
    }

    if (tokenState === 'invalid' || tokenState === 'expired') {
      return (
        <div className="flex flex-col items-center text-center space-y-4 py-4">
          <div className="h-14 w-14 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertCircle className="h-7 w-7 text-destructive" />
          </div>
          <div>
            <h2 className="text-base font-semibold">
              {tokenState === 'expired' ? 'Link Expired' : 'Invalid Link'}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {tokenState === 'expired'
                ? 'This reset link has expired. Password reset links are valid for 1 hour.'
                : 'This reset link is invalid or has already been used.'}
            </p>
          </div>
          <Link to="/forgot-password">
            <Button variant="outline" size="sm">Request a new link</Button>
          </Link>
        </div>
      );
    }

    if (success) {
      return (
        <div className="flex flex-col items-center text-center space-y-4 py-4">
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
            <ShieldCheck className="h-7 w-7 text-primary" />
          </div>
          <div>
            <h2 className="text-base font-semibold">Password reset!</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Your password has been changed. Redirecting you to sign in...
            </p>
          </div>
          <Link to="/login">
            <Button size="sm">Sign in now</Button>
          </Link>
        </div>
      );
    }

    return (
      <>
        {error && (
          <div className="mb-4 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reset-password">New Password</Label>
            <div className="relative">
              <Input
                id="reset-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="pr-10"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="reset-confirm">Confirm New Password</Label>
            <Input
              id="reset-confirm"
              type={showPassword ? 'text' : 'password'}
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <Button
            type="submit"
            className="w-full mt-2"
            disabled={isLoading || !password || !confirmPassword}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Set New Password
          </Button>
        </form>
      </>
    );
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-[400px] flex flex-col">
        <div className="mb-8 flex flex-col items-center">
          <div className="h-10 w-10 bg-primary text-primary-foreground rounded-lg flex items-center justify-center mb-4 font-semibold text-sm">
            DM
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Set new password</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Enter a strong password for your account.
          </p>
        </div>

        <div className="bg-card border shadow-sm rounded-xl p-6 sm:p-8">
          {renderContent()}
        </div>

        {tokenState === 'valid' && !success && (
          <p className="mt-6 text-center text-sm text-muted-foreground">
            <Link to="/login" className="inline-flex items-center gap-1 text-primary hover:underline font-medium">
              <ArrowLeft className="h-3 w-3" />
              Back to sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
