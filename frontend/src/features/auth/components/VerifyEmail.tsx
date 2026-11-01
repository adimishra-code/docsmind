import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'verifying' | 'error'>('verifying');
  const [errorMessage, setErrorMessage] = useState<string>('Verification link is invalid or expired.');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setErrorMessage('No verification token provided.');
      return;
    }

    // Direct browser navigation to backend verification endpoint,
    // which commits verification in Postgres and 302 redirects to /login?verified=true
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8006';
    window.location.href = `${apiUrl}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`;
  }, [token]);

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-[420px] flex flex-col items-center text-center bg-card border shadow-sm rounded-xl p-8">
        {status === 'verifying' ? (
          <>
            <div className="mb-4 h-14 w-14 bg-primary/10 text-primary rounded-full flex items-center justify-center">
              <Loader2 className="h-7 w-7 animate-spin" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground mb-2">
              Verifying your email
            </h1>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Please wait while we activate your DocsMind account...
            </p>
          </>
        ) : (
          <>
            <div className="mb-4 h-14 w-14 bg-destructive/10 text-destructive rounded-full flex items-center justify-center">
              <XCircle className="h-7 w-7" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground mb-2">
              Verification failed
            </h1>
            <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
              {errorMessage}
            </p>
            <div className="w-full space-y-2">
              <Button asChild className="w-full">
                <Link to="/login">Go to sign in</Link>
              </Button>
              <Button asChild variant="outline" className="w-full">
                <Link to="/register">Create new account</Link>
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

