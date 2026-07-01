import React from 'react';
import { MessageList } from './MessageList';
import { PromptInput } from './PromptInput';
import { useContextStore } from '@/store/useContextStore';
import { Button } from '@/components/ui/button';
import { PanelRightOpen, PanelRightClose, MessageSquare } from 'lucide-react';

export function ConversationArea() {
  const { isContextPanelOpen, toggleContextPanel } = useContextStore();

  return (
    <div className="flex flex-col h-full w-full relative">
      <div className="absolute top-4 right-4 z-10">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleContextPanel}
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
          title={isContextPanelOpen ? 'Close context panel' : 'Open context panel'}
        >
          {isContextPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
        </Button>
      </div>

      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>

      <div className="p-4 bg-background max-w-3xl mx-auto w-full">
        <PromptInput />
      </div>
    </div>
  );
}
