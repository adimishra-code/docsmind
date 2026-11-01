import { describe, it, expect } from 'vitest';
import { estimateReadingTime } from './index';

describe('estimateReadingTime', () => {
  it('estimates from page count (preferred)', () => {
    // 10 pages × 450 words ÷ 220 wpm ≈ 20 min
    expect(estimateReadingTime({ pages: 10 })).toBe(20);
  });

  it('falls back to chunk count when pages are missing', () => {
    // 20 chunks × 110 words ÷ 220 wpm = 10 min
    expect(estimateReadingTime({ chunkCount: 20 })).toBe(10);
  });

  it('prefers pages over chunk count when both exist', () => {
    expect(estimateReadingTime({ pages: 10, chunkCount: 999 })).toBe(20);
  });

  it('returns null when there is nothing to estimate from', () => {
    expect(estimateReadingTime({})).toBeNull();
    expect(estimateReadingTime({ pages: 0, chunkCount: 0 })).toBeNull();
  });

  it('never returns less than 1 minute for a real document', () => {
    expect(estimateReadingTime({ chunkCount: 1 })).toBe(1);
  });
});
