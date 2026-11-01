/**
 * Text-layer passage highlighting.
 *
 * We have no stored bounding boxes for RAG chunks, so we highlight the cited
 * passage by matching the citation's real excerpt text against the words the
 * PDF text layer actually rendered. This never fabricates — if the excerpt
 * text isn't present on the page (e.g. an OCR mismatch) nothing is highlighted.
 */

// Whole-item stopwords: skip only when the ENTIRE text-layer item is one of
// these, so a distinctive multi-word span is never suppressed. Prevents common
// filler words from lighting up scattered across the page.
const STOPWORDS = new Set([
  'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was', 'were',
  'has', 'have', 'had', 'not', 'but', 'you', 'your', 'our', 'their', 'its',
  'into', 'than', 'then', 'they', 'them', 'which', 'while', 'also', 'such',
  'can', 'will', 'may', 'per', 'via',
]);

export function normalizeText(s: string): string {
  return s.toLowerCase().replace(/\s+/g, ' ').trim();
}

/**
 * Build a predicate that decides whether a single text-layer item belongs to
 * the cited passage. An item matches when its normalized text is contained in
 * the normalized excerpt, is at least 4 characters, and isn't a lone stopword.
 * Very short excerpts are ignored to avoid noisy, meaningless highlights.
 */
export function buildHighlightMatcher(excerpt?: string | null): (item: string) => boolean {
  const norm = normalizeText(excerpt ?? '');
  if (norm.length < 10) return () => false;
  return (item: string): boolean => {
    const t = normalizeText(item);
    if (t.length < 4) return false;
    if (STOPWORDS.has(t)) return false;
    return norm.includes(t);
  };
}

/** Escape a text-layer string before it is used as innerHTML by the renderer. */
export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
