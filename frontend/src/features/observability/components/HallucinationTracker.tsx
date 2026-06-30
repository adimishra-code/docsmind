import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { AlertTriangle, Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function HallucinationTracker() {
  return (
    <div className="space-y-6">
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Hallucination Detection</AlertTitle>
        <AlertDescription>
          This dashboard tracks responses where the LLM generated claims that could not be mapped to the retrieved context chunks (Faithfulness failure).
        </AlertDescription>
      </Alert>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Faithfulness Score</CardTitle>
            <CardDescription>Average across all conversations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-success">98.2%</div>
            <p className="text-sm text-muted-foreground mt-2">1.8% of responses contained unsupported claims.</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Missing Citations</CardTitle>
            <CardDescription>Responses lacking explicit source attribution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-warning">4.5%</div>
            <p className="text-sm text-muted-foreground mt-2">Requires prompt tuning to enforce strict citation formatting.</p>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Recent Flagged Responses</CardTitle>
          <CardDescription>Click to view the full trace</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground text-center py-8 border-dashed border-2 rounded-md">
            No hallucinations detected in the last 24 hours.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
