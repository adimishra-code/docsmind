# Conversation Platform

## Overview
The Conversation Platform orchestrates the interactive chat experience. It supports rich text rendering, code syntax highlighting, streaming message assembly, and interactive citations.

## Architecture
- **Message Rendering**: `MessageBubble.tsx` uses `react-markdown` augmented with `remark-gfm` and `rehype-highlight` to support tables, Github-flavored markdown, and robust code block syntax highlighting.
- **Input**: `PromptInput.tsx` utilizes `react-textarea-autosize` for a seamless expanding text box similar to native iMessage or Claude interfaces. It hooks into the streaming hook to submit payloads.
- **Virtualization**: As conversations grow, `MessageList.tsx` is designed to be upgraded to a virtualized list to maintain performance, though currently it relies on a standard map and scroll-to-bottom logic.

## Citations
- `CitationCard.tsx` intercepts specific regex patterns in the Markdown output (e.g. `[1]`) and replaces them with interactive badges. These badges, when clicked, open the document in the `KnowledgeEngine` to verify the source material.
