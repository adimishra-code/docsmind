import { describe, it, expect, beforeEach } from 'vitest';
import { useConversationStore } from './useConversationStore';
import type { Message } from '@/services/chatApi';

describe('useConversationStore', () => {
  beforeEach(() => {
    useConversationStore.setState({
      activeSessionId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
    });
  });

  it('starts with empty state', () => {
    const state = useConversationStore.getState();
    expect(state.activeSessionId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.isStreaming).toBe(false);
    expect(state.streamingContent).toBe('');
  });

  it('setActiveSession resets messages', () => {
    useConversationStore.getState().addMessage({ id: 'm1', role: 'user', content: 'hi', created_at: '' });
    useConversationStore.getState().setActiveSession('s1');
    const state = useConversationStore.getState();
    expect(state.activeSessionId).toBe('s1');
    expect(state.messages).toEqual([]);
  });

  it('addMessage appends to messages', () => {
    const msg: Message = { id: 'm1', role: 'user', content: 'hello', created_at: '2024-01-01' };
    useConversationStore.getState().addMessage(msg);
    expect(useConversationStore.getState().messages).toHaveLength(1);
    expect(useConversationStore.getState().messages[0]).toEqual(msg);
  });

  it('appendStreamingContent accumulates text', () => {
    useConversationStore.getState().appendStreamingContent('Hello');
    useConversationStore.getState().appendStreamingContent(' World');
    expect(useConversationStore.getState().streamingContent).toBe('Hello World');
  });

  it('commitStreamingMessage moves content to messages and clears streaming state', () => {
    useConversationStore.getState().appendStreamingContent('Final answer');
    useConversationStore.getState().commitStreamingMessage();
    const state = useConversationStore.getState();
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].role).toBe('assistant');
    expect(state.messages[0].content).toBe('Final answer');
    expect(state.streamingContent).toBe('');
    expect(state.isStreaming).toBe(false);
  });

  it('clearStreamingContent resets streaming', () => {
    useConversationStore.getState().setStreaming(true);
    useConversationStore.getState().appendStreamingContent('some text');
    useConversationStore.getState().clearStreamingContent();
    const state = useConversationStore.getState();
    expect(state.streamingContent).toBe('');
    expect(state.isStreaming).toBe(false);
  });

  it('setStreaming toggles isStreaming', () => {
    useConversationStore.getState().setStreaming(true);
    expect(useConversationStore.getState().isStreaming).toBe(true);
    useConversationStore.getState().setStreaming(false);
    expect(useConversationStore.getState().isStreaming).toBe(false);
  });
});
