import React from 'react';
import { CheckCircle2, Circle, Clock, Loader2 } from 'lucide-react';

interface AgentTimelineProps {
  states: { node: string; status: 'running' | 'completed' | 'error' }[];
}

export function AgentTimeline({ states }: AgentTimelineProps) {
  if (states.length === 0) return null;

  return (
    <div className="flex flex-col space-y-2 mb-4 bg-muted/20 rounded-md p-4 border text-sm">
      <h4 className="font-semibold text-xs text-muted-foreground uppercase tracking-wider mb-2">Execution Graph</h4>
      {states.map((state, i) => (
        <div key={i} className="flex items-center gap-3">
          {state.status === 'completed' ? (
            <CheckCircle2 className="h-4 w-4 text-success" />
          ) : state.status === 'error' ? (
            <Circle className="h-4 w-4 text-destructive" />
          ) : (
            <Loader2 className="h-4 w-4 text-primary animate-spin" />
          )}
          <span className="capitalize font-medium text-foreground">{state.node}</span>
          <span className="text-muted-foreground ml-auto">{state.status}</span>
        </div>
      ))}
    </div>
  );
}
