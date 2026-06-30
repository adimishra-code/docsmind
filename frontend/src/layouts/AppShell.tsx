import React from 'react';
import { Outlet } from 'react-router';
import { Sidebar } from './Sidebar';
import { TopNavigation } from './TopNavigation';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { useLayoutStore } from '@/store/useLayoutStore';
import { cn } from '@/utils';

export function AppShell() {
  const { isSidebarCollapsed, setSidebarCollapsed } = useLayoutStore();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel
          defaultSize={20}
          minSize={15}
          maxSize={30}
          collapsible={true}
          collapsedSize={4}
          onCollapse={() => setSidebarCollapsed(true)}
          onExpand={() => setSidebarCollapsed(false)}
          className={cn("transition-all duration-300 ease-in-out", isSidebarCollapsed && "min-w-[50px]")}
        >
          <Sidebar collapsed={isSidebarCollapsed} />
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={80}>
          <div className="flex flex-col h-full">
            <TopNavigation />
            <main className="flex-1 overflow-y-auto">
              <Outlet />
            </main>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
