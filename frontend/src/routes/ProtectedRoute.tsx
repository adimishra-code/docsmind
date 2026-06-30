import React from 'react';
import { Navigate, Outlet } from 'react-router';
import { useAuthStore } from '@/store/useAuthStore';

export function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
