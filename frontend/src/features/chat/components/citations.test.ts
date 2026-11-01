import { describe, it, expect } from 'vitest';
import { formatPageRanges, groupCitations } from './MessageBubble';

describe('formatPageRanges', () => {
  it('compresses consecutive pages into ranges', () => {
    expect(formatPageRanges([1, 2, 3, 5, 8, 9])).toBe('1–3, 5, 8–9');
  });
  it('deduplicates and sorts', () => {
    expect(formatPageRanges([9, 8, 8, 1])).toBe('1, 8–9');
  });
  it('handles a single page', () => {
    expect(formatPageRanges([4])).toBe('4');
  });
  it('handles empty input', () => {
    expect(formatPageRanges([])).toBe('');
  });
});

describe('groupCitations', () => {
  it('groups multiple citations from the same document, preserving first-seen order', () => {
    const groups = groupCitations([
      { document_id: 'mem', document_name: 'Memory Notes.pdf', page_number: 4 },
      { document_id: 'cv', document_name: 'AdityaCV.pdf', page_number: 1 },
      { document_id: 'mem', document_name: 'Memory Notes.pdf', page_number: 10 },
    ]);
    expect(groups).toHaveLength(2);
    expect(groups[0].documentName).toBe('Memory Notes.pdf');
    expect(groups[0].pages.sort((a: number, b: number) => a - b)).toEqual([4, 10]);
    expect(groups[1].documentName).toBe('AdityaCV.pdf');
  });

  it('ignores missing/zero page numbers without dropping the document', () => {
    const groups = groupCitations([
      { document_id: 'x', document_name: 'NoPages.pdf', page_number: undefined },
      { document_id: 'x', document_name: 'NoPages.pdf', page_number: 0 },
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].pages).toEqual([]);
  });
});
