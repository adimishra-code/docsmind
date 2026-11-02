import React from 'react';
import { useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatGrid } from '@/components/analytics/StatGrid';
import { documentsApi, isDocumentProcessing } from '@/services/documentsApi';
import { chatApi } from '@/services/chatApi';
import { observabilityApi } from '@/services/observabilityApi';
import { useAuthStore } from '@/store/useAuthStore';
import {
  FileText,
  MessageSquare,
  Search,
  Upload,
  Clock,
  ArrowRight,
  Zap,
  BarChart3,
  FolderOpen,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const QUICK_ACTIONS = [
  {
    icon: Upload,
    label: 'Upload Document',
    description: 'Add a new document to your knowledge base',
    href: '/documents?upload=true',
  },
  {
    icon: MessageSquare,
    label: 'Start a Chat',
    description: 'Ask questions about your documents',
    href: '/chat',
  },
  {
    icon: Search,
    label: 'Search',
    description: 'Find information across all documents',
    href: '/search',
  },
  {
    icon: BarChart3,
    label: 'View Analytics',
    description: 'Monitor retrieval quality and usage',
    href: '/observability',
  },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function Dashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'there';

  const { data: docsData, isLoading: docsLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.getAll({ limit: 10 }),
    staleTime: 60_000,
    // Keep recent activity + counts live while any document is still ingesting;
    // stop once everything reaches a terminal state. Mirrors the workspace grid.
    refetchInterval: (query) =>
      (query.state.data?.items ?? []).some((d) => isDocumentProcessing(d.status)) ? 4000 : false,
  });

  const { data: chatsData, isLoading: chatsLoading } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => chatApi.getSessions({ limit: 10 }),
    staleTime: 60_000,
  });

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => observabilityApi.getSummary(),
    staleTime: 120_000,
  });

  // Real workspace/knowledge-base status (never estimated). Kept live while any
  // document is still being ingested.
  const { data: health } = useQuery({
    queryKey: ['workspace-health'],
    queryFn: () => observabilityApi.getHealth(),
    staleTime: 60_000,
    refetchInterval: (query) => ((query.state.data?.processing_documents ?? 0) > 0 ? 4000 : false),
  });

  const STATS = [
    {
      id: 'docs',
      title: 'Documents',
      value: docsLoading ? null : String(docsData?.total ?? 0),
      icon: FileText,
    },
    {
      id: 'chats',
      title: 'Conversations',
      value: chatsLoading ? null : String(chatsData?.total ?? 0),
      icon: MessageSquare,
    },
    {
      id: 'tokens',
      title: 'Tokens Used',
      value: analyticsLoading ? null : formatNumber(analytics?.total_tokens_consumed ?? 0),
      icon: Zap,
    },
    {
      id: 'requests',
      title: 'Total Requests',
      value: analyticsLoading ? null : String(analytics?.total_requests ?? 0),
      icon: BarChart3,
    },
  ];

  const recentDocs = docsData?.items?.slice(0, 4) ?? [];
  const recentChats = chatsData?.items?.slice(0, 4) ?? [];

  return (
    <div className="p-4 sm:p-6 max-w-[1200px] mx-auto space-y-6 sm:space-y-8 animate-fade-in">
      {/* Welcome */}
      <div>
        <h1 className="text-[26px] font-semibold tracking-tight text-balance">Welcome back, {firstName}</h1>
        <p className="text-muted-foreground mt-1.5">
          Here's what's happening in your workspace.
        </p>
      </div>

      {/* Stats */}
      <StatGrid stats={STATS} />

      {/* Quick Actions + Recent Activity */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.href}
                onClick={() => navigate(action.href)}
                className="flex items-center gap-3 w-full p-3 rounded-lg text-left hover:bg-accent transition-colors group"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-secondary/60 text-foreground group-hover:bg-background transition-colors">
                  <action.icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{action.label}</p>
                  <p className="text-xs text-muted-foreground truncate">{action.description}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {docsLoading && chatsLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : recentDocs.length === 0 && recentChats.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-center">
                <FolderOpen className="h-8 w-8 text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground">No recent activity</p>
                <p className="text-xs text-muted-foreground">Upload a document or start a chat to get started.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Merge and sort recent docs + chats by date */}
                {[
                  ...recentDocs.map((d) => ({
                    type: 'doc' as const,
                    id: d.id,
                    text: d.filename,
                    href: `/documents/${d.id}`,
                    time: d.updated_at || d.created_at,
                    icon: FileText,
                  })),
                  ...recentChats.map((c) => ({
                    type: 'chat' as const,
                    id: c.id,
                    text: c.title,
                    href: `/chat/${c.id}`,
                    time: c.updated_at || c.created_at,
                    icon: MessageSquare,
                  })),
                ]
                  .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
                  .slice(0, 6)
                  .map((item) => (
                    <button
                      key={`${item.type}-${item.id}`}
                      onClick={() => navigate(item.href)}
                      className="flex items-start gap-3 w-full text-left hover:bg-accent p-2 rounded-lg transition-colors group"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                        <item.icon className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{item.text}</p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                          <Clock className="h-3 w-3" />
                          {formatDistanceToNow(new Date(item.time), { addSuffix: true })}
                        </p>
                      </div>
                    </button>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* System / knowledge-base status — real data only */}
      {(analytics || health) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Workspace Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground text-xs mb-1">Knowledge base</p>
                <p className="font-semibold flex items-center gap-1.5 capitalize">
                  <span
                    className={
                      'inline-block h-2 w-2 rounded-full ' +
                      (health?.knowledge_base_health === 'attention'
                        ? 'bg-destructive'
                        : health?.knowledge_base_health === 'processing'
                          ? 'bg-warning'
                          : 'bg-success')
                    }
                    aria-hidden
                  />
                  {health?.knowledge_base_health ?? '—'}
                </p>
                {health && (
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {health.indexed_documents} indexed
                    {health.processing_documents > 0 && ` · ${health.processing_documents} processing`}
                    {health.failed_documents > 0 && ` · ${health.failed_documents} failed`}
                  </p>
                )}
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-1">Avg. Latency</p>
                <p className="font-semibold">{analytics ? `${analytics.average_latency_ms.toFixed(0)} ms` : '—'}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-1">Total Cost</p>
                <p className="font-semibold">{analytics ? `$${analytics.cumulative_cost_usd.toFixed(4)}` : '—'}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-1">Top Topics</p>
                <p className="font-semibold truncate">
                  {analytics && analytics.most_searched_topics.length > 0
                    ? analytics.most_searched_topics.slice(0, 2).map((t) => t.topic).join(', ')
                    : '—'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
