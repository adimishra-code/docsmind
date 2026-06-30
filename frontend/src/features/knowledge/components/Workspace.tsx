import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { useTaskStore } from '@/store/useTaskStore';
import { documentsApi } from '@/services/documentsApi';
import { KnowledgeGrid } from './KnowledgeGrid';
import { KnowledgeList } from './KnowledgeList';
import { SearchPlatform } from './SearchPlatform';
import { UploadCloud } from 'lucide-react';
import { cn } from '@/utils';

export function Workspace() {
  const { viewMode } = useWorkspaceStore();
  const addTask = useTaskStore((state) => state.addTask);
  const updateTask = useTaskStore((state) => state.updateTask);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach(async (file) => {
      // Create a temporary local task id
      const tempId = `temp-${Date.now()}-${file.name}`;
      
      addTask({
        id: tempId,
        filename: file.name,
        status: 'uploading',
        progress: 0,
      });

      try {
        const doc = await documentsApi.upload(file, (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            updateTask(tempId, { progress });
          }
        });
        
        // Once uploaded, the backend returns the real ID and status (likely 'queued' or 'ocr')
        updateTask(tempId, { 
          id: doc.id, // We'd realistically need to swap keys in the store or just use tempId as a local ref
          status: doc.status as any,
          progress: 100 
        });
      } catch (error) {
        updateTask(tempId, { status: 'failed', error: 'Upload failed' });
      }
    });
  }, [addTask, updateTask]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, noClick: true, noKeyboard: true });

  return (
    <div {...getRootProps()} className="flex flex-col h-full relative outline-none">
      <input {...getInputProps()} />
      
      {/* Drag Overlay */}
      {isDragActive && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm border-2 border-dashed border-primary rounded-lg m-4">
          <UploadCloud className="h-16 w-16 text-primary mb-4 animate-bounce" />
          <h2 className="text-2xl font-bold">Drop files to upload</h2>
          <p className="text-muted-foreground mt-2">PDF, DOCX, TXT, CSV, Markdown supported</p>
        </div>
      )}

      <div className={cn("flex flex-col h-full p-6", isDragActive && "opacity-50")}>
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Home</h1>
          <SearchPlatform />
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {viewMode === 'grid' ? <KnowledgeGrid /> : <KnowledgeList />}
        </div>
      </div>
    </div>
  );
}
