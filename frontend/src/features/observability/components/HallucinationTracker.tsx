import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { AlertTriangle, Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

/**
 * Faithfulness / hallucination metrics require persisted evaluation runs
 * (see backend app/services/rag/evaluator.py) which are not yet aggregated
 * behind an API. Rather than display fabricated scores, this panel is honest
 * about the metric not being available yet. Do NOT hardcode sample numbers
 * here — wire this to a real metrics endpoint when one exists.
 */
export function HallucinationTracker() {
  return (
    <div className="space-y-6">
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Hallucination Detection</AlertTitle>
        <AlertDescription>
          This dashboard will track responses where the LLM generated claims that could not be
          mapped to the retrieved context chunks (faithfulness failures).
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Faithfulness Score</CardTitle>
            <CardDescription>Average across all conversations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-muted-foreground">—</div>
            <p className="text-sm text-muted-foreground mt-2">
              Not available yet. Requires evaluation runs to be recorded.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Missing Citations</CardTitle>
            <CardDescription>Responses lacking explicit source attribution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-muted-foreground">—</div>
            <p className="text-sm text-muted-foreground mt-2">
              Not available yet. Requires evaluation runs to be recorded.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Flagged Responses</CardTitle>
          <CardDescription>Responses flagged by the evaluator will appear here</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground text-center py-8 border-dashed border-2 rounded-md">
            <Info className="h-4 w-4" />
            No evaluation data recorded yet.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
