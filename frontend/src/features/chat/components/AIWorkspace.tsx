import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { ConversationArea } from './ConversationArea';
import { ConversationSidebar } from './ConversationSidebar';
import { ContextManager } from './ContextManager';
import { useContextStore } from '@/store/useContextStore';
import { useConversationStore } from '@/store/useConversationStore';
import { chatApi } from '@/services/chatApi';
import { Skeleton } from '@/components/ui/skeleton';

export function AIWorkspace() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isContextPanelOpen } = useContextStore();
  const { setActiveSession, setMessages } = useConversationStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      if (!id) {
        // No session in URL — don't create one yet; let the sidebar handle it
        setActiveSession(null);
        setMessages([]);
        return;
      }

      setLoading(true);
      try {
        // Load the session and its existing messages
        const session = await chatApi.getSession(id);
        if (!cancelled) {
          setActiveSession(session.id);
          // Restore message history from the server
          if (session.messages && session.messages.length > 0) {
            setMessages(session.messages);
          } else {
            setMessages([]);
          }
        }
      } catch (err) {
        console.error('Failed to load chat session:', err);
        if (!cancelled) {
          // Session not found or access denied — redirect to /chat
          navigate('/chat', { replace: true });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => { cancelled = true; };
  }, [id, setActiveSession, setMessages, navigate]);

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      <ResizablePanelGroup orientation="horizontal" className="h-full w-full">
        {/* Conversation Sidebar */}
        <ResizablePanel defaultSize={22} minSize={15} maxSize={35} className="border-r">
          <ConversationSidebar />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Main Chat Area */}
        <ResizablePanel defaultSize={isContextPanelOpen ? 53 : 78} minSize={40}>
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
              <p className="text-muted-foreground text-sm mt-2 max-w-xs">
                Select a conversation from the sidebar or create a new one to start chatting with your documents.
              </p>
            </div>
          ) : (
            <ConversationArea />
          )}
        </ResizablePanel>

        {/* Context Panel */}
        {isContextPanelOpen && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={25} minSize={20} maxSize={40} className="border-l bg-muted/30">
              <ContextManager />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  );
}
