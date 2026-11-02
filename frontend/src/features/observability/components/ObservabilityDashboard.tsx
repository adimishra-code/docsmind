import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { observabilityApi } from '@/services/observabilityApi';
import { useObservabilityStore } from '@/store/useObservabilityStore';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { RetrievalMetrics } from './RetrievalMetrics';
import { LLMMetrics } from './LLMMetrics';
import { ExperimentTracker } from './ExperimentTracker';
import { Activity, Database, TerminalSquare, GitBranch, Zap, Clock, DollarSign, Hash } from 'lucide-react';

function StatCard({ title, value, subtitle, icon: Icon, loading }: {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function ObservabilityDashboard() {
  const { activeTab, setActiveTab } = useObservabilityStore();

  const { data: analytics, isLoading, isError } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => observabilityApi.getSummary(),
    staleTime: 60_000,
  });

  const formatTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

  return (
    <div className="flex flex-col h-full p-4 sm:p-6 overflow-y-auto animate-fade-in">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Monitor retrieval quality and LLM performance.</p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full space-y-6">
        <div className="overflow-x-auto no-scrollbar pb-1">
          <TabsList className="flex w-max sm:grid sm:w-full sm:grid-cols-4 sm:max-w-xl">
            <TabsTrigger value="overview" className="gap-1.5 text-xs px-3 sm:px-2">
              <Activity className="h-3.5 w-3.5" /> Overview
            </TabsTrigger>
            <TabsTrigger value="retrieval" className="gap-1.5 text-xs px-3 sm:px-2">
              <Database className="h-3.5 w-3.5" /> Retrieval
            </TabsTrigger>
            <TabsTrigger value="llm" className="gap-1.5 text-xs px-3 sm:px-2">
              <TerminalSquare className="h-3.5 w-3.5" /> LLM
            </TabsTrigger>
            <TabsTrigger value="experiments" className="gap-1.5 text-xs px-3 sm:px-2">
              <GitBranch className="h-3.5 w-3.5" /> Experiments
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="overview" className="m-0 space-y-6">
          {isError ? (
            <div className="p-8 border rounded-lg bg-card text-center text-muted-foreground text-sm">
              Unable to load analytics. Make sure the backend is running.
            </div>
          ) : (
            <>
              {/* Key Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <StatCard
                  title="Total Requests"
                  value={analytics ? String(analytics.total_requests) : '0'}
                  icon={Hash}
                  loading={isLoading}
                />
                <StatCard
                  title="Avg. Latency"
                  value={analytics ? `${analytics.average_latency_ms.toFixed(0)} ms` : '0 ms'}
                  subtitle="Per RAG request"
                  icon={Clock}
                  loading={isLoading}
                />
                <StatCard
                  title="Tokens Used"
                  value={analytics ? formatTokens(analytics.total_tokens_consumed) : '0'}
                  subtitle="All time"
                  icon={Zap}
                  loading={isLoading}
                />
                <StatCard
                  title="Total Cost"
                  value={analytics ? `$${analytics.cumulative_cost_usd.toFixed(4)}` : '$0.0000'}
                  subtitle="Estimated"
                  icon={DollarSign}
                  loading={isLoading}
                />
              </div>

              {/* Top Topics */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Top Searched Topics</CardTitle>
                  <CardDescription>Most frequent keywords in your queries</CardDescription>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
                    </div>
                  ) : !analytics || analytics.most_searched_topics.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No search data yet. Start chatting to see your top topics.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {analytics.most_searched_topics.map(({ topic, count }, i) => {
                        const max = analytics.most_searched_topics[0]?.count ?? 1;
                        const pct = Math.round((count / max) * 100);
                        return (
                          <div key={topic} className="flex items-center gap-3">
                            <span className="text-xs text-muted-foreground w-4">{i + 1}</span>
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium capitalize">{topic}</span>
                                <span className="text-xs text-muted-foreground">{count}×</span>
                              </div>
                              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-primary rounded-full transition-all duration-500"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Latency Breakdown */}
              {analytics && Object.keys(analytics.latencies_breakdown).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Latency Breakdown by Action</CardTitle>
                    <CardDescription>Average latency in milliseconds per operation type</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(analytics.latencies_breakdown)
                        .sort(([, a], [, b]) => b - a)
                        .map(([action, latency]) => (
                          <div key={action} className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground capitalize">{action.replace(/_/g, ' ')}</span>
                            <span className="font-medium tabular-nums">{latency.toFixed(0)} ms</span>
                          </div>
                        ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        <TabsContent value="retrieval" className="m-0">
          <RetrievalMetrics />
        </TabsContent>

        <TabsContent value="llm" className="m-0">
          <LLMMetrics />
        </TabsContent>

        <TabsContent value="experiments" className="m-0">
          <ExperimentTracker />
        </TabsContent>
      </Tabs>
    </div>
  );
}
