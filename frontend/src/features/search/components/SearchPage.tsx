import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, FileText, MessageSquare, ArrowRight } from 'lucide-react';

export function SearchPage() {
  const [query, setQuery] = useState('');

  return (
    <div className="p-6 max-w-[800px] mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-muted-foreground mt-1">Find information across all your documents.</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search documents, conversations, and more..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 h-11"
        />
      </div>

      {!query && (
        <div className="space-y-4 mt-8">
          <p className="text-sm text-muted-foreground">Recent searches</p>
          {['Q3 revenue analysis', 'Engineering spec', 'API documentation'].map((item) => (
            <button
              key={item}
              onClick={() => setQuery(item)}
              className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-accent transition-colors"
            >
              <Search className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="text-sm">{item}</span>
            </button>
          ))}
        </div>
      )}

      {query && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Results for "{query}"</p>
          {[
            { type: 'document', title: 'Sample Document', snippet: 'This is a sample result...' },
            { type: 'conversation', title: 'Chat about ' + query, snippet: 'Previous conversation...' },
          ].map((result, i) => (
            <Card key={i} className="cursor-pointer hover:border-primary/50 transition-colors">
              <CardContent className="p-4 flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                  {result.type === 'document' ? (
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{result.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{result.snippet}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
