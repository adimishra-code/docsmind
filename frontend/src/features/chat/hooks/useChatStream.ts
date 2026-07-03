import { useCallback } from 'react';
import { useConversationStore } from '@/store/useConversationStore';
import { useContextStore } from '@/store/useContextStore';
import { useAuthStore } from '@/store/useAuthStore';

// Module-level so that Send, Stop, Retry and Regenerate — which may be
// triggered from different components each holding their own hook instance —
// all act on the same in-flight request.
let activeAbortController: AbortController | null = null;

export function useChatStream() {
  const {
    setStreaming,
    appendStreamingContent,
    setStreamingCitations,
    pushAgentState,
    commitStreamingMessage,
    clearStreamingContent,
    setStreamError,
    setLastUserPrompt,
    popLastAssistantMessage,
  } = useConversationStore();

  const streamChat = useCallback(async (prompt: string) => {
    const sessionId = useConversationStore.getState().activeSessionId;
    if (!sessionId) {
      setStreamError('No active conversation. Start a new chat and try again.');
      return;
    }

    setLastUserPrompt(prompt);
    setStreamError(null);
    setStreaming(true);
    clearStreamingContent();
    activeAbortController = new AbortController();
    const token = useAuthStore.getState().accessToken;

    // Scope retrieval to the documents pinned in the Context panel. An empty
    // list is omitted so the backend searches across all of the user's docs.
    const documentIds = useContextStore.getState().pinnedDocuments.map((d) => d.id);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8006'}/api/v1/chat/sessions/${sessionId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            content: prompt,
            ...(documentIds.length ? { document_ids: documentIds } : {}),
          }),
          signal: activeAbortController.signal,
        }
      );

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.status}`);
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
              } else if (data.type === 'citations' && Array.isArray(data.citations)) {
                setStreamingCitations(data.citations);
              } else if (data.type === 'agent_state' && data.node) {
                pushAgentState({ node: data.node, status: data.status ?? 'completed' });
              } else if (data.type === 'error') {
                throw new Error(data.message || data.content || 'The assistant returned an error.');
              }
            } catch (parseErr: any) {
              // Re-throw errors we deliberately raised; ignore malformed SSE fragments.
              if (parseErr?.message && !(parseErr instanceof SyntaxError)) {
                throw parseErr;
              }
            }
          }
        }
      }

      commitStreamingMessage();
    } catch (error: any) {
      if (error.name === 'AbortError') {
        // User stopped generation — keep whatever streamed so far.
        commitStreamingMessage();
      } else {
        console.error('Streaming error:', error);
        setStreamError(
          "Something went wrong while generating a response. Your message was saved — you can retry."
        );
      }
    }
  }, [setStreaming, appendStreamingContent, setStreamingCitations, pushAgentState, commitStreamingMessage, clearStreamingContent, setStreamError, setLastUserPrompt]);

  const abortStream = useCallback(() => {
    activeAbortController?.abort();
    activeAbortController = null;
  }, []);

  /** Re-run the last user prompt without adding a new user message. */
  const retry = useCallback(() => {
    const prompt = useConversationStore.getState().lastUserPrompt;
    if (prompt) void streamChat(prompt);
  }, [streamChat]);

  /** Discard the last assistant reply and generate a fresh one. */
  const regenerate = useCallback(() => {
    const prompt = useConversationStore.getState().lastUserPrompt;
    if (!prompt) return;
    popLastAssistantMessage();
    void streamChat(prompt);
  }, [streamChat, popLastAssistantMessage]);

  return { streamChat, abortStream, retry, regenerate };
}
