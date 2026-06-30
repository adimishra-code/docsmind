import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { observabilityApi } from '@/services/observabilityApi';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export function ExperimentTracker() {
  const { data: experiments, isLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => observabilityApi.getExperiments()
  });

  if (isLoading || !experiments) {
    return <div className="space-y-4"><Skeleton className="h-40 w-full" /></div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Experiment Runs</CardTitle>
        <CardDescription>Compare retrieval configurations, embedding models, and chunk strategies.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Experiment Name</TableHead>
                <TableHead>LLM</TableHead>
                <TableHead>Retriever Strategy</TableHead>
                <TableHead className="text-right">Hit Rate</TableHead>
                <TableHead className="text-right">MRR</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {experiments.map((exp) => (
                <TableRow key={exp.id} className="cursor-pointer hover:bg-muted/50">
                  <TableCell className="font-medium">{exp.name}</TableCell>
                  <TableCell><Badge variant="secondary">{exp.model}</Badge></TableCell>
                  <TableCell className="capitalize">{exp.retriever}</TableCell>
                  <TableCell className="text-right font-medium text-success">
                    {(exp.hitRate * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {(exp.mrr * 100).toFixed(1)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
