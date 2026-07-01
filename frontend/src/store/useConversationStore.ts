import { create } from 'zustand';
import { Message } from '@/services/chatApi';

interface ConversationState {
  activeSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;

  setActiveSession: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setStreaming: (isStreaming: boolean) => void;
  appendStreamingContent: (chunk: string) => void;
  commitStreamingMessage: () => void;
  clearStreamingContent: () => void;
  reset: () => void;
}

export const useConversationStore = create<ConversationState>((set) => ({
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',

  setActiveSession: (id) => set({ activeSessionId: id, messages: [] }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamingContent: (chunk) => set((state) => ({ streamingContent: state.streamingContent + chunk })),
  commitStreamingMessage: () => set((state) => {
    if (!state.streamingContent) return state;
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: state.streamingContent,
      created_at: new Date().toISOString(),
    };
    return {
      messages: [...state.messages, newMessage],
      streamingContent: '',
      isStreaming: false,
    };
  }),
  clearStreamingContent: () => set({ streamingContent: '', isStreaming: false }),
  reset: () => set({ activeSessionId: null, messages: [], isStreaming: false, streamingContent: '' }),
}));
