import React from 'react';
import { Outlet } from 'react-router';
import { Sidebar } from './Sidebar';
import { TopNavigation } from './TopNavigation';
import { OfflineBanner } from '@/components/OfflineBanner';
import { ErrorBoundary } from '@/shared/ErrorBoundary';
import { useLayoutStore } from '@/store/useLayoutStore';
import { cn } from '@/utils';

export function AppShell() {
  const { isSidebarCollapsed } = useLayoutStore();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <div
        className={cn(
          'shrink-0 border-r transition-all duration-200 ease-in-out',
          isSidebarCollapsed ? 'w-[64px]' : 'w-[240px]'
        )}
      >
        <Sidebar collapsed={isSidebarCollapsed} />
      </div>
      <div className="flex flex-col flex-1 min-w-0">
        <OfflineBanner />
        <TopNavigation />
        <main className="flex-1 overflow-y-auto">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
