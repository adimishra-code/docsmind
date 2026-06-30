import { create } from 'zustand';
import { Message } from '@/services/chatApi';

interface ConversationState {
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  
  setActiveConversation: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setStreaming: (isStreaming: boolean) => void;
  appendStreamingContent: (chunk: string) => void;
  commitStreamingMessage: () => void;
  clearStreamingContent: () => void;
}

export const useConversationStore = create<ConversationState>((set) => ({
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',

  setActiveConversation: (id) => set({ activeConversationId: id, messages: [] }),
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
      isStreaming: false
    };
  }),
  clearStreamingContent: () => set({ streamingContent: '', isStreaming: false }),
}));
