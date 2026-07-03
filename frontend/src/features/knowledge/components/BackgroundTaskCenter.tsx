import React from 'react';
import { useTaskStore } from '@/store/useTaskStore';
import { useQuery } from '@tanstack/react-query';
import { documentsApi, isDocumentReady, isDocumentFailed, isDocumentProcessing } from '@/services/documentsApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/utils';

export function BackgroundTaskCenter() {
  const { tasks, isTaskCenterOpen, toggleTaskCenter, updateTask, clearCompleted } = useTaskStore();
  const taskList = Object.values(tasks);

  // Poll server-side status for tasks still being ingested (skip local-only
  // 'uploading' state and anything already terminal).
  const pendingTasks = taskList.filter(t => t.status !== 'uploading' && isDocumentProcessing(t.status));

  useQuery({
    queryKey: ['task-polling', pendingTasks.map(t => t.id)],
    queryFn: async () => {
      for (const task of pendingTasks) {
        if (task.id.startsWith('temp-')) continue;
        try {
          const res = await documentsApi.getStatus(task.id);
          updateTask(task.id, { status: res.status as any, progress: (res as any).progress_pct ?? (isDocumentReady(res.status) ? 100 : 50) });
        } catch (error) {
          updateTask(task.id, { status: 'failed', error: 'Failed to fetch status' });
        }
      }
      return true;
    },
    refetchInterval: pendingTasks.length > 0 ? 3000 : false, // Poll every 3 seconds if there are active tasks
  });

  if (!isTaskCenterOpen) return null;

  return (
    <Card className="fixed bottom-4 right-4 w-96 shadow-xl z-50 animate-in slide-in-from-bottom-5">
      <CardHeader className="py-3 px-4 border-b flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">Background Tasks ({taskList.length})</CardTitle>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={clearCompleted}>
            <span className="sr-only">Clear completed</span>
            <CheckCircle className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={toggleTaskCenter}>
            <span className="sr-only">Close</span>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {taskList.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No active tasks
          </div>
        ) : (
          <ScrollArea className="h-64">
            <div className="flex flex-col divide-y">
              {taskList.map(task => (
                <div key={task.id} className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium truncate pr-4">{task.filename}</span>
                    {isDocumentReady(task.status) && <CheckCircle className="h-4 w-4 text-success flex-shrink-0" />}
                    {isDocumentFailed(task.status) && <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />}
                    {isDocumentProcessing(task.status) && (
                      <Loader2 className="h-4 w-4 text-muted-foreground animate-spin flex-shrink-0" />
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="capitalize">{task.status}</span>
                    <span>{task.progress}%</span>
                  </div>
                  <Progress 
                    value={task.progress} 
                    className={cn(
                      "h-1.5", 
                      task.status === 'failed' ? "bg-destructive/20" : "bg-primary/20"
                    )} 
                  />
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
