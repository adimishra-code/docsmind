import { useRef, useCallback } from 'react';
import { useConversationStore } from '@/store/useConversationStore';
import { useAuthStore } from '@/store/useAuthStore';

export function useChatStream() {
  const { setStreaming, appendStreamingContent, commitStreamingMessage, clearStreamingContent, activeSessionId } = useConversationStore();
  const abortControllerRef = useRef<AbortController | null>(null);

  const streamChat = useCallback(async (prompt: string) => {
    const sessionId = useConversationStore.getState().activeSessionId;
    if (!sessionId) {
      console.error('No active session');
      return;
    }

    setStreaming(true);
    clearStreamingContent();
    abortControllerRef.current = new AbortController();
    const token = useAuthStore.getState().accessToken;

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8006'}/api/v1/chat/sessions/${sessionId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: prompt }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Chat request failed: ${response.status} ${errorBody}`);
      }

      if (!response.body) throw new Error('ReadableStream not supported');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') break;
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'content' && data.content) {
                appendStreamingContent(data.content);
              }
            } catch {
              // Silent parse errors for SSE chunks
            }
          }
        }
      }

      commitStreamingMessage();
    } catch (error: any) {
      if (error.name === 'AbortError') {
        commitStreamingMessage();
      } else {
        console.error('Streaming error:', error);
        setStreaming(false);
      }
    }
  }, [setStreaming, appendStreamingContent, commitStreamingMessage, clearStreamingContent]);

  const abortStream = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);

  return { streamChat, abortStream };
}
