import React, { useState } from 'react';
import { Link } from 'react-router';
import { authApi } from '@/services/authApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ArrowLeft, MailCheck } from 'lucide-react';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Something went wrong. Please try again.';
      // Rate-limit message is user-friendly
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-[400px] flex flex-col">
        <div className="mb-8 flex flex-col items-center">
          <div className="h-10 w-10 bg-primary text-primary-foreground rounded-lg flex items-center justify-center mb-4 font-semibold text-sm">
            DM
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Reset your password</h1>
          <p className="text-sm text-muted-foreground mt-1 text-center">
            Enter your email and we'll send you a reset link.
          </p>
        </div>

        <div className="bg-card border shadow-sm rounded-xl p-6 sm:p-8">
          {sent ? (
            <div className="flex flex-col items-center text-center space-y-4 py-4">
              <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                <MailCheck className="h-7 w-7 text-primary" />
              </div>
              <div>
                <h2 className="text-base font-semibold">Check your inbox</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  If an account exists for <strong>{email}</strong>, you'll receive a password reset link within a few minutes.
                </p>
              </div>
              <p className="text-xs text-muted-foreground">
                Didn't receive it?{' '}
                <button
                  onClick={() => setSent(false)}
                  className="text-primary hover:underline font-medium"
                >
                  Try again
                </button>
              </p>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
                  {error}
                </div>
              )}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="forgot-email">Email address</Label>
                  <Input
                    id="forgot-email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                    autoFocus
                  />
                </div>
                <Button type="submit" className="w-full mt-2" disabled={isLoading || !email.trim()}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Send Reset Link
                </Button>
              </form>
            </>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link to="/login" className="inline-flex items-center gap-1 text-primary hover:underline font-medium">
            <ArrowLeft className="h-3 w-3" />
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
