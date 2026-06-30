import React from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { MessageSquare, FileText, Settings, LayoutDashboard, Star, Pin } from 'lucide-react';
import { cn } from '@/utils';
import { useAuthStore } from '@/store/useAuthStore';

interface SidebarProps {
  collapsed: boolean;
}

export function Sidebar({ collapsed }: SidebarProps) {
  const user = useAuthStore((state) => state.user);

  const NavItem = ({ icon: Icon, label, href }: { icon: any, label: string, href: string }) => (
    <Button variant="ghost" className={cn("w-full justify-start", collapsed ? "px-2" : "px-4")}>
      <Icon className={cn("h-4 w-4", collapsed ? "mr-0 mx-auto" : "mr-2")} />
      {!collapsed && <span>{label}</span>}
    </Button>
  );

  return (
    <div className="flex flex-col h-full bg-muted/20 border-r">
      <div className="flex h-14 items-center border-b px-4 font-semibold">
        {!collapsed ? "DocsMind" : "DM"}
      </div>
      <ScrollArea className="flex-1 py-4">
        <div className="space-y-1 px-2">
          <NavItem icon={LayoutDashboard} label="Dashboard" href="/dashboard" />
          <NavItem icon={MessageSquare} label="Chats" href="/chat" />
          <NavItem icon={FileText} label="Documents" href="/documents" />
        </div>
        
        {!collapsed && (
          <>
            <div className="mt-6 mb-2 px-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Favorites
            </div>
            <div className="space-y-1 px-2">
              <NavItem icon={Star} label="Q3 Reports" href="/documents/star-1" />
              <NavItem icon={Pin} label="Engineering Spec" href="/chat/pin-1" />
            </div>
          </>
        )}
      </ScrollArea>
      <div className="p-4 border-t">
        <NavItem icon={Settings} label="Settings" href="/settings" />
      </div>
    </div>
  );
}
