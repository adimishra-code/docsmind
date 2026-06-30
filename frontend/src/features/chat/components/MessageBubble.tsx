import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css'; // or any highlight style you prefer
import { Message } from '@/services/chatApi';
import { cn } from '@/utils';
import { Bot, User } from 'lucide-react';
import { CitationCard } from './CitationCard'; // we'll build this next

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={cn("flex w-full py-6", isUser ? "bg-background" : "bg-muted/30")}>
      <div className="max-w-4xl mx-auto w-full flex gap-4 px-4">
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              <User className="h-5 w-5" />
            </div>
          ) : (
            <div className="h-8 w-8 rounded-md bg-secondary border flex items-center justify-center text-secondary-foreground">
              <Bot className="h-5 w-5" />
            </div>
          )}
        </div>
        
        <div className="flex-1 min-w-0 prose prose-neutral dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              a: ({ node, ...props }) => {
                // Intercept citations like [1]
                const match = props.children?.toString().match(/^\[(\d+)\]$/);
                if (match && message.citations) {
                  const citationIndex = parseInt(match[1]) - 1;
                  const citation = message.citations[citationIndex];
                  if (citation) {
                    return <CitationCard citation={citation} index={citationIndex + 1} />;
                  }
                }
                return <a {...props} className="text-primary hover:underline" />;
              }
            }}
          >
            {message.content + (isStreaming ? ' ▍' : '')}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
