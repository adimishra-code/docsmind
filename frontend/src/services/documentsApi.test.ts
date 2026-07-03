import { describe, it, expect } from 'vitest';
import {
  isDocumentReady,
  isDocumentFailed,
  isDocumentProcessing,
  documentStatusVariant,
  documentStatusLabel,
} from './documentsApi';

describe('document status helpers', () => {
  it("treats the backend's 'completed' as ready", () => {
    // The worker (app/workers/tasks.py) writes 'completed' on success — the UI
    // must recognise that as the terminal ready state, not just 'ready'.
    expect(isDocumentReady('completed')).toBe(true);
    expect(isDocumentReady('ready')).toBe(true);
    expect(isDocumentReady('processing')).toBe(false);
    expect(isDocumentReady('failed')).toBe(false);
  });

  it('classifies failed and in-flight states', () => {
    expect(isDocumentFailed('failed')).toBe(true);
    expect(isDocumentProcessing('pending')).toBe(true);
    expect(isDocumentProcessing('processing')).toBe(true);
    expect(isDocumentProcessing('completed')).toBe(false);
    expect(isDocumentProcessing('failed')).toBe(false);
  });

  it('maps statuses to badge variants', () => {
    expect(documentStatusVariant('completed')).toBe('default');
    expect(documentStatusVariant('failed')).toBe('destructive');
    expect(documentStatusVariant('processing')).toBe('secondary');
  });

  it('renders friendly labels', () => {
    expect(documentStatusLabel('completed')).toBe('Ready');
    expect(documentStatusLabel('processing')).toBe('Processing');
    expect(documentStatusLabel('pending')).toBe('Processing');
    expect(documentStatusLabel('failed')).toBe('Failed');
  });
});
