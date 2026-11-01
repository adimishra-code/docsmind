import React from 'react';
import { Navigate, Outlet } from 'react-router';
import { useAuthStore } from '@/store/useAuthStore';

/** Guards the admin area: must be authenticated AND an admin. Non-admins are
 *  sent to the admin login screen (which explains the requirement). */
export function AdminRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isAdmin = useAuthStore((state) => state.user?.is_admin ?? false);

  if (!isAuthenticated || !isAdmin) {
    return <Navigate to="/admin/login" replace />;
  }

  return <Outlet />;
}
