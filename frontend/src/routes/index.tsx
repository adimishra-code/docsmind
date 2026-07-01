import React, { Suspense } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { Login } from '@/features/auth/components/Login';
import { Register } from '@/features/auth/components/Register';
import { EmailSent } from '@/features/auth/components/EmailSent';
import { OAuthCallback } from '@/features/auth/components/OAuthCallback';
import { ForgotPassword } from '@/features/auth/components/ForgotPassword';
import { ResetPassword } from '@/features/auth/components/ResetPassword';
import { AppShell } from '@/layouts/AppShell';
import { PageSkeleton, ChatSkeleton } from '@/shared/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { Home, ArrowLeft } from 'lucide-react';

const Dashboard = React.lazy(() => import('@/features/dashboard/components/Dashboard').then(m => ({ default: m.Dashboard })));
const Workspace = React.lazy(() => import('@/features/knowledge/components/Workspace').then(m => ({ default: m.Workspace })));
const KnowledgeEngine = React.lazy(() => import('@/features/viewer/components/KnowledgeEngine').then(m => ({ default: m.KnowledgeEngine })));
const AIWorkspace = React.lazy(() => import('@/features/chat/components/AIWorkspace').then(m => ({ default: m.AIWorkspace })));
const ObservabilityDashboard = React.lazy(() => import('@/features/observability/components/ObservabilityDashboard').then(m => ({ default: m.ObservabilityDashboard })));
const Settings = React.lazy(() => import('@/features/settings/components/Settings').then(m => ({ default: m.Settings })));
const SearchPage = React.lazy(() => import('@/features/search/components/SearchPage').then(m => ({ default: m.SearchPage })));

function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className="text-8xl font-black text-muted-foreground/20 mb-4 select-none">404</div>
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-muted-foreground mt-2 max-w-sm">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div className="flex gap-3 mt-8">
        <Button variant="outline" onClick={() => navigate(-1)} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Go back
        </Button>
        <Button onClick={() => navigate('/dashboard')} className="gap-2">
          <Home className="h-4 w-4" />
          Dashboard
        </Button>
      </div>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes (redirect to dashboard if already authenticated) */}
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Auth flow pages (accessible without auth) */}
      <Route path="/email-sent" element={<EmailSent />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<Suspense fallback={<PageSkeleton />}><Dashboard /></Suspense>} />
          <Route path="/documents" element={<Suspense fallback={<PageSkeleton />}><Workspace /></Suspense>} />
          <Route path="/documents/:id" element={<Suspense fallback={<PageSkeleton />}><KnowledgeEngine /></Suspense>} />
          <Route path="/chat" element={<Suspense fallback={<ChatSkeleton />}><AIWorkspace /></Suspense>} />
          <Route path="/chat/:id" element={<Suspense fallback={<ChatSkeleton />}><AIWorkspace /></Suspense>} />
          <Route path="/search" element={<Suspense fallback={<PageSkeleton />}><SearchPage /></Suspense>} />
          <Route path="/observability" element={<Suspense fallback={<PageSkeleton />}><ObservabilityDashboard /></Suspense>} />
          <Route path="/settings" element={<Suspense fallback={<PageSkeleton />}><Settings /></Suspense>} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
