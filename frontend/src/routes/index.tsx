import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { Login } from '@/features/auth/components/Login';
import { Register } from '@/features/auth/components/Register';
import { AppShell } from '@/layouts/AppShell';
import { Workspace } from '@/features/knowledge/components/Workspace';
import { KnowledgeEngine } from '@/features/viewer/components/KnowledgeEngine';
import { AIWorkspace } from '@/features/chat/components/AIWorkspace';
import { ObservabilityDashboard } from '@/features/observability/components/ObservabilityDashboard';

const Dashboard = () => <div className="p-8">Dashboard Placeholder</div>;
const NotFound = () => <div className="p-8 text-center text-xl">404 - Not Found</div>;

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        {/* Protected Routes inside App Shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/documents" element={<Workspace />} />
            <Route path="/documents/:id" element={<KnowledgeEngine />} />
            <Route path="/chat" element={<AIWorkspace />} />
            <Route path="/chat/:id" element={<AIWorkspace />} />
            <Route path="/observability" element={<ObservabilityDashboard />} />
            {/* Will add other routes here in future sprints */}
          </Route>
        </Route>

        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        {/* Catch-all 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
