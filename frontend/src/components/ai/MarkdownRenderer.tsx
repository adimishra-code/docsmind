import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { CodeBlock } from './CodeBlock';
import { CitationBadge } from './CitationBadge';
import { cn } from '@/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  onCitationClick?: (citationId: string) => void;
}

export function MarkdownRenderer({ content, className, onCitationClick }: MarkdownRendererProps) {
  // Regex to find [N] citations and replace them with a custom placeholder or process them
  // For simplicity, we can intercept standard links or use a custom remark plugin.
  // Here we use standard react-markdown capabilities.

  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        rehypePlugins={[rehypeHighlight]}
        components={{
          code(props: any) {
            const { children, className, node, ...rest } = props;
            const match = /language-(\w+)/.exec(className || '');
            return match ? (
              <CodeBlock
                language={match[1]}
                code={String(children).replace(/\n$/, '')}
                {...rest}
              />
            ) : (
              <code className={cn("bg-muted px-1.5 py-0.5 rounded-md font-mono text-sm", className)} {...rest}>
                {children}
              </code>
            );
          },
          a(props: any) {
            const { href, children } = props;
            // Intercept internal citation links if they follow a specific pattern, e.g., #cite-1
            if (href?.startsWith('#cite-')) {
              const citeId = href.replace('#cite-', '');
              return <CitationBadge id={citeId} onClick={() => onCitationClick?.(citeId)} />;
            }
            return <a href={href} target="_blank" rel="noreferrer" className="text-primary hover:underline">{children}</a>;
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
