import React, { useEffect, useRef } from 'react';
import { useConversationStore } from '@/store/useConversationStore';
import { MessageBubble } from './MessageBubble';
import { AgentTimeline } from './AgentTimeline';
import { useChatStream } from '../hooks/useChatStream';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Sparkles, AlertTriangle, RefreshCw, Bot, Loader2 } from 'lucide-react';

export function MessageList() {
  const { messages, isStreaming, streamingContent, streamError, agentStates } = useConversationStore();
  const { retry, regenerate } = useChatStream();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages, stream chunks, reasoning steps, or errors
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, streamingContent, streamError, agentStates]);

  if (messages.length === 0 && !streamingContent && !streamError && !isStreaming) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
        <Sparkles className="h-12 w-12 text-primary/50" />
        <h2 className="text-2xl font-semibold">How can I help you today?</h2>
        <p className="text-muted-foreground max-w-sm">
          Pin documents from your knowledge workspace to the Context Manager to get highly accurate answers based on your private data.
        </p>
      </div>
    );
  }

  const lastMessage = messages[messages.length - 1];
  const canRegenerate = !isStreaming && !streamError && lastMessage?.role === 'assistant';
  // Before the answer text starts streaming, show a live reasoning trace.
  const showThinking = isStreaming && !streamingContent;

  return (
    <ScrollArea className="h-full" ref={scrollRef}>
      <div className="flex flex-col pb-8">
        {messages.map((msg, i) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onRegenerate={canRegenerate && i === messages.length - 1 ? regenerate : undefined}
          />
        ))}

        {showThinking && (
          <div className="flex w-full py-6 bg-muted/30">
            <div className="max-w-4xl mx-auto w-full flex gap-4 px-4">
              <div className="flex-shrink-0 mt-1">
                <div className="h-8 w-8 rounded-md bg-secondary border flex items-center justify-center text-secondary-foreground">
                  <Bot className="h-5 w-5" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                {agentStates.length > 0 && <AgentTimeline states={agentStates} />}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{agentStates.length ? 'Composing answer…' : 'Thinking…'}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {isStreaming && streamingContent && (
          <MessageBubble
            message={{ id: 'streaming', role: 'assistant', content: streamingContent, created_at: new Date().toISOString() }}
            isStreaming={true}
          />
        )}

        {streamError && !isStreaming && (
          <div className="w-full py-6">
            <div className="max-w-4xl mx-auto w-full px-4">
              <div
                role="alert"
                className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4"
              >
                <AlertTriangle className="h-5 w-5 shrink-0 text-destructive mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">Generation failed</p>
                  <p className="text-sm text-muted-foreground mt-0.5">{streamError}</p>
                </div>
                <Button variant="outline" size="sm" onClick={retry} className="shrink-0 gap-1.5">
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
