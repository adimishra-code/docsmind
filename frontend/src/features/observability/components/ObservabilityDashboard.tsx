import React from 'react';
import { useObservabilityStore } from '@/store/useObservabilityStore';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { RetrievalMetrics } from './RetrievalMetrics';
import { LLMMetrics } from './LLMMetrics';
import { ExperimentTracker } from './ExperimentTracker';
import { Activity, Database, GitBranch, TerminalSquare } from 'lucide-react';

export function ObservabilityDashboard() {
  const { activeTab, setActiveTab } = useObservabilityStore();

  return (
    <div className="flex flex-col h-full bg-background p-8 overflow-y-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">AI Operations Console</h1>
          <p className="text-muted-foreground">Monitor, evaluate, and benchmark RAG pipelines and LLM telemetry.</p>
        </div>
        
        {/* Timeframe filters could go here */}
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full space-y-6">
        <TabsList className="grid w-full grid-cols-4 max-w-2xl">
          <TabsTrigger value="overview" className="flex gap-2"><Activity className="h-4 w-4" /> Overview</TabsTrigger>
          <TabsTrigger value="retrieval" className="flex gap-2"><Database className="h-4 w-4" /> Retrieval Analytics</TabsTrigger>
          <TabsTrigger value="llm" className="flex gap-2"><TerminalSquare className="h-4 w-4" /> LLM Telemetry</TabsTrigger>
          <TabsTrigger value="experiments" className="flex gap-2"><GitBranch className="h-4 w-4" /> Experiments</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="m-0 space-y-6">
          <div className="p-8 border rounded-lg bg-card text-center text-muted-foreground">
            Overview Dashboards unifying LLM and Retrieval health go here.
          </div>
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
