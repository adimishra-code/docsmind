import React, { useState, useRef, KeyboardEvent } from 'react';
import TextareaAutosize from 'react-textarea-autosize';
import { Button } from '@/components/ui/button';
import { Send, Paperclip, StopCircle } from 'lucide-react';
import { useConversationStore } from '@/store/useConversationStore';
import { useChatStream } from '../hooks/useChatStream';

export function PromptInput() {
  const [prompt, setPrompt] = useState('');
  const { isStreaming, addMessage } = useConversationStore();
  const { streamChat, abortStream } = useChatStream();
  const formRef = useRef<HTMLFormElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isStreaming) return;

    const userMessage = prompt;
    setPrompt('');

    // Add user message to store immediately
    addMessage({
      id: `msg-user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    });

    // Initiate streaming request
    await streamChat(userMessage);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  return (
    <form ref={formRef} onSubmit={handleSubmit} className="relative flex w-full items-end gap-2 bg-background border rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary transition-shadow">
      <Button type="button" variant="ghost" size="icon" className="shrink-0 h-10 w-10 rounded-full text-muted-foreground hover:text-foreground">
        <Paperclip className="h-5 w-5" />
      </Button>

      <TextareaAutosize
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question or use / for commands..."
        className="flex-1 max-h-60 min-h-[40px] resize-none bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
        maxRows={8}
        disabled={isStreaming}
      />

      {isStreaming ? (
        <Button 
          type="button" 
          onClick={abortStream}
          size="icon" 
          className="shrink-0 h-10 w-10 rounded-full bg-destructive hover:bg-destructive/90 text-destructive-foreground animate-pulse"
        >
          <StopCircle className="h-5 w-5" />
        </Button>
      ) : (
        <Button 
          type="submit" 
          size="icon" 
          disabled={!prompt.trim()}
          className="shrink-0 h-10 w-10 rounded-full"
        >
          <Send className="h-5 w-5" />
        </Button>
      )}
    </form>
  );
}
