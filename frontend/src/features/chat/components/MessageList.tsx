import React, { useEffect, useRef } from 'react';
import { useConversationStore } from '@/store/useConversationStore';
import { MessageBubble } from './MessageBubble';
import { AgentTimeline } from './AgentTimeline';
import { useChatStream } from '../hooks/useChatStream';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Sparkles, AlertTriangle, RefreshCw, Bot } from 'lucide-react';

export function MessageList() {
  const { messages, isStreaming, streamingContent, streamingCitations, streamError, agentStates, streamMeta, streamStartedAt } =
    useConversationStore();
  const { retry, regenerate } = useChatStream();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Helper to synchronously check if the user is near the bottom.
  // This prevents fighting the user if they scroll up to read earlier messages during a stream.
  const isNearBottom = () => {
    const vp = bottomRef.current?.closest<HTMLElement>('[data-radix-scroll-area-viewport]');
    if (!vp) return true; // Default to true if not found
    // 100px threshold
    return Math.abs(vp.scrollHeight - vp.scrollTop - vp.clientHeight) < 100;
  };

  // During streaming: set scrollTop directly (instant) on every token so we
  // never queue up multiple queued smooth-scroll animations that fight each
  // other and yank the view. Also fires on agent-state ticks and
  // isStreaming toggle so the thinking indicator scrolls into view.
  useEffect(() => {
    if (!isNearBottom()) return;
    const vp = bottomRef.current?.closest<HTMLElement>('[data-radix-scroll-area-viewport]');
    if (vp) vp.scrollTop = vp.scrollHeight;
  }, [streamingContent, agentStates.length, isStreaming]);

  // After a message is committed (or an error appears): one smooth scroll.
  // Runs only when the count changes — not on every token — so it never
  // interrupts someone who has already scrolled up to read earlier messages.
  useEffect(() => {
    if (!isNearBottom()) return;
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, streamError]);

  // Empty conversation: guided prompt to help the user get started.
  if (messages.length === 0 && !streamingContent && !streamError && !isStreaming) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center space-y-3 px-8">
        <div className="h-12 w-12 rounded-2xl bg-primary/8 flex items-center justify-center">
          <Sparkles className="h-6 w-6 text-primary/70" />
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">Ask anything</h2>
          <p className="text-sm text-muted-foreground max-w-xs leading-relaxed">
            Pin documents in the Context panel to ground answers in your own files.
          </p>
        </div>
      </div>
    );
  }

  const lastMessage = messages[messages.length - 1];
  const canRegenerate = !isStreaming && !streamError && lastMessage?.role === 'assistant';
  // Before any tokens arrive, show the live reasoning trace.
  const showThinking = isStreaming && !streamingContent;

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col pb-6">
        {messages.map((msg, i) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onRegenerate={canRegenerate && i === messages.length - 1 ? regenerate : undefined}
          />
        ))}

        {/* Thinking / reasoning indicator — shown before the first token */}
        {showThinking && (
          <div className="flex w-full py-5 bg-muted/40">
            <div className="max-w-3xl mx-auto w-full flex gap-4 px-4">
              <div className="flex-shrink-0 mt-0.5">
                <div className="h-7 w-7 rounded-md bg-secondary border border-border flex items-center justify-center text-secondary-foreground">
                  <Bot className="h-4 w-4" />
                </div>
              </div>
              <div className="flex-1 min-w-0 pt-1">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-2 select-none">
                  DocsMind
                </p>
                <AgentTimeline
                  states={agentStates}
                  streaming={false}
                  provider={streamMeta?.provider}
                  startedAt={streamStartedAt}
                />
              </div>
            </div>
          </div>
        )}

        {/* Live streaming bubble — appears once the first token arrives */}
        {isStreaming && streamingContent && (
          <MessageBubble
            message={{
              id: 'streaming',
              role: 'assistant',
              content: streamingContent,
              created_at: new Date().toISOString(),
              citations: streamingCitations?.length ? (streamingCitations as any[]) : undefined,
            }}
            isStreaming
          />
        )}

        {/* Error state */}
        {streamError && !isStreaming && (
          <div className="w-full py-5">
            <div className="max-w-3xl mx-auto w-full px-4">
              <div
                role="alert"
                className="flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3.5"
              >
                <AlertTriangle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">Generation failed</p>
                  <p className="text-sm text-muted-foreground mt-0.5 leading-relaxed">{streamError}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={retry}
                  className="shrink-0 gap-1.5 text-xs h-8"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={bottomRef} aria-hidden className="h-px" />
      </div>
    </ScrollArea>
  );
}
