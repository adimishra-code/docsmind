import React, { useState, useRef, KeyboardEvent } from 'react';
import TextareaAutosize from 'react-textarea-autosize';
import { Button } from '@/components/ui/button';
import { Send, StopCircle } from 'lucide-react';
import { useConversationStore } from '@/store/useConversationStore';
import { useChatStream } from '../hooks/useChatStream';
import { useContextStore } from '@/store/useContextStore';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import { useMediaQuery } from '@/hooks/useMediaQuery';

export function PromptInput() {
  const [prompt, setPrompt] = useState('');
  const { isStreaming, addMessage } = useConversationStore();
  const { streamChat, abortStream } = useChatStream();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const {
    isContextPanelOpen,
    toggleContextPanel,
    isMobileContextOpen,
    toggleMobileContext,
  } = useContextStore();

  const isContextOpen = isDesktop ? isContextPanelOpen : isMobileContextOpen;
  const handleToggleContext = () => {
    if (isDesktop) {
      toggleContextPanel();
    } else {
      toggleMobileContext();
    }
  };
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
      // One clean surface — the form is the only visible border.
      // focus-within darkens it slightly; no secondary ring.
      className="relative flex w-full items-end gap-2 rounded-xl border bg-card px-2.5 py-2 shadow-sm transition-colors duration-150 focus-within:border-foreground/30"
    >
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={handleToggleContext}
              className="shrink-0 h-9 w-9 text-muted-foreground hover:text-foreground mb-0.5"
              aria-label="Toggle context panel"
            >
              {isContextOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">
            {isContextOpen ? 'Close context panel' : 'Open context panel'}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TextareaAutosize
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={isStreaming ? 'Generating…' : 'Ask about your documents…'}
        // Suppress ALL browser/global focus indicators so the form border is the
        // sole affordance — prevents the classic "box inside a box" double border.
        className="flex-1 max-h-60 min-h-[36px] resize-none appearance-none border-0 bg-transparent py-2 text-sm shadow-none outline-none ring-0 focus:border-0 focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60 disabled:opacity-50"
        maxRows={8}
        disabled={isStreaming}
      />

      {isStreaming ? (
        <Button
          type="button"
          onClick={abortStream}
          size="icon"
          title="Stop generation"
          className="shrink-0 h-9 w-9 rounded-lg bg-destructive hover:bg-destructive/90 text-destructive-foreground focus-visible:ring-0 focus-visible:ring-offset-0 transition-colors duration-150 mb-0.5"
          aria-label="Stop generation"
        >
          <StopCircle className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          type="submit"
          size="icon"
          disabled={!prompt.trim()}
          title="Send (Enter)"
          className="shrink-0 h-9 w-9 rounded-lg focus-visible:ring-0 focus-visible:ring-offset-0 transition-opacity duration-150 mb-0.5"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </form>
  );
}
