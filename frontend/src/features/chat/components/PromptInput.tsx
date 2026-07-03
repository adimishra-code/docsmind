import React, { useState, useRef, KeyboardEvent } from 'react';
import TextareaAutosize from 'react-textarea-autosize';
import { Button } from '@/components/ui/button';
import { Send, StopCircle } from 'lucide-react';
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

    addMessage({
      id: `msg-user-${Date.now()}`,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    });

    await streamChat(userMessage);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className="relative flex w-full items-end gap-2 bg-card border rounded-xl p-2 pl-3.5 shadow-sm focus-within:ring-1 focus-within:ring-ring transition-all duration-150"
    >
      <TextareaAutosize
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question..."
        className="flex-1 max-h-60 min-h-[36px] resize-none bg-transparent py-2.5 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
        maxRows={8}
        disabled={isStreaming}
      />

      {isStreaming ? (
        <Button
          type="button"
          onClick={abortStream}
          size="icon"
          className="shrink-0 h-9 w-9 rounded-lg bg-destructive hover:bg-destructive/90 text-destructive-foreground"
        >
          <StopCircle className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          type="submit"
          size="icon"
          disabled={!prompt.trim()}
          className="shrink-0 h-9 w-9 rounded-lg"
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </form>
  );
}
