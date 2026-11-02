import React from 'react';
import { NavLink } from 'react-router';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  BarChart3,
  Settings,
  Search,
  Upload,
  LogOut,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  X,
} from 'lucide-react';
import { cn } from '@/utils';
import { useAuthStore } from '@/store/useAuthStore';
import { useLayoutStore } from '@/store/useLayoutStore';

interface SidebarProps {
  collapsed: boolean;
  onNavigate?: () => void;
  hideCollapseButton?: boolean;
  onClose?: () => void;
}

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
  { icon: MessageSquare, label: 'Chat', href: '/chat' },
  { icon: FileText, label: 'Documents', href: '/documents' },
  { icon: Search, label: 'Search', href: '/search' },
  { icon: BarChart3, label: 'Analytics', href: '/observability' },
] as const;

const BOTTOM_ITEMS = [
  { icon: Settings, label: 'Settings', href: '/settings' },
] as const;

function NavItemLink({
  icon: Icon,
  label,
  href,
  collapsed,
  onNavigate,
}: {
  icon: any;
  label: string;
  href: string;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const link = (
    <NavLink
      to={href}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'group/nav relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-150',
          isActive
            ? 'bg-accent text-foreground font-medium before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-foreground'
            : 'text-muted-foreground font-medium hover:bg-accent/60 hover:text-foreground',
          collapsed && 'justify-center px-2'
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span>{label}</span>}
    </NavLink>
  );

  if (collapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    );
  }

  return link;
}

export function Sidebar({ collapsed, onNavigate, hideCollapseButton = false, onClose }: SidebarProps) {
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const toggleSidebar = useLayoutStore((state) => state.toggleSidebar);

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? 'U';

  const handleSignOut = () => {
    onNavigate?.();
    clearAuth();
  };

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full bg-secondary/40 border-r">
        {/* Logo */}
        <div className={cn(
          'flex h-14 items-center px-4 shrink-0',
          collapsed ? 'justify-center' : 'justify-between'
        )}>
          {!collapsed && (
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 text-white text-[11px] font-bold shadow-sm">
                DM
              </div>
              <span className="text-[15px] font-semibold tracking-tight">DocsMind</span>
            </div>
          )}
          {onClose ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              aria-label="Close menu"
            >
              <X className="h-4 w-4" />
            </Button>
          ) : !hideCollapseButton ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="h-7 w-7 text-muted-foreground hover:text-foreground"
            >
              {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </Button>
          ) : null}
        </div>

        {/* Main nav */}
        <ScrollArea className="flex-1 py-3 px-2">
          <nav className="space-y-0.5">
            {NAV_ITEMS.map((item) => (
              <NavItemLink key={item.href} {...item} collapsed={collapsed} onNavigate={onNavigate} />
            ))}
          </nav>

          {!collapsed && (
            <>
              <Separator className="my-4" />
              <div className="px-3 mb-2">
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                  Quick Actions
                </p>
              </div>
              <div className="space-y-0.5">
                <NavItemLink icon={Upload} label="Upload" href="/documents?upload=true" collapsed={collapsed} onNavigate={onNavigate} />
              </div>
            </>
          )}
        </ScrollArea>

        {/* Bottom section */}
        <div className="border-t px-2 py-2 space-y-0.5">
          {user?.is_admin && (
            <NavItemLink icon={ShieldCheck} label="Admin" href="/admin" collapsed={collapsed} onNavigate={onNavigate} />
          )}
          {BOTTOM_ITEMS.map((item) => (
            <NavItemLink key={item.href} {...item} collapsed={collapsed} onNavigate={onNavigate} />
          ))}

          <Separator className="my-2" />

          {/* User section */}
          {collapsed ? (
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <button
                  onClick={handleSignOut}
                  className="flex w-full items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">Sign out</TooltipContent>
            </Tooltip>
          ) : (
            <div className="flex items-center gap-3 rounded-md px-3 py-2">
              <Avatar className="h-8 w-8">
                <AvatarImage src="" alt={user?.full_name ?? ''} />
                <AvatarFallback className="bg-foreground text-background text-xs font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.full_name ?? 'User'}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email ?? ''}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleSignOut}
                className="h-7 w-7 text-muted-foreground hover:text-foreground shrink-0"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
