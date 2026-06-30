import React, { useEffect, useRef } from 'react';
import { useConversationStore } from '@/store/useConversationStore';
import { MessageBubble } from './MessageBubble';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sparkles } from 'lucide-react';

export function MessageList() {
  const { messages, isStreaming, streamingContent } = useConversationStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or stream chunks
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, streamingContent]);

  if (messages.length === 0 && !streamingContent) {
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

  return (
    <ScrollArea className="h-full" ref={scrollRef}>
      <div className="flex flex-col pb-8">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isStreaming && streamingContent && (
          <MessageBubble 
            message={{ id: 'streaming', role: 'assistant', content: streamingContent, created_at: new Date().toISOString() }} 
            isStreaming={true} 
          />
        )}
      </div>
    </ScrollArea>
  );
}
