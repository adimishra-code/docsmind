import { useRef, useCallback } from 'react';
import { useConversationStore } from '@/store/useConversationStore';
import { useContextStore } from '@/store/useContextStore';

export function useChatStream() {
  const { setStreaming, appendStreamingContent, commitStreamingMessage, clearStreamingContent, messages } = useConversationStore();
  const { pinnedDocuments } = useContextStore();
  const abortControllerRef = useRef<AbortController | null>(null);

  const streamChat = useCallback(async (prompt: string) => {
    setStreaming(true);
    clearStreamingContent();

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`, // Ideal to pull from auth store, simplified for isolation
        },
        body: JSON.stringify({
          messages: [...messages, { role: 'user', content: prompt }],
          context_ids: pinnedDocuments.map(d => d.id)
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error('Network response was not ok');
      if (!response.body) throw new Error('ReadableStream not supported');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        // Assume backend sends standard SSE format: data: {"token": "hello"} \n\n
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') break;
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'content' && data.content) {
                appendStreamingContent(data.content);
              } else if (data.type === 'agent_state') {
                // Future: Dispatch agent state to a new store array to render in AgentTimeline
                // e.g. useConversationStore.getState().addAgentState(data.node, data.status);
                console.log(`Agent state update: ${data.node} is ${data.status}`);
              } else if (data.type === 'citations') {
                // Handled at message completion, but could be saved incrementally
              }
            } catch (e) {
              // Handle parse errors silently
            }
          }
        }
      }
      
      commitStreamingMessage();
    } catch (error: any) {
      if (error.name === 'AbortError') {
        // Handle abort gracefully, keep what was generated so far
        commitStreamingMessage();
      } else {
        console.error("Streaming error:", error);
        setStreaming(false);
      }
    }
  }, [messages, pinnedDocuments, setStreaming, appendStreamingContent, commitStreamingMessage, clearStreamingContent]);

  const abortStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  return { streamChat, abortStream };
}
