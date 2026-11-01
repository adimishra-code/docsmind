import { describe, it, expect } from 'vitest';
import { buildHighlightMatcher, escapeHtml, normalizeText } from './highlightMatch';

describe('buildHighlightMatcher', () => {
  const excerpt =
    'The Gandhara school of art blended Greco-Roman and Buddhist styles in the northwest.';

  it('matches distinctive words present in the excerpt', () => {
    const match = buildHighlightMatcher(excerpt);
    expect(match('Gandhara')).toBe(true);
    expect(match('Buddhist')).toBe(true);
    expect(match('school of art')).toBe(true);
  });

  it('does not match words absent from the excerpt', () => {
    const match = buildHighlightMatcher(excerpt);
    expect(match('Mathura')).toBe(false);
    expect(match('economics')).toBe(false);
  });

  it('ignores lone stopwords and very short items', () => {
    const match = buildHighlightMatcher(excerpt);
    expect(match('the')).toBe(false); // stopword
    expect(match('of')).toBe(false);  // too short
  });

  it('never matches when the excerpt is empty or too short', () => {
    expect(buildHighlightMatcher('')('anything')).toBe(false);
    expect(buildHighlightMatcher(null)('anything')).toBe(false);
    expect(buildHighlightMatcher('short')('short')).toBe(false);
  });
});

describe('normalizeText', () => {
  it('lowercases and collapses whitespace', () => {
    expect(normalizeText('  Hello   World \n')).toBe('hello world');
  });
});

describe('escapeHtml', () => {
  it('escapes HTML-significant characters', () => {
    expect(escapeHtml('<b>a & "b" \'c\'</b>')).toBe(
      '&lt;b&gt;a &amp; &quot;b&quot; &#39;c&#39;&lt;/b&gt;',
    );
  });
});
