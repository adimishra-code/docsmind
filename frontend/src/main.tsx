import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { ThemeProvider } from './providers/theme-provider'
import { QueryProvider } from './providers/query-provider'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Toaster } from './components/ui/toaster'
import { CommandPalette } from './components/CommandPalette'
import { BackgroundTaskCenter } from './features/knowledge/components/BackgroundTaskCenter'
import { AppRoutes } from './routes'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system" storageKey="docsmind-ui-theme">
        <QueryProvider>
          {/* BrowserRouter wraps everything so CommandPalette/BackgroundTaskCenter
              can use useNavigate and other router hooks */}
          <BrowserRouter>
            <AppRoutes />
            <CommandPalette />
            <BackgroundTaskCenter />
            <Toaster />
          </BrowserRouter>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </StrictMode>,
)
