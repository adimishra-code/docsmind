import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number | null | undefined, decimals = 2): string {
  // Guard against missing/invalid sizes so the UI never renders "NaN MB".
  if (bytes == null || Number.isNaN(bytes) || bytes < 0) return "—"
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"]
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1)
  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + " " + sizes[i]
}

/**
 * Estimate reading time in whole minutes from the real signals we have — page
 * count (preferred) or chunk count — using rough word densities. Returns null
 * when we have nothing to base it on, so callers can hide the field rather than
 * show a fabricated number. Intentionally labeled "Estimated" in the UI.
 */
export function estimateReadingTime(opts: { pages?: number | null; chunkCount?: number | null }): number | null {
  const WORDS_PER_MINUTE = 220
  const WORDS_PER_PAGE = 450    // typical dense document page
  const WORDS_PER_CHUNK = 110   // ~512-char chunk at the configured chunk size
  let words = 0
  if (opts.pages && opts.pages > 0) words = opts.pages * WORDS_PER_PAGE
  else if (opts.chunkCount && opts.chunkCount > 0) words = opts.chunkCount * WORDS_PER_CHUNK
  if (words <= 0) return null
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE))
}
