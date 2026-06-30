import React from 'react';
import { cn } from '@/utils';
import { MarkdownRenderer } from './MarkdownRenderer';
import { StreamingCursor } from './StreamingCursor';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Bot, User } from 'lucide-react';

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
  className?: string;
}

export function MessageBubble({ role, content, isStreaming, className }: MessageBubbleProps) {
  const isUser = role === 'user';
  
  if (role === 'system') return null;

  return (
    <div className={cn("flex w-full space-x-4 py-4", className)}>
      <Avatar className={cn("h-8 w-8 mt-1", isUser ? "bg-secondary" : "bg-primary")}>
        {isUser ? (
          <AvatarFallback><User className="h-4 w-4 text-secondary-foreground" /></AvatarFallback>
        ) : (
          <AvatarFallback><Bot className="h-4 w-4 text-primary-foreground" /></AvatarFallback>
        )}
      </Avatar>
      
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="font-semibold text-sm text-foreground">
          {isUser ? "You" : "DocsMind AI"}
        </div>
        <div className="text-sm text-foreground/90">
          <MarkdownRenderer content={content} />
          {isStreaming && <StreamingCursor />}
        </div>
      </div>
    </div>
  );
}
