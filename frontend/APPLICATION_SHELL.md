# Application Shell

The Application Shell provides the persistent layout framing all protected routes. It is composed of a responsive Sidebar, a Top Navigation header, and a scrollable main content area.

## Key Components

### 1. `AppShell.tsx`
The primary layout wrapper. It utilizes the `ResizablePanelGroup` from `shadcn/ui` to create an adjustable and collapsible sidebar, persisting state to `useLayoutStore`.

### 2. `Sidebar.tsx`
Handles main navigation groups:
- **Core**: Dashboard, Chats, Documents
- **Contextual**: Pinned Items, Favorites
- **Footer**: Settings, Profile

It adapts its rendering based on the `collapsed` prop passed down from the AppShell, gracefully minimizing labels and centering icons.

### 3. `TopNavigation.tsx`
Contains contextual controls:
- **Breadcrumbs**: Hierarchical location (stubbed).
- **Global Search**: Triggers the `CommandPalette`.
- **Theme Toggle**: Fast toggling between Light and Dark mode.
- **User Profile**: Avatar with a dropdown for logout and settings.
