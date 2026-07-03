import { create } from 'zustand';
import { Message } from '@/services/chatApi';

export interface AgentState {
  node: string;
  status: 'running' | 'completed' | 'error';
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
  /** Human-readable error from the most recent failed generation, or null. */
  streamError: string | null;
  /** The last prompt the user sent — used to power retry / regenerate. */
  lastUserPrompt: string | null;

  setActiveSession: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setStreaming: (isStreaming: boolean) => void;
  appendStreamingContent: (chunk: string) => void;
  setStreamingCitations: (citations: unknown[]) => void;
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
};

export const useConversationStore = create<ConversationState>((set) => ({
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingCitations: [],
  agentStates: [],
  streamError: null,
  lastUserPrompt: null,

  setActiveSession: (id) => set({ activeSessionId: id, messages: [], streamError: null, lastUserPrompt: null, ...EMPTY_TRANSIENT }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamingContent: (chunk) => set((state) => ({ streamingContent: state.streamingContent + chunk })),
  setStreamingCitations: (streamingCitations) => set({ streamingCitations }),
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
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: state.streamingContent,
      created_at: new Date().toISOString(),
      citations: state.streamingCitations.length ? (state.streamingCitations as Message['citations']) : undefined,
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
