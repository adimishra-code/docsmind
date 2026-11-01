import { useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useConversationStore } from '@/store/useConversationStore';
import { useContextStore } from '@/store/useContextStore';
import { useAuthStore } from '@/store/useAuthStore';
import { refreshAccessToken } from '@/services/api';

// Module-level so that Send, Stop, Retry and Regenerate — which may be
// triggered from different components each holding their own hook instance —
// all act on the same in-flight request.
let activeAbortController: AbortController | null = null;

export function useChatStream() {
  const {
    beginStream,
    appendStreamingContent,
    resetStreamingContent,
    setStreamingCitations,
    setStreamMeta,
    setStreamStats,
    pushAgentState,
    commitStreamingMessage,
    setStreamError,
    setLastUserPrompt,
    popLastAssistantMessage,
  } = useConversationStore();
  const queryClient = useQueryClient();

  const streamChat = useCallback(async (prompt: string) => {
    const sessionId = useConversationStore.getState().activeSessionId;
    if (!sessionId) {
      setStreamError('No active conversation. Start a new chat and try again.');
      return;
    }

    setLastUserPrompt(prompt);

    // Cancel any in-flight request before starting a new one.  Without this,
    // navigating away mid-stream or a double-send edge case would leave an
    // orphaned fetch running with no AbortController to stop it.
    activeAbortController?.abort();

    // One atomic transition into the streaming state: this immediately flips the
    // UI to the live "thinking" indicator on send.
    beginStream();
    const currentAbortController = new AbortController();
    activeAbortController = currentAbortController;

    // Scope retrieval to the documents pinned in the Context panel. An empty
    // list is omitted so the backend searches across all of the user's docs.
    const documentIds = useContextStore.getState().pinnedDocuments.map((d) => d.id);
    const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8006'}/api/v1/chat/sessions/${sessionId}/messages`;
    const body = JSON.stringify({
      content: prompt,
      ...(documentIds.length ? { document_ids: documentIds } : {}),
    });
    const doFetch = (token: string | null) =>
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body,
        signal: activeAbortController!.signal,
      });

    try {
      // Raw fetch bypasses the axios 401-refresh interceptor, so handle an
      // expired access token here: refresh once and retry before giving up.
      let response = await doFetch(useAuthStore.getState().accessToken);
      if (response.status === 401) {
        const newToken = await refreshAccessToken();
        response = await doFetch(newToken);
      }

      if (!response.ok) {
        // Surface the backend's actual error instead of a bare status code.
        let detail = '';
        try {
          const body = await response.clone().json();
          detail = body?.detail || body?.message || '';
        } catch {
          try {
            detail = (await response.text()).slice(0, 300);
          } catch {
            /* ignore — fall back to the status code below */
          }
        }
        throw new Error(
          detail
            ? `Chat request failed (${response.status}): ${detail}`
            : `Chat request failed: ${response.status}`,
        );
      }

      if (!response.body) throw new Error('ReadableStream not supported');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      // SSE frames can be split across network reads, so we accumulate into a
      // buffer and only process complete lines. Without this, a `data:` payload
      // straddling two chunks fails JSON.parse and its tokens are lost.
      let buffer = '';
      let done = false;

      const handleLine = (line: string) => {
        if (!line.startsWith('data:')) return;
        const dataStr = line.slice(line.indexOf(':') + 1).trim();
        if (!dataStr) return;
        if (dataStr === '[DONE]') {
          done = true;
          return;
        }
        try {
          const data = JSON.parse(dataStr);
          if (data.type === 'content' && data.content) {
            appendStreamingContent(data.content);
          } else if (data.type === 'content_reset') {
            // Backend restarted the answer (e.g. a revision) — drop the draft.
            resetStreamingContent();
          } else if (data.type === 'citations' && Array.isArray(data.citations)) {
            setStreamingCitations(data.citations);
          } else if (data.type === 'meta') {
            setStreamMeta({ model: data.model, provider: data.provider });
          } else if (data.type === 'stats') {
            setStreamStats({
              confidence: data.confidence,
              chunkCount: data.chunk_count,
              tokenCount: data.token_count,
              latencyMs: data.latency_ms,
              cached: data.cached,
            });
          } else if (data.type === 'title' && data.title) {
            // Backend auto-named this conversation from the first prompt — refresh
            // the sidebar so the "New Chat" placeholder updates immediately.
            queryClient.invalidateQueries({ queryKey: ['chat-sessions'] });
          } else if (data.type === 'agent_state' && data.node) {
            pushAgentState({ node: data.node, status: data.status ?? 'completed' });
          } else if (data.type === 'error') {
            throw new Error(data.message || data.content || 'The assistant returned an error.');
          }
        } catch (parseErr: any) {
          // Re-throw errors we deliberately raised; ignore malformed fragments.
          if (parseErr?.message && !(parseErr instanceof SyntaxError)) {
            throw parseErr;
          }
        }
      };

      while (!done) {
        const { done: readerDone, value } = await reader.read();
        if (readerDone) break;

        buffer += decoder.decode(value, { stream: true });
        let newlineIndex: number;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex).replace(/\r$/, '');
          buffer = buffer.slice(newlineIndex + 1);
          handleLine(line);
          if (done) break;
        }
      }
      // Flush any trailing line that arrived without a terminating newline.
      if (buffer.trim()) handleLine(buffer.replace(/\r$/, ''));

      commitStreamingMessage();
    } catch (error: any) {
      // If a new stream started, this one was aborted automatically.
      // Silently exit so we don't accidentally commit the NEW stream's partial content.
      if (activeAbortController !== currentAbortController) {
        return;
      }

      if (error.name === 'AbortError') {
        // User explicitly stopped generation — keep whatever streamed so far.
        commitStreamingMessage();
      } else {
        console.error('Streaming error:', error);
        setStreamError(
          "Something went wrong while generating a response. Your message was saved — you can retry."
        );
      }
    }
  }, [beginStream, appendStreamingContent, resetStreamingContent, setStreamingCitations, setStreamMeta, setStreamStats, pushAgentState, commitStreamingMessage, setStreamError, setLastUserPrompt, queryClient]);

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
