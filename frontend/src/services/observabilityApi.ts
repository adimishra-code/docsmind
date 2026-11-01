import { api } from './api';

export interface AnalyticsSummary {
  user_id: string;
  total_requests: number;
  average_latency_ms: number;
  total_tokens_consumed: number;
  cumulative_cost_usd: number;
  latencies_breakdown: Record<string, number>;
  most_searched_topics: Array<{ topic: string; count: number }>;
}

export interface WorkspaceHealth {
  total_documents: number;
  indexed_documents: number;
  processing_documents: number;
  failed_documents: number;
  chat_sessions: number;
  knowledge_base_health: 'healthy' | 'processing' | 'attention';
  recent_activity: Array<{
    id: string;
    filename: string;
    status: string;
    updated_at: string | null;
  }>;
}

export const observabilityApi = {
  getSummary: async (): Promise<AnalyticsSummary> => {
    const { data } = await api.get<AnalyticsSummary>('/api/v1/analytics/summary');
    return data;
  },

  getHealth: async (): Promise<WorkspaceHealth> => {
    const { data } = await api.get<WorkspaceHealth>('/api/v1/analytics/health');
    return data;
  },
};
