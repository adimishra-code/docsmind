import React from 'react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { ConversationArea } from './ConversationArea';
import { ContextManager } from './ContextManager';
import { useContextStore } from '@/store/useContextStore';

export function AIWorkspace() {
  const { isContextPanelOpen } = useContextStore();

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={75} minSize={50} className="flex-1 relative">
          <ConversationArea />
        </ResizablePanel>
        
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
