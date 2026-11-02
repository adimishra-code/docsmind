import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router';
import { Sidebar } from './Sidebar';
import { TopNavigation } from './TopNavigation';
import { OfflineBanner } from '@/components/OfflineBanner';
import { ErrorBoundary } from '@/shared/ErrorBoundary';
import { useLayoutStore } from '@/store/useLayoutStore';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { cn } from '@/utils';

export function AppShell() {
  const { isSidebarCollapsed, isMobileMenuOpen, setMobileMenuOpen } = useLayoutStore();
  const location = useLocation();

  // Close mobile drawer on navigation
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname, setMobileMenuOpen]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Desktop Sidebar (hidden on screens < 768px) */}
      <div
        className={cn(
          'hidden md:block shrink-0 transition-all duration-200 ease-in-out',
          isSidebarCollapsed ? 'w-[64px]' : 'w-[240px]'
        )}
      >
        <Sidebar collapsed={isSidebarCollapsed} />
      </div>

      {/* Mobile Sidebar Sheet (visible only when triggered on screens < 768px) */}
      <Sheet open={isMobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" hideCloseButton className="p-0 w-[260px] sm:w-[280px]">
          <Sidebar
            collapsed={false}
            hideCollapseButton
            onClose={() => setMobileMenuOpen(false)}
            onNavigate={() => setMobileMenuOpen(false)}
          />
        </SheetContent>
      </Sheet>

      {/* Main Content Area */}
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
