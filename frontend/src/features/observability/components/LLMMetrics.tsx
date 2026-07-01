import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { observabilityApi } from '@/services/observabilityApi';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function LLMMetrics() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => observabilityApi.getSummary(),
  });

  if (isLoading) {
    return <div className="space-y-4"><Skeleton className="h-40 w-full" /><Skeleton className="h-80 w-full" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl font-bold">${(data?.cumulative_cost_usd ?? 0).toFixed(2)}</CardTitle>
            <CardDescription>Total Cost</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl font-bold">{(data?.total_tokens_consumed ?? 0).toLocaleString()}</CardTitle>
            <CardDescription>Total Tokens</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl font-bold">{(data?.average_latency_ms ?? 0).toFixed(0)}ms</CardTitle>
            <CardDescription>Average Latency</CardDescription>
          </CardHeader>
        </Card>
      </div>

      {data?.latencies_breakdown && Object.keys(data.latencies_breakdown).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Per-Action Latency</CardTitle>
            <CardDescription>Average latency by request type.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(data.latencies_breakdown).map(([action, latency]) => (
                <div key={action} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{action.replace('_', ' ')}</span>
                  <span className="text-sm font-medium">{(latency as number).toFixed(0)}ms</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
