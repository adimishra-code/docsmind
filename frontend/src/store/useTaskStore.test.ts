import { describe, it, expect, beforeEach } from 'vitest';
import { useTaskStore } from './useTaskStore';

describe('useTaskStore', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: {}, isTaskCenterOpen: false });
  });

  it('adds a task keyed by its id', () => {
    useTaskStore.getState().addTask({ id: 'temp-1', filename: 'a.pdf', status: 'uploading', progress: 0 });
    expect(useTaskStore.getState().tasks['temp-1']?.filename).toBe('a.pdf');
  });

  it('re-keys the task when an upload swaps the temp id for the server id', () => {
    // Upload flow: task starts under a client temp id, then the real document
    // id arrives on success. Later status polls look it up by the real id, so
    // the store must move the record to the new key.
    const { addTask, updateTask } = useTaskStore.getState();
    addTask({ id: 'temp-1', filename: 'a.pdf', status: 'uploading', progress: 0 });
    updateTask('temp-1', { id: 'doc-uuid', status: 'indexing', progress: 100 });

    const { tasks } = useTaskStore.getState();
    expect(tasks['temp-1']).toBeUndefined();
    expect(tasks['doc-uuid']).toBeDefined();
    expect(tasks['doc-uuid'].status).toBe('indexing');

    // A subsequent poll addressed by the real id must land.
    useTaskStore.getState().updateTask('doc-uuid', { status: 'completed' });
    expect(useTaskStore.getState().tasks['doc-uuid'].status).toBe('completed');
  });

  it('ignores updates for unknown ids', () => {
    useTaskStore.getState().updateTask('missing', { status: 'completed' });
    expect(useTaskStore.getState().tasks['missing']).toBeUndefined();
  });

  it('clears completed and failed tasks only', () => {
    const { addTask, clearCompleted } = useTaskStore.getState();
    addTask({ id: 'a', filename: 'a', status: 'completed', progress: 100 });
    addTask({ id: 'b', filename: 'b', status: 'failed', progress: 0 });
    addTask({ id: 'c', filename: 'c', status: 'indexing', progress: 50 });
    clearCompleted();
    const { tasks } = useTaskStore.getState();
    expect(tasks['a']).toBeUndefined();
    expect(tasks['b']).toBeUndefined();
    expect(tasks['c']).toBeDefined();
  });
});
