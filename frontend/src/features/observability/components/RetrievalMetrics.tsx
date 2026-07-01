import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { observabilityApi } from '@/services/observabilityApi';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function RetrievalMetrics() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => observabilityApi.getSummary(),
  });

  if (isLoading) {
    return <div className="space-y-4"><Skeleton className="h-40 w-full" /><Skeleton className="h-80 w-full" /></div>;
  }

  const keywordData = (data?.most_searched_topics ?? []).map((kw) => ({ name: kw.topic, count: kw.count }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl font-bold">{data?.total_requests ?? 0}</CardTitle>
            <CardDescription>Total Requests</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl font-bold">{(data?.average_latency_ms ?? 0).toFixed(0)}ms</CardTitle>
            <CardDescription>Average Latency</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl font-bold">{(data?.total_tokens_consumed ?? 0).toLocaleString()}</CardTitle>
            <CardDescription>Tokens Consumed</CardDescription>
          </CardHeader>
        </Card>
      </div>

      {keywordData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Top Search Keywords</CardTitle>
            <CardDescription>Most frequent search terms across your queries.</CardDescription>
          </CardHeader>
          <CardContent className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={keywordData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
