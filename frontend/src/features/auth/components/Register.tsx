import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { authApi } from '@/services/authApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Eye, EyeOff } from 'lucide-react';

export function Register() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simple password strength calculation
  const calculateStrength = (pwd: string) => {
    let score = 0;
    if (pwd.length >= 8) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;
    return score;
  };
  const strength = calculateStrength(password);
  
  // Password match status
  const passwordsMatch = password.length > 0 && confirmPassword.length > 0 && password === confirmPassword;
  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setIsLoading(true);

    try {
      await authApi.register({ email, password, full_name: fullName });
      // Redirect to a specific route indicating email was sent
      navigate('/email-sent', { state: { email } });
    } catch (err: any) {
      const errorData = err?.response?.data;
      const message =
        errorData?.error ||
        errorData?.detail ||
        (Array.isArray(errorData?.details) ? errorData.details.map((d: any) => d.msg).join(', ') : null) ||
        err?.message ||
        'Registration failed. Please try again.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-[440px] flex flex-col my-8">
        <div className="mb-8 flex flex-col items-center">
          <div className="h-10 w-10 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 text-white rounded-xl flex items-center justify-center mb-4 font-bold text-sm shadow-md">
            DM
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Create an account</h1>
          <p className="text-sm text-muted-foreground mt-1">Start your DocsMind workspace</p>
        </div>

        <div className="bg-card border shadow-sm rounded-xl p-6 sm:p-8">
          {error && (
            <div className="mb-6 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
              {error}
              {error.toLowerCase().includes('already exists') && (
                <div className="mt-2">
                  <Link to="/login" className="underline font-semibold hover:text-destructive/80">
                    → Sign in to your account
                  </Link>
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="register-name">Full Name</Label>
              <Input
                id="register-name"
                type="text"
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="register-email">Email</Label>
              <Input
                id="register-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="register-password">Password</Label>
              <div className="relative">
                <Input
                  id="register-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
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
              
              {/* Password strength indicator */}
              {password.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {[1, 2, 3, 4, 5].map((level) => (
                    <div 
                      key={level} 
                      className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                        level <= strength 
                          ? strength < 3 ? 'bg-warning' : strength < 4 ? 'bg-info' : 'bg-success'
                          : 'bg-muted'
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="register-confirm">Confirm Password</Label>
              <Input
                id="register-confirm"
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={isLoading}
                className={passwordsMismatch ? 'border-destructive focus-visible:ring-destructive' : passwordsMatch ? 'border-success focus-visible:ring-success' : ''}
              />
              {passwordsMismatch && (
                <p className="text-xs text-destructive mt-1">Passwords do not match</p>
              )}
            </div>

            <Button type="submit" className="w-full mt-4" disabled={isLoading || passwordsMismatch}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Account
            </Button>
          </form>
          
          <p className="text-xs text-muted-foreground mt-6 text-center leading-relaxed">
            By clicking "Create Account" or "Continue with Google", you agree to our 
            <a href="#" className="underline ml-1 hover:text-foreground">Terms of Service</a> and 
            <a href="#" className="underline ml-1 hover:text-foreground">Privacy Policy</a>.
          </p>
        </div>

        <p className="mt-8 text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
