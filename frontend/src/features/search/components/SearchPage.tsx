import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Search, FileText, ArrowRight, AlertCircle } from 'lucide-react';
import { searchApi } from '@/services/searchApi';

/** Debounce a value by `delay` ms. */
function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function SearchPage() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounced(query.trim(), 350);
  const navigate = useNavigate();

  const {
    data,
    isFetching,
    isError,
    error,
  } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.search(debouncedQuery),
    enabled: debouncedQuery.length > 0,
    staleTime: 30_000,
  });

  const hasQuery = debouncedQuery.length > 0;
  const results = data?.results ?? [];

  return (
    <div className="p-4 sm:p-6 max-w-[800px] mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-muted-foreground mt-1">
          Hybrid search across your documents, powered by the same retrieval engine as chat.
        </p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search your documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 h-11"
          autoFocus
        />
      </div>

      {/* Idle / empty-query state */}
      {!hasQuery && (
        <div className="text-center py-16 text-muted-foreground">
          <Search className="h-8 w-8 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Start typing to search across your document library.</p>
        </div>
      )}

      {/* Loading state */}
      {hasQuery && isFetching && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {hasQuery && !isFetching && isError && (
        <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
          <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-destructive">Search failed</p>
            <p className="text-muted-foreground mt-0.5">
              {(error as Error)?.message || 'Something went wrong. Please try again.'}
            </p>
          </div>
        </div>
      )}

      {/* Empty-results state */}
      {hasQuery && !isFetching && !isError && results.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <FileText className="h-8 w-8 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No matches for "{debouncedQuery}".</p>
          <p className="text-xs mt-1">Try different keywords, or upload more documents.</p>
        </div>
      )}

      {/* Results */}
      {hasQuery && !isFetching && !isError && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {data?.total} result{data?.total === 1 ? '' : 's'} for "{debouncedQuery}"
          </p>
          {results.map((result) => (
            <Card
              key={result.chunk_id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => navigate(`/documents/${result.document_id}`)}
            >
              <CardContent className="p-4 flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate">{result.document_name}</p>
                    {result.page_number != null && (
                      <span className="text-xs text-muted-foreground shrink-0">
                        p.{result.page_number}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{result.excerpt}</p>
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
