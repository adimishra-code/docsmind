import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi, ChatSession } from '@/services/chatApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/utils';
import {
  Plus,
  Search,
  Pin,
  PinOff,
  Pencil,
  Trash2,
  MessageSquare,
  MoreHorizontal,
  X,
  Check,
  Loader2,
} from 'lucide-react';
import { formatDistanceToNow, isToday, isYesterday, parseISO } from 'date-fns';

interface ConversationSidebarProps {
  onSessionChange?: (sessionId: string) => void;
}

function getGroupLabel(dateStr: string): string {
  const date = parseISO(dateStr);
  if (isToday(date)) return 'Today';
  if (isYesterday(date)) return 'Yesterday';
  const days = Math.floor((Date.now() - date.getTime()) / 86400000);
  if (days < 7) return 'This Week';
  if (days < 30) return 'This Month';
  return 'Older';
}

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  onSelect: () => void;
  onRename: (id: string, title: string) => void;
  onPin: (id: string, pinned: boolean) => void;
  onDelete: (id: string) => void;
}

function SessionItem({ session, isActive, onSelect, onRename, onPin, onDelete }: SessionItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(session.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const commitRename = () => {
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== session.title) {
      onRename(session.id, trimmed);
    } else {
      setEditTitle(session.title);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commitRename();
    if (e.key === 'Escape') { setEditTitle(session.title); setIsEditing(false); }
  };

  return (
    <div
      className={cn(
        'group relative flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer transition-colors duration-100',
        isActive ? 'bg-primary/10 text-primary' : 'hover:bg-accent text-foreground',
      )}
      onClick={() => !isEditing && onSelect()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && !isEditing && onSelect()}
      aria-selected={isActive}
    >
      <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden />

      {isEditing ? (
        <div className="flex-1 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Input
            ref={inputRef}
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={commitRename}
            className="h-6 text-xs px-1 py-0 border-primary"
          />
          <button onClick={commitRename} className="text-primary hover:text-primary/80" aria-label="Save rename">
            <Check className="h-3.5 w-3.5" />
          </button>
          <button onClick={() => { setEditTitle(session.title); setIsEditing(false); }} className="text-muted-foreground hover:text-foreground" aria-label="Cancel rename">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <>
          <span className="flex-1 truncate text-[13px]">{session.title}</span>
          {session.is_pinned && <Pin className="h-3 w-3 shrink-0 text-muted-foreground" aria-label="Pinned" />}
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <button
                className="shrink-0 opacity-0 group-hover:opacity-100 h-5 w-5 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-all"
                aria-label="Session options"
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); setIsEditing(true); }}>
                <Pencil className="mr-2 h-3.5 w-3.5" /> Rename
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onPin(session.id, !session.is_pinned); }}>
                {session.is_pinned
                  ? <><PinOff className="mr-2 h-3.5 w-3.5" /> Unpin</>
                  : <><Pin className="mr-2 h-3.5 w-3.5" /> Pin</>}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
              >
                <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </>
      )}
    </div>
  );
}

export function ConversationSidebar({ onSessionChange }: ConversationSidebarProps) {
  const { id: activeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => chatApi.getSessions({ limit: 100 }),
    refetchOnWindowFocus: true,
    staleTime: 30_000,
  });

  const sessions = data?.items ?? [];

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: { title?: string; is_pinned?: boolean } }) =>
      chatApi.updateSession(id, updates),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat-sessions'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => chatApi.deleteSession(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
      if (activeId === deletedId) {
        navigate('/chat', { replace: true });
      }
    },
  });

  const handleNewChat = async () => {
    setIsCreating(true);
    try {
      const session = await chatApi.createSession('New Chat');
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
      navigate(`/chat/${session.id}`);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelect = (id: string) => {
    navigate(`/chat/${id}`);
    onSessionChange?.(id);
  };

  const handleRename = (id: string, title: string) => {
    updateMutation.mutate({ id, updates: { title } });
  };

  const handlePin = (id: string, pinned: boolean) => {
    updateMutation.mutate({ id, updates: { is_pinned: pinned } });
  };

  const handleDelete = (id: string) => setDeleteTarget(id);
  const confirmDelete = () => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget);
      setDeleteTarget(null);
    }
  };

  // Filter and group sessions
  const filtered = sessions.filter((s) =>
    s.title.toLowerCase().includes(search.toLowerCase())
  );

  const pinned = filtered.filter((s) => s.is_pinned);
  const unpinned = filtered.filter((s) => !s.is_pinned);

  // Group unpinned by date
  const groups: Record<string, ChatSession[]> = {};
  unpinned.forEach((s) => {
    const label = getGroupLabel(s.updated_at || s.created_at);
    if (!groups[label]) groups[label] = [];
    groups[label].push(s);
  });

  const groupOrder = ['Today', 'Yesterday', 'This Week', 'This Month', 'Older'];
  const sortedGroups = groupOrder.filter((g) => g in groups);

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full bg-card border-r">
        {/* Header */}
        <div className="flex items-center justify-between h-14 px-3 border-b shrink-0">
          <span className="text-sm font-semibold text-foreground">Conversations</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleNewChat}
                disabled={isCreating}
                className="h-8 w-8"
                aria-label="New chat"
              >
                {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>New chat</TooltipContent>
          </Tooltip>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations..."
              className="pl-8 h-8 text-sm"
              aria-label="Search conversations"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Session List */}
        <ScrollArea className="flex-1 px-2 py-2">
          {isLoading ? (
            <div className="space-y-1.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-8 rounded-md bg-muted animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <MessageSquare className="h-8 w-8 text-muted-foreground/40 mb-3" />
              <p className="text-sm text-muted-foreground">
                {search ? 'No conversations found' : 'No conversations yet'}
              </p>
              {!search && (
                <Button variant="ghost" size="sm" className="mt-3 text-xs" onClick={handleNewChat}>
                  Start your first chat
                </Button>
              )}
            </div>
          ) : (
            <nav aria-label="Conversation history">
              {/* Pinned */}
              {pinned.length > 0 && (
                <div className="mb-3">
                  <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Pinned
                  </p>
                  <div className="space-y-0.5">
                    {pinned.map((s) => (
                      <SessionItem
                        key={s.id}
                        session={s}
                        isActive={s.id === activeId}
                        onSelect={() => handleSelect(s.id)}
                        onRename={handleRename}
                        onPin={handlePin}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Grouped */}
              {sortedGroups.map((groupLabel) => (
                <div key={groupLabel} className="mb-3">
                  <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {groupLabel}
                  </p>
                  <div className="space-y-0.5">
                    {groups[groupLabel].map((s) => (
                      <SessionItem
                        key={s.id}
                        session={s}
                        isActive={s.id === activeId}
                        onSelect={() => handleSelect(s.id)}
                        onRename={handleRename}
                        onPin={handlePin}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </nav>
          )}
        </ScrollArea>

        {/* Delete Confirmation Dialog */}
        <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Delete conversation?</DialogTitle>
              <DialogDescription>
                This will permanently delete this conversation and all its messages. This cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
}
