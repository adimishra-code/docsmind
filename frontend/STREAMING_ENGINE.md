# Streaming Engine

## Overview
The Streaming Engine powers the real-time token generation experience for the AI Workspace, ensuring the UI remains responsive while handling Server-Sent Events (SSE) from the DocsMind backend.

## Architecture
- **Location**: `src/features/chat/hooks/useChatStream.ts`
- **Mechanism**: Rather than relying on heavy third-party libraries (like `EventSource` polyfills or `ai` SDKs), it utilizes the native `fetch` API and `ReadableStream`.
- **Parsing**: It decodes the incoming byte stream using `TextDecoder`, splits the chunks by newline, and parses the `data: {...}` payload.
- **State Injection**: Parsed tokens are immediately dispatched to `useConversationStore.appendStreamingContent(token)`, which triggers a re-render of the active `MessageBubble`.
- **Graceful Abortion**: The hook leverages an `AbortController`. If a user clicks the "Stop" button, the controller aborts the fetch request, terminating the TCP connection and gracefully committing the partially generated message to the permanent history.
