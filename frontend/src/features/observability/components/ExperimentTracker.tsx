import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { GitBranch } from 'lucide-react';

export function ExperimentTracker() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Experiment Runs</CardTitle>
        <CardDescription>Compare retrieval configurations and models.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <GitBranch className="h-10 w-10 text-muted-foreground/30 mb-3" />
          <p className="text-sm text-muted-foreground max-w-sm">
            Experiments will appear here once you start evaluating different retrieval and chunking strategies.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
