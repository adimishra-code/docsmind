import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { usePanelRef } from 'react-resizable-panels';
import { ConversationArea } from './ConversationArea';
import { ConversationSidebar } from './ConversationSidebar';
import { ContextManager } from './ContextManager';
import { useContextStore } from '@/store/useContextStore';
import { useConversationStore } from '@/store/useConversationStore';
import { chatApi } from '@/services/chatApi';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { PanelLeftOpen, PanelRightOpen, MessageSquare, BookOpen, Plus } from 'lucide-react';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function AIWorkspace() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const {
    isContextPanelOpen,
    isConversationPanelOpen,
    toggleConversationPanel,
    toggleContextPanel,
    setConversationPanelOpen,
    setContextPanelOpen,
    isMobileChatsOpen,
    isMobileContextOpen,
    setMobileChatsOpen,
    setMobileContextOpen,
    toggleMobileChats,
    toggleMobileContext,
    pinnedDocuments,
  } = useContextStore();

  const sidebarRef = usePanelRef();
  const contextRef = usePanelRef();

  const { setActiveSession, setMessages } = useConversationStore();
  const [loading, setLoading] = useState(false);

  // Store → panel (Desktop only): drive collapse/expand only when the panel's *actual* state disagrees
  useEffect(() => {
    if (!isDesktop) return;
    const panel = sidebarRef.current;
    if (!panel) return;
    if (isConversationPanelOpen && panel.isCollapsed()) panel.expand();
    else if (!isConversationPanelOpen && !panel.isCollapsed()) panel.collapse();
  }, [isDesktop, isConversationPanelOpen, sidebarRef]);

  useEffect(() => {
    if (!isDesktop) return;
    const panel = contextRef.current;
    if (!panel) return;
    if (isContextPanelOpen && panel.isCollapsed()) panel.expand();
    else if (!isContextPanelOpen && !panel.isCollapsed()) panel.collapse();
  }, [isDesktop, isContextPanelOpen, contextRef]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      if (!id) {
        setActiveSession(null);
        setMessages([]);
        return;
      }

      setLoading(true);
      try {
        const session = await chatApi.getSession(id);
        if (!cancelled) {
          setActiveSession(session.id);
          if (session.messages && session.messages.length > 0) {
            setMessages(session.messages);
          } else {
            setMessages([]);
          }
        }
      } catch (err) {
        console.error('Failed to load chat session:', err);
        if (!cancelled) {
          navigate('/chat', { replace: true });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => { cancelled = true; };
  }, [id, setActiveSession, setMessages, navigate]);

  // Initial sizes summing to 100 based on which panels start open
  const sidebarDefault = isConversationPanelOpen ? "20" : "0";
  const contextDefault = isContextPanelOpen ? "25" : "0";
  const mainDefault = `${100 - (isConversationPanelOpen ? 20 : 0) - (isContextPanelOpen ? 25 : 0)}`;

  const mainContent = loading ? (
    <div className="flex h-full items-center justify-center">
      <Skeleton className="h-8 w-48" />
    </div>
  ) : !id ? (
    <div className="flex flex-col h-full items-center justify-center text-center p-6 sm:p-8">
      <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
        <MessageSquare className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-semibold tracking-tight">Start a conversation</h2>
      <p className="text-muted-foreground text-sm mt-2 max-w-xs mb-6">
        Select a conversation from the sidebar or create a new one to start chatting with your documents.
      </p>
      <Button
        onClick={async () => {
          setLoading(true);
          try {
            const session = await chatApi.createSession('New Chat');
            navigate(`/chat/${session.id}`);
          } catch (err) {
            console.error('Failed to create chat:', err);
          } finally {
            setLoading(false);
          }
        }}
        className="gap-2"
      >
        <Plus className="h-4 w-4" />
        Create New Chat
      </Button>
    </div>
  ) : (
    <ConversationArea />
  );

  // Tablet & Mobile View (< 1024px): Single pane chat + slide-over drawer sheets
  if (!isDesktop) {
    return (
      <div className="relative flex flex-col h-full w-full overflow-hidden bg-background">
        {/* Mobile/Tablet Chat Header Bar */}
        <div className="flex items-center justify-between border-b px-3 h-11 bg-background/90 backdrop-blur-sm shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleMobileChats}
            className="h-8 gap-1.5 px-2 text-xs font-medium text-muted-foreground hover:text-foreground"
            aria-label="Open chats drawer"
          >
            <PanelLeftOpen className="h-4 w-4" />
            <span>Chats</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={toggleMobileContext}
            className="h-8 gap-1.5 px-2 text-xs font-medium text-muted-foreground hover:text-foreground"
            aria-label="Open context drawer"
          >
            <BookOpen className="h-4 w-4" />
            <span>Context</span>
            {pinnedDocuments.length > 0 && (
              <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary/15 px-1 text-[10px] font-semibold text-primary">
                {pinnedDocuments.length}
              </span>
            )}
          </Button>
        </div>

        {/* Full-width Main Chat Area */}
        <div className="flex-1 overflow-hidden min-w-0">
          {mainContent}
        </div>

        {/* Mobile Slide-Over Sheets */}
        <Sheet open={isMobileChatsOpen} onOpenChange={setMobileChatsOpen}>
          <SheetContent side="left" hideCloseButton className="p-0 w-[300px] sm:w-[360px]">
            <ConversationSidebar
              hideCollapseButton
              onClose={() => setMobileChatsOpen(false)}
              onSessionChange={() => setMobileChatsOpen(false)}
            />
          </SheetContent>
        </Sheet>

        <Sheet open={isMobileContextOpen} onOpenChange={setMobileContextOpen}>
          <SheetContent side="right" hideCloseButton className="p-0 w-[300px] sm:w-[360px]">
            <div className="h-full bg-muted/30">
              <ContextManager
                hideCloseButton
                onClose={() => setMobileContextOpen(false)}
              />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    );
  }

  // Desktop View (>= 1024px): 3-panel Resizable layout
  return (
    <div className="relative flex h-full w-full overflow-hidden bg-background">
      {/* Reopen affordance — visible only when conversation panel is collapsed */}
      {!isConversationPanelOpen && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleConversationPanel}
                className="absolute left-3 top-3 z-20 h-8 w-8 text-muted-foreground hover:text-foreground"
                aria-label="Open conversation panel"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Conversations</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      {/* Reopen affordance — visible only when context panel is collapsed */}
      {!isContextPanelOpen && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleContextPanel}
                className="absolute right-3 top-3 z-20 h-8 w-8 text-muted-foreground hover:text-foreground"
                aria-label="Open context panel"
              >
                <PanelRightOpen className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">Context</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      <ResizablePanelGroup id="workspace-group" orientation="horizontal" className="h-full w-full">
        {/* Conversation Sidebar */}
        <ResizablePanel
          panelRef={sidebarRef}
          id="sidebar"
          defaultSize={sidebarDefault}
          minSize="15"
          maxSize="30"
          collapsible
          collapsedSize="0"
          onResize={(size) => {
            const isNowOpen = size.asPercentage > 0;
            if (isNowOpen !== useContextStore.getState().isConversationPanelOpen) {
              setConversationPanelOpen(isNowOpen);
            }
          }}
          className="overflow-hidden"
        >
          <ConversationSidebar />
        </ResizablePanel>

        {isConversationPanelOpen && <ResizableHandle withHandle />}

        {/* Main Chat Area */}
        <ResizablePanel id="main" defaultSize={mainDefault} minSize="40">
          {mainContent}
        </ResizablePanel>

        {/* Context Panel */}
        {isContextPanelOpen && <ResizableHandle withHandle />}
        <ResizablePanel
          panelRef={contextRef}
          id="context"
          defaultSize={contextDefault}
          minSize="20"
          maxSize="40"
          collapsible
          collapsedSize="0"
          onResize={(size) => {
            const isNowOpen = size.asPercentage > 0;
            if (isNowOpen !== useContextStore.getState().isContextPanelOpen) {
              setContextPanelOpen(isNowOpen);
            }
          }}
          className="overflow-hidden"
        >
          <div className="h-full bg-muted/30">
            <ContextManager />
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
