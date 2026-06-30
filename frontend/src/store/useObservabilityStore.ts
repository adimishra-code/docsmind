import { create } from 'zustand';

interface ObservabilityState {
  timeframe: '24h' | '7d' | '30d' | 'all';
  selectedModels: string[];
  activeTab: 'overview' | 'llm' | 'retrieval' | 'experiments';
  
  setTimeframe: (timeframe: '24h' | '7d' | '30d' | 'all') => void;
  toggleModel: (model: string) => void;
  setActiveTab: (tab: 'overview' | 'llm' | 'retrieval' | 'experiments') => void;
}

export const useObservabilityStore = create<ObservabilityState>((set) => ({
  timeframe: '7d',
  selectedModels: ['gpt-4o', 'claude-3-5-sonnet'],
  activeTab: 'overview',
  
  setTimeframe: (timeframe) => set({ timeframe }),
  toggleModel: (model) => set((state) => ({
    selectedModels: state.selectedModels.includes(model)
      ? state.selectedModels.filter(m => m !== model)
      : [...state.selectedModels, model]
  })),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
