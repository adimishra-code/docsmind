import React, { useState, useEffect } from 'react';
import { WifiOff, AlertCircle } from 'lucide-react';

export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div 
      className="bg-destructive/10 border-b border-destructive/20 text-destructive px-4 py-2 flex items-center justify-center gap-2 text-xs font-medium animate-in fade-in slide-in-from-top duration-200"
      role="alert"
      aria-live="assertive"
    >
      <WifiOff className="h-4 w-4 shrink-0" />
      <span>You are currently offline. Some features may be unavailable.</span>
    </div>
  );
}
