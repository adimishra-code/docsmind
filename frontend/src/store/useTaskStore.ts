import { create } from 'zustand';

export interface Task {
  id: string;
  filename: string;
  status: 'uploading' | 'queued' | 'ocr' | 'parsing' | 'chunking' | 'embedding' | 'indexing' | 'completed' | 'failed' | 'retrying';
  progress: number;
  error?: string;
}

interface TaskState {
  tasks: Record<string, Task>;
  isTaskCenterOpen: boolean;
  
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  clearCompleted: () => void;
  toggleTaskCenter: () => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: {},
  isTaskCenterOpen: false,

  addTask: (task) => set((state) => ({ 
    tasks: { ...state.tasks, [task.id]: task },
    isTaskCenterOpen: true // Auto-open when new task arrives
  })),
  
  updateTask: (id, updates) => set((state) => {
    if (!state.tasks[id]) return state;
    return {
      tasks: {
        ...state.tasks,
        [id]: { ...state.tasks[id], ...updates }
      }
    };
  }),

  removeTask: (id) => set((state) => {
    const newTasks = { ...state.tasks };
    delete newTasks[id];
    return { tasks: newTasks };
  }),

  clearCompleted: () => set((state) => {
    const newTasks = { ...state.tasks };
    Object.keys(newTasks).forEach(key => {
      if (newTasks[key].status === 'completed' || newTasks[key].status === 'failed') {
        delete newTasks[key];
      }
    });
    return { tasks: newTasks };
  }),

  toggleTaskCenter: () => set((state) => ({ isTaskCenterOpen: !state.isTaskCenterOpen })),
}));
