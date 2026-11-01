import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/utils';

interface AgentTimelineProps {
  states: { node: string; status: 'running' | 'completed' | 'error' }[];
  streaming?: boolean;
  provider?: string;
  startedAt?: number | null;
}

const STAGES = ['Thinking', 'Retrieving documents', 'Reasoning', 'Generating'] as const;

const HELPERS = [
  'Understanding your question…',
  'Searching your documents for relevant context…',
  'Synthesising retrieved sources…',
  'Composing a grounded answer…',
] as const;

const NODE_STAGE: Record<string, number> = {
  planner: 0,
  retriever: 1,
  reasoner: 2,
  verifier: 2,
  critic: 2,
  composer: 3,
};

function useElapsedSeconds(startedAt?: number | null): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!startedAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);
  if (!startedAt) return 0;
  return Math.max(0, Math.floor((now - startedAt) / 1000));
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s.toString().padStart(2, '0')}s`;
}

/**
 * Live progress indicator during generation.
 * Stages only advance on real backend `agent_state` events — never fabricated.
 */
export function AgentTimeline({ states, streaming = false, provider, startedAt }: AgentTimelineProps) {
  const reached = states.reduce((max, s) => Math.max(max, NODE_STAGE[s.node] ?? 0), -1);
  const current = streaming ? 3 : Math.max(reached, 0);
  const label = STAGES[current] ?? 'Thinking';
  const elapsed = useElapsedSeconds(startedAt);
  const isLocal = provider === 'local' || provider === 'ollama';

  let helper: string = HELPERS[current] ?? 'Working…';
  if (current === 3 && isLocal) helper = 'Generating with the local model — this may take a moment…';

  const slowNote =
    isLocal && elapsed >= 15
      ? 'Local models are slower than cloud APIs. Still working…'
      : null;

  return (
    <div className="space-y-1.5">
      {/* Stage row */}
      <div className="flex items-center gap-2 text-sm">
        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground/70" />
        <span className="font-semibold text-foreground/75 tabular-nums">{label}</span>

        {/* Progress dots */}
        <span className="flex items-center gap-1 ml-0.5" aria-hidden>
          {STAGES.map((_, i) => (
            <span
              key={i}
              className={cn(
                'h-1 w-1 rounded-full transition-all duration-300',
                i < current  && 'bg-foreground/25',
                i === current && 'bg-foreground/65 scale-125',
                i > current  && 'bg-foreground/10',
              )}
            />
          ))}
        </span>

        {/* Elapsed clock — only once a second has passed */}
        {elapsed >= 1 && (
          <span className="ml-auto tabular-nums text-xs text-muted-foreground/50">
            {formatElapsed(elapsed)}
          </span>
        )}
      </div>

      {/* Helper text */}
      <p className="text-xs text-muted-foreground/65 leading-relaxed">{helper}</p>

      {/* Slow-run note for local models */}
      {slowNote && (
        <p className="text-[11px] text-muted-foreground/50 leading-relaxed">{slowNote}</p>
      )}
    </div>
  );
}
