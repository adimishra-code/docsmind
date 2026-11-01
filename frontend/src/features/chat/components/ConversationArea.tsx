import React from 'react';
import { MessageList } from './MessageList';
import { PromptInput } from './PromptInput';
export function ConversationArea() {
  return (
    <div className="flex flex-col h-full w-full relative">
      {/* Message list fills the remaining space */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>

      {/* Input bar — fixed to the bottom, never overflows */}
      <div className="shrink-0 border-t bg-background/95 backdrop-blur-sm">
        <div className="mx-auto w-full max-w-3xl px-4 py-3">
          <PromptInput />
          <p className="mt-1.5 text-center text-[11px] text-muted-foreground/50 select-none">
            Answers are grounded in your documents and may contain errors.
          </p>
        </div>
      </div>
    </div>
  );
}
