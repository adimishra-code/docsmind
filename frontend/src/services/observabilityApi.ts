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

export const observabilityApi = {
  getSummary: async (): Promise<AnalyticsSummary> => {
    const { data } = await api.get<AnalyticsSummary>('/api/v1/analytics/summary');
    return data;
  },
};
