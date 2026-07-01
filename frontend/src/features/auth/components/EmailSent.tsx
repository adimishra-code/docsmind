import React, { useState } from 'react';
import { useLocation, Link } from 'react-router';
import { authApi } from '@/services/authApi';
import { Button } from '@/components/ui/button';
import { Loader2, MailCheck } from 'lucide-react';

export function EmailSent() {
  const location = useLocation();
  const email = (location.state as any)?.email || 'your inbox';

  const [resendLoading, setResendLoading] = useState(false);
  const [resendSent, setResendSent] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);

  const handleResend = async () => {
    setResendLoading(true);
    setResendError(null);
    try {
      await authApi.resendVerification(email);
      setResendSent(true);
    } catch (err: any) {
      setResendError(err?.response?.data?.error || 'Failed to resend. Please try again.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-[440px] flex flex-col items-center text-center">
        <div className="mb-6 h-16 w-16 bg-primary/10 text-primary rounded-full flex items-center justify-center animate-pulse">
          <MailCheck className="h-8 w-8" />
        </div>

        <div className="bg-card border shadow-sm rounded-xl p-8 w-full">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground mb-4">
            Check your email
          </h1>
          <p className="text-muted-foreground text-sm mb-4">
            We sent a verification link to:
          </p>
          <div className="bg-muted px-4 py-3 rounded-lg mb-6 mx-auto inline-block">
            <span className="font-medium text-foreground">{email}</span>
          </div>
          <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
            Click the link in the email to verify your account.
            The link expires in <strong className="text-foreground font-medium">24 hours</strong>.
          </p>

          {resendError && (
            <div className="mb-6 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
              {resendError}
            </div>
          )}

          {resendSent ? (
            <div className="mb-6 p-3 rounded-md bg-success/10 border border-success/20 text-success text-sm font-medium">
              New verification email sent. Please check your inbox.
            </div>
          ) : (
            <Button
              variant="outline"
              onClick={handleResend}
              disabled={resendLoading}
              className="w-full mb-6"
            >
              {resendLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Resending...
                </>
              ) : (
                'Resend verification email'
              )}
            </Button>
          )}

          <div className="border-t pt-6 space-y-3">
            <p className="text-sm text-muted-foreground">
              Wrong email?{' '}
              <Link to="/register" className="text-primary hover:underline font-medium">
                Go back and register again
              </Link>
            </p>
            <p className="text-sm text-muted-foreground">
              Already verified?{' '}
              <Link to="/login" className="text-primary hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <p className="mt-8 text-xs text-muted-foreground">
          Check your spam folder if you don't see the email.
        </p>
      </div>
    </div>
  );
}
