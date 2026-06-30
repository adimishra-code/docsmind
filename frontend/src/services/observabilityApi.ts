// Mock data simulating backend metrics

export const observabilityApi = {
  getRetrievalMetrics: async (timeframe: string) => {
    // Simulated delay
    await new Promise(resolve => setTimeout(resolve, 500));
    return {
      averageRecall: 0.82,
      averagePrecision: 0.76,
      averageHitRate: 0.91,
      chunkDistribution: [
        { name: '0-250', count: 120 },
        { name: '250-500', count: 340 },
        { name: '500-1000', count: 210 },
        { name: '1000+', count: 40 }
      ],
      latencyOverTime: [
        { date: 'Mon', p50: 120, p95: 350 },
        { date: 'Tue', p50: 130, p95: 310 },
        { date: 'Wed', p50: 115, p95: 290 },
        { date: 'Thu', p50: 140, p95: 400 },
        { date: 'Fri', p50: 125, p95: 320 },
      ]
    };
  },

  getLLMMetrics: async (timeframe: string) => {
    await new Promise(resolve => setTimeout(resolve, 500));
    return {
      totalCost: 142.50,
      totalTokens: 14500000,
      averageLatency: 1.2, // seconds
      costOverTime: [
        { date: 'Mon', cost: 12, tokens: 1.2 },
        { date: 'Tue', cost: 18, tokens: 1.8 },
        { date: 'Wed', cost: 22, tokens: 2.2 },
        { date: 'Thu', cost: 15, tokens: 1.5 },
        { date: 'Fri', cost: 25, tokens: 2.5 },
      ]
    };
  },

  getExperiments: async () => {
    await new Promise(resolve => setTimeout(resolve, 500));
    return [
      { id: 'exp-1', name: 'Baseline 512 chunks', model: 'gpt-4o', retriever: 'hybrid', hitRate: 0.85, mrr: 0.72 },
      { id: 'exp-2', name: 'Semantic Chunker', model: 'gpt-4o', retriever: 'hybrid', hitRate: 0.92, mrr: 0.81 },
      { id: 'exp-3', name: 'Claude vs GPT-4', model: 'claude-3-5-sonnet', retriever: 'dense', hitRate: 0.81, mrr: 0.69 },
    ];
  }
};
