import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { cn } from '@/utils';
import { Button } from '@/components/ui/button';

interface CodeBlockProps {
  language: string;
  code: string;
  className?: string;
}

export function CodeBlock({ language, code, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("relative my-4 rounded-lg overflow-hidden border bg-zinc-950", className)}>
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900 text-zinc-400 text-xs font-mono">
        <span>{language}</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
          onClick={handleCopy}
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </Button>
      </div>
      <div className="p-4 overflow-x-auto text-sm font-mono text-zinc-100">
        <pre>
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
