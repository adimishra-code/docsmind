import React from 'react';
import { MessageList } from './MessageList';
import { PromptInput } from './PromptInput';
import { useContextStore } from '@/store/useContextStore';
import { Button } from '@/components/ui/button';
import { PanelRightOpen, PanelRightClose } from 'lucide-react';

export function ConversationArea() {
  const { isContextPanelOpen, toggleContextPanel } = useContextStore();

  return (
    <div className="flex flex-col h-full w-full relative">
      <div className="absolute top-4 right-4 z-10">
        <Button 
          variant="outline" 
          size="icon" 
          onClick={toggleContextPanel}
          title={isContextPanelOpen ? "Close Context Manager" : "Open Context Manager"}
        >
          {isContextPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
        </Button>
      </div>

      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      <div className="p-4 bg-background max-w-4xl mx-auto w-full">
        <PromptInput />
      </div>
    </div>
  );
}
