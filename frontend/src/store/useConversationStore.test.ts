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

  it('commitStreamingMessage carries citations into the committed message', () => {
    const citations = [{ document_name: 'guide.pdf', page_number: 3 }];
    useConversationStore.getState().appendStreamingContent('Grounded answer');
    useConversationStore.getState().setStreamingCitations(citations);
    useConversationStore.getState().commitStreamingMessage();
    const { messages } = useConversationStore.getState();
    expect(messages).toHaveLength(1);
    expect(messages[0].citations).toEqual(citations);
  });

  it('commitStreamingMessage carries latencyMs, chunkCount, and model meta', () => {
    useConversationStore.getState().appendStreamingContent('Answer with stats');
    useConversationStore.getState().setStreamMeta({ model: 'gpt-4o', provider: 'openai' });
    useConversationStore.getState().setStreamStats({
      confidence: 0.85,
      chunkCount: 5,
      tokenCount: 120,
      latencyMs: 1340,
    });
    useConversationStore.getState().commitStreamingMessage();
    const { messages } = useConversationStore.getState();
    expect(messages).toHaveLength(1);
    const meta = messages[0].meta!;
    expect(meta.model).toBe('gpt-4o');
    expect(meta.provider).toBe('openai');
    expect(meta.confidence).toBe(0.85);
    expect(meta.chunkCount).toBe(5);
    expect(meta.tokenCount).toBe(120);
    expect(meta.latencyMs).toBe(1340);
    // Streaming state is cleared
    expect(useConversationStore.getState().streamingContent).toBe('');
    expect(useConversationStore.getState().isStreaming).toBe(false);
    expect(useConversationStore.getState().streamStats).toBeNull();
  });

  it('commitStreamingMessage with no content does not add a message', () => {
    // beginStream sets isStreaming=true; if aborted before any content arrives,
    // commitStreamingMessage must clear isStreaming without appending an empty message.
    useConversationStore.getState().beginStream();
    useConversationStore.getState().commitStreamingMessage();
    const state = useConversationStore.getState();
    expect(state.messages).toHaveLength(0);
    expect(state.isStreaming).toBe(false);
  });

  it('setStreamError clears streaming state and records the error', () => {
    useConversationStore.getState().beginStream();
    useConversationStore.getState().appendStreamingContent('partial');
    useConversationStore.getState().setStreamError('Network timeout');
    const state = useConversationStore.getState();
    expect(state.isStreaming).toBe(false);
    expect(state.streamError).toBe('Network timeout');
    expect(state.streamingContent).toBe('');
  });

  it('resetStreamingContent clears draft without ending the stream', () => {
    useConversationStore.getState().beginStream();
    useConversationStore.getState().appendStreamingContent('draft response');
    useConversationStore.getState().resetStreamingContent();
    const state = useConversationStore.getState();
    expect(state.streamingContent).toBe('');
    // Stream is still active — a revision pass is in flight
    expect(state.isStreaming).toBe(true);
  });

  it('popLastAssistantMessage removes only the last assistant message', () => {
    const user: import('@/services/chatApi').Message = { id: 'u1', role: 'user', content: 'q', created_at: '' };
    const asst: import('@/services/chatApi').Message = { id: 'a1', role: 'assistant', content: 'a', created_at: '' };
    useConversationStore.getState().addMessage(user);
    useConversationStore.getState().addMessage(asst);
    useConversationStore.getState().popLastAssistantMessage();
    const { messages } = useConversationStore.getState();
    expect(messages).toHaveLength(1);
    expect(messages[0].role).toBe('user');
  });

  it('clearStreamingContent resets streaming', () => {
    useConversationStore.getState().setStreaming(true);
    useConversationStore.getState().appendStreamingContent('some text');
    useConversationStore.getState().clearStreamingContent();
    const state = useConversationStore.getState();
    expect(state.streamingContent).toBe('');
    expect(state.isStreaming).toBe(false);
  });

  it('beginStream turns streaming on and clears prior transient state atomically', () => {
    // Simulate leftover state from a previous response.
    useConversationStore.getState().appendStreamingContent('stale draft');
    useConversationStore.getState().setStreamError('old error');

    useConversationStore.getState().beginStream();

    const state = useConversationStore.getState();
    // The whole point of the fix: after beginStream, streaming must be ON so the
    // live thinking indicator / streaming bubble render immediately on send.
    expect(state.isStreaming).toBe(true);
    expect(state.streamingContent).toBe('');
    expect(state.streamError).toBeNull();
    expect(state.streamStartedAt).not.toBeNull();
  });

  it('setStreaming toggles isStreaming', () => {
    useConversationStore.getState().setStreaming(true);
    expect(useConversationStore.getState().isStreaming).toBe(true);
    useConversationStore.getState().setStreaming(false);
    expect(useConversationStore.getState().isStreaming).toBe(false);
  });
});
