import React, { useCallback, useRef, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useDropzone } from 'react-dropzone';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { useTaskStore } from '@/store/useTaskStore';
import { documentsApi } from '@/services/documentsApi';
import { KnowledgeGrid } from './KnowledgeGrid';
import { KnowledgeList } from './KnowledgeList';
import { SearchPlatform } from './SearchPlatform';
import { UploadCloud, Trash2, X, Download, Loader2, Upload } from 'lucide-react';
import { cn } from '@/utils';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function Workspace() {
  const { viewMode, selectedDocumentIds, clearSelection } = useWorkspaceStore();
  const addTask = useTaskStore((state) => state.addTask);
  const updateTask = useTaskStore((state) => state.updateTask);
  const [searchParams] = useSearchParams();
  const isUploadMode = searchParams.get('upload') === 'true';

  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const uploadFiles = useCallback((files: File[]) => {
    files.forEach(async (file) => {
      const tempId = `temp-${Date.now()}-${file.name}`;
      addTask({ id: tempId, filename: file.name, status: 'uploading', progress: 0 });
      try {
        const doc = await documentsApi.upload(file, (progressEvent) => {
          if (progressEvent.total) {
            updateTask(tempId, { progress: Math.round((progressEvent.loaded * 100) / progressEvent.total) });
          }
        });
        updateTask(tempId, { id: doc.id, status: doc.status as any, progress: 100 });
        queryClient.invalidateQueries({ queryKey: ['documents'] });
        toast({ title: 'Upload successful', description: `${file.name} uploaded successfully.` });
      } catch {
        updateTask(tempId, { status: 'failed', error: 'Upload failed' });
        toast({ title: 'Upload failed', variant: 'destructive', description: `Failed to upload ${file.name}.` });
      }
    });
  }, [addTask, updateTask, queryClient]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    uploadFiles(acceptedFiles);
  }, [uploadFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true,
    noKeyboard: true,
  });

  // Handle ?upload=true query parameter to trigger dialog
  useEffect(() => {
    if (isUploadMode && fileInputRef.current) {
      fileInputRef.current.click();
      // Remove query parameter so it doesn't trigger again on reload
      const newUrl = window.location.pathname;
      window.history.replaceState(null, '', newUrl);
    }
  }, [isUploadMode]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(Array.from(e.target.files));
      e.target.value = ''; // Reset input
    }
  };

  const handleBulkDelete = async () => {
    setIsDeleting(true);
    try {
      await Promise.all(selectedDocumentIds.map((id) => documentsApi.delete(id)));
      toast({
        title: 'Documents deleted',
        description: `Successfully deleted ${selectedDocumentIds.length} documents.`,
      });
      clearSelection();
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch {
      toast({
        title: 'Deletion failed',
        variant: 'destructive',
        description: 'Failed to delete some documents. Please try again.',
      });
    } finally {
      setIsDeleting(false);
      setShowConfirmDelete(false);
    }
  };

  const handleBulkDownload = async () => {
    toast({
      title: 'Downloading documents',
      description: `Starting download for ${selectedDocumentIds.length} documents.`,
    });
    
    // Fetch all documents to resolve their names
    try {
      const response = await documentsApi.getAll();
      const docsMap = new Map(response.items.map(d => [d.id, d]));
      
      for (const id of selectedDocumentIds) {
        const doc = docsMap.get(id);
        if (doc) {
          await documentsApi.download(id, doc.filename);
          // Small delay to prevent browser blocking multiple downloads
          await new Promise(r => setTimeout(r, 300));
        }
      }
    } catch {
      toast({
        title: 'Download failed',
        variant: 'destructive',
        description: 'Failed to resolve document filenames.',
      });
    }
  };

  return (
    <div {...getRootProps()} className="flex flex-col h-full relative outline-none">
      <input {...getInputProps()} />
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        className="hidden"
        aria-hidden="true"
      />

      {isDragActive && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm border-2 border-dashed border-primary rounded-lg m-4">
          <UploadCloud className="h-12 w-12 text-primary mb-3" />
          <h2 className="text-lg font-semibold">Drop files to upload</h2>
          <p className="text-sm text-muted-foreground mt-1">PDF, DOCX, TXT, CSV, Markdown</p>
        </div>
      )}

      <div className={cn("flex flex-col h-full p-6", isDragActive && "opacity-50")}>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Documents</h1>
            <p className="text-sm text-muted-foreground mt-0.5">Manage your knowledge base.</p>
          </div>
          
          <div className="flex items-center gap-3">
            <Button
              onClick={() => fileInputRef.current?.click()}
              size="sm"
              className="gap-1.5"
            >
              <Upload className="h-4 w-4" /> Upload Files
            </Button>
            <SearchPlatform />
          </div>
        </div>

        {/* Workspace content grid / list */}
        <div className="flex-1 overflow-y-auto">
          {viewMode === 'grid' ? <KnowledgeGrid /> : <KnowledgeList />}
        </div>
      </div>

      {/* Bulk Action Bar */}
      {selectedDocumentIds.length > 0 && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-card border shadow-lg rounded-full px-5 py-3 flex items-center gap-4 z-40 animate-slide-up">
          <span className="text-sm font-medium text-foreground">
            {selectedDocumentIds.length} selected
          </span>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 px-3 rounded-full hover:bg-accent text-foreground"
              onClick={handleBulkDownload}
            >
              <Download className="h-4 w-4" /> Download
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 px-3 rounded-full hover:bg-destructive/10 text-destructive hover:text-destructive"
              onClick={() => setShowConfirmDelete(true)}
            >
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-full text-muted-foreground hover:text-foreground"
              onClick={clearSelection}
              aria-label="Clear selection"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Bulk Delete Confirm Dialog */}
      <Dialog open={showConfirmDelete} onOpenChange={setShowConfirmDelete}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              Delete selected documents?
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the <strong>{selectedDocumentIds.length}</strong> selected documents?
              This action will permanently delete their text extraction, chunks, and vector embeddings. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfirmDelete(false)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={handleBulkDelete}
              disabled={isDeleting}
            >
              {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete {selectedDocumentIds.length} files
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
