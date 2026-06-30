# Command Palette

DocsMind incorporates a global, keyboard-first Command Palette inspired by Linear and Notion.

## Features
- **Trigger**: Bound globally to `Cmd+K` (or `Ctrl+K`) and accessible via the Top Navigation search bar.
- **Engine**: Powered by `cmdk` (wrapped via `shadcn/ui` Command primitive) to guarantee zero-layout-shift and native-like performance.
- **State**: The visibility of the dialog is managed globally via `useLayoutStore`, allowing any component to programmatically invoke the palette.

## Capabilities (Sprint 2)
- **Navigation**: Jump instantly to Dashboard, Chats, or Documents.
- **Settings**: Jump to preferences.
- **Theme**: Toggle between Light and Dark mode instantly.

## Future Extensibility
The `CommandPalette` component is structured into `CommandGroup` blocks. As Search and Semantic Document Retrieval comes online, a new asynchronous `CommandGroup` will be added to query the backend in real-time, displaying vectorized document matches directly in the palette.
