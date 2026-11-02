import React from 'react';
import { useLocation, useNavigate, Link } from 'react-router';
import { Search, Sun, Moon, LogOut, User, Settings, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useLayoutStore } from '@/store/useLayoutStore';
import { useTheme } from '@/providers/theme-provider';
import { useAuthStore } from '@/store/useAuthStore';

const ROUTE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  chat: 'Chat',
  documents: 'Documents',
  search: 'Search',
  settings: 'Settings',
  observability: 'Analytics',
  admin: 'Admin',
};

export function TopNavigation() {
  const setCommandPaletteOpen = useLayoutStore((state) => state.setCommandPaletteOpen);
  const toggleMobileMenu = useLayoutStore((state) => state.toggleMobileMenu);
  const { theme, setTheme } = useTheme();
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const user = useAuthStore((state) => state.user);
  const location = useLocation();
  const navigate = useNavigate();

  const pathSegments = location.pathname.split('/').filter(Boolean);
  const breadcrumbs = pathSegments.map((segment, i) => ({
    label: ROUTE_LABELS[segment] ?? segment.charAt(0).toUpperCase() + segment.slice(1),
    path: '/' + pathSegments.slice(0, i + 1).join('/'),
    isLast: i === pathSegments.length - 1,
  }));

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() ?? 'U';

  return (
    <header className="flex h-14 items-center justify-between border-b px-3 sm:px-6 bg-background/85 backdrop-blur-sm supports-[backdrop-filter]:bg-background/70 shrink-0 sticky top-0 z-20">
      {/* Left: Hamburger menu (mobile) + Breadcrumbs */}
      <div className="flex items-center min-w-0 mr-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleMobileMenu}
          className="md:hidden h-9 w-9 mr-1 text-muted-foreground hover:text-foreground shrink-0"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <nav className="flex items-center gap-1.5 text-sm min-w-0 overflow-hidden">
          <Link
            to="/dashboard"
            className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            Home
          </Link>
          {breadcrumbs.map((crumb) => (
            <React.Fragment key={crumb.path}>
              <span className="text-muted-foreground/50 shrink-0">/</span>
              {crumb.isLast ? (
                <span className="font-medium text-foreground truncate max-w-[120px] sm:max-w-[200px] md:max-w-none">
                  {crumb.label}
                </span>
              ) : (
                <Link
                  to={crumb.path}
                  className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[80px] sm:max-w-[140px] md:max-w-none"
                >
                  {crumb.label}
                </Link>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          className="hidden sm:flex h-9 w-full justify-start rounded-md bg-muted/50 text-sm text-muted-foreground sm:pr-12 md:w-44 lg:w-64"
          onClick={() => setCommandPaletteOpen(true)}
        >
          <Search className="mr-2 h-4 w-4 shrink-0" />
          <span className="truncate">Search...</span>
          <kbd className="ml-auto pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-background px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCommandPaletteOpen(true)}
          className="sm:hidden h-9 w-9 text-muted-foreground hover:text-foreground"
          aria-label="Search"
        >
          <Search className="h-4 w-4" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="h-9 w-9 text-muted-foreground hover:text-foreground"
          aria-label="Toggle theme"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full ml-1" aria-label="User profile">
              <Avatar className="h-8 w-8">
                <AvatarImage src="" alt={user?.full_name ?? ''} />
                <AvatarFallback className="bg-foreground text-background text-xs font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end">
            <div className="flex items-center gap-2 p-2">
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
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate('/settings')}>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => navigate('/settings')}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => clearAuth()}>
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
