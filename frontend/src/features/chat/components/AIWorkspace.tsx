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
import { PanelLeftOpen, PanelRightOpen } from 'lucide-react';

export function AIWorkspace() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    isContextPanelOpen,
    isConversationPanelOpen,
    toggleConversationPanel,
    toggleContextPanel,
    setConversationPanelOpen,
    setContextPanelOpen,
  } = useContextStore();

  const sidebarRef = usePanelRef();
  const contextRef = usePanelRef();

  const { setActiveSession, setMessages } = useConversationStore();
  const [loading, setLoading] = useState(false);

  // Store → panel: drive collapse/expand only when the panel's *actual* state
  // disagrees with the store. Comparing against isCollapsed() (not blindly
  // calling expand/collapse) keeps a programmatic change and a user drag from
  // fighting each other.
  useEffect(() => {
    const panel = sidebarRef.current;
    if (!panel) return;
    if (isConversationPanelOpen && panel.isCollapsed()) panel.expand();
    else if (!isConversationPanelOpen && !panel.isCollapsed()) panel.collapse();
  }, [isConversationPanelOpen, sidebarRef]);

  useEffect(() => {
    const panel = contextRef.current;
    if (!panel) return;
    if (isContextPanelOpen && panel.isCollapsed()) panel.expand();
    else if (!isContextPanelOpen && !panel.isCollapsed()) panel.collapse();
  }, [isContextPanelOpen, contextRef]);

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
        {/* Conversation Sidebar — always in DOM, collapses to 0 */}
        <ResizablePanel
          panelRef={sidebarRef}
          id="sidebar"
          defaultSize={sidebarDefault}
          minSize="15"
          maxSize="30"
          collapsible
          collapsedSize="0"
          onResize={(size) => {
            // Read the numerical size directly to avoid thrashing during drag.
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
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Skeleton className="h-8 w-48" />
            </div>
          ) : !id ? (
            <div className="flex flex-col h-full items-center justify-center text-center p-8">
              <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold tracking-tight">Start a conversation</h2>
              <p className="text-muted-foreground text-sm mt-2 max-w-xs mb-6">
                Select a conversation from the sidebar or create a new one to start chatting with your documents.
              </p>
              <Button onClick={async () => {
                setLoading(true);
                try {
                  const session = await chatApi.createSession('New Chat');
                  navigate(`/chat/${session.id}`);
                } catch (err) {
                  console.error('Failed to create chat:', err);
                } finally {
                  setLoading(false);
                }
              }}>
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create New Chat
              </Button>
            </div>
          ) : (
            <ConversationArea />
          )}
        </ResizablePanel>

        {/* Context Panel — always in DOM, collapses to 0 */}
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
