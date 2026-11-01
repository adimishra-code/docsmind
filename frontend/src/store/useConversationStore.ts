import { create } from 'zustand';
import { Message, MessageMeta } from '@/services/chatApi';

export interface AgentState {
  node: string;
  status: 'running' | 'completed' | 'error';
}

export interface StreamStats {
  confidence?: number;
  chunkCount?: number;
  tokenCount?: number;
  latencyMs?: number;   // server-measured backend latency from the stats SSE event
  cached?: boolean;
}

interface ConversationState {
  activeSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  /** Citations received for the in-flight response, attached on commit. */
  streamingCitations: unknown[];
  /** Live LangGraph node progress for the in-flight response. */
  agentStates: AgentState[];
  /** Model/provider announced at the start of the in-flight response. */
  streamMeta: MessageMeta | null;
  /** Server-computed grounding stats for the in-flight response. */
  streamStats: StreamStats | null;
  /** Client timestamps used to derive time-to-first-token and total time. */
  streamStartedAt: number | null;
  streamFirstTokenAt: number | null;
  /** Human-readable error from the most recent failed generation, or null. */
  streamError: string | null;
  /** The last prompt the user sent — used to power retry / regenerate. */
  lastUserPrompt: string | null;

  setActiveSession: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setStreaming: (isStreaming: boolean) => void;
  /** Atomically begin a new stream: clears any prior transient state AND turns
   *  streaming on in a single update. Prevents the ordering hazard where a
   *  separate clear-then-set (or set-then-clear) would leave isStreaming false
   *  and hide the live "thinking"/streaming UI until the answer was committed. */
  beginStream: () => void;
  markStreamStart: () => void;
  appendStreamingContent: (chunk: string) => void;
  /** Clear the in-flight draft (used when the backend restarts a generation
   *  pass, e.g. a revision) without ending the stream. */
  resetStreamingContent: () => void;
  setStreamingCitations: (citations: unknown[]) => void;
  setStreamMeta: (meta: MessageMeta) => void;
  setStreamStats: (stats: StreamStats) => void;
  pushAgentState: (state: AgentState) => void;
  commitStreamingMessage: () => void;
  clearStreamingContent: () => void;
  setStreamError: (error: string | null) => void;
  setLastUserPrompt: (prompt: string) => void;
  /** Removes the trailing assistant message (used before regenerating). */
  popLastAssistantMessage: () => void;
  reset: () => void;
}

const EMPTY_TRANSIENT = {
  streamingContent: '',
  streamingCitations: [] as unknown[],
  agentStates: [] as AgentState[],
  streamMeta: null as MessageMeta | null,
  streamStats: null as StreamStats | null,
  streamStartedAt: null as number | null,
  streamFirstTokenAt: null as number | null,
};

export const useConversationStore = create<ConversationState>((set) => ({
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingCitations: [],
  agentStates: [],
  streamMeta: null,
  streamStats: null,
  streamStartedAt: null,
  streamFirstTokenAt: null,
  streamError: null,
  lastUserPrompt: null,

  setActiveSession: (id) => set({ activeSessionId: id, messages: [], streamError: null, lastUserPrompt: null, ...EMPTY_TRANSIENT }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setStreaming: (isStreaming) => set({ isStreaming }),
  beginStream: () => set({
    // Reset every transient field first, then switch streaming on and stamp the
    // start time — all in one atomic update so the UI flips to "thinking"
    // immediately on send and never briefly reads isStreaming === false.
    ...EMPTY_TRANSIENT,
    isStreaming: true,
    streamError: null,
    streamStartedAt: Date.now(),
    streamFirstTokenAt: null,
  }),
  markStreamStart: () => set({ streamStartedAt: Date.now(), streamFirstTokenAt: null, streamMeta: null, streamStats: null }),
  appendStreamingContent: (chunk) => set((state) => ({
    streamingContent: state.streamingContent + chunk,
    // Stamp the first visible token so we can report time-to-first-token.
    streamFirstTokenAt: state.streamFirstTokenAt ?? Date.now(),
  })),
  resetStreamingContent: () => set({ streamingContent: '' }),
  setStreamingCitations: (streamingCitations) => set({ streamingCitations }),
  setStreamMeta: (meta) => set((state) => ({ streamMeta: { ...(state.streamMeta ?? {}), ...meta } })),
  setStreamStats: (stats) => set((state) => ({ streamStats: { ...(state.streamStats ?? {}), ...stats } })),
  pushAgentState: (incoming) => set((state) => {
    const existing = state.agentStates.findIndex((s) => s.node === incoming.node);
    if (existing === -1) {
      return { agentStates: [...state.agentStates, incoming] };
    }
    const next = [...state.agentStates];
    next[existing] = incoming;
    return { agentStates: next };
  }),
  commitStreamingMessage: () => set((state) => {
    if (!state.streamingContent) return { isStreaming: false, ...EMPTY_TRANSIENT };

    const startedAt = state.streamStartedAt;
    const rawMeta: MessageMeta = {
      ...(state.streamMeta ?? {}),
      confidence: state.streamStats?.confidence,
      chunkCount: state.streamStats?.chunkCount,
      tokenCount: state.streamStats?.tokenCount,
      latencyMs: state.streamStats?.latencyMs,
      cached: state.streamStats?.cached,
      ttftMs: startedAt && state.streamFirstTokenAt ? state.streamFirstTokenAt - startedAt : undefined,
      totalMs: startedAt ? Date.now() - startedAt : undefined,
    };
    // Drop undefined fields so the UI never renders empty/placeholder metadata.
    const meta = Object.fromEntries(
      Object.entries(rawMeta).filter(([, v]) => v !== undefined && v !== null),
    ) as MessageMeta;

    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: state.streamingContent,
      created_at: new Date().toISOString(),
      citations: state.streamingCitations.length ? (state.streamingCitations as Message['citations']) : undefined,
      meta: Object.keys(meta).length ? meta : undefined,
    };
    return {
      messages: [...state.messages, newMessage],
      isStreaming: false,
      streamError: null,
      ...EMPTY_TRANSIENT,
    };
  }),
  clearStreamingContent: () => set({ isStreaming: false, ...EMPTY_TRANSIENT }),
  setStreamError: (streamError) => set({ streamError, isStreaming: false, ...EMPTY_TRANSIENT }),
  setLastUserPrompt: (lastUserPrompt) => set({ lastUserPrompt }),
  popLastAssistantMessage: () => set((state) => {
    const messages = [...state.messages];
    if (messages.length && messages[messages.length - 1].role === 'assistant') {
      messages.pop();
    }
    return { messages };
  }),
  reset: () => set({ activeSessionId: null, messages: [], isStreaming: false, streamError: null, lastUserPrompt: null, ...EMPTY_TRANSIENT }),
}));
