import React from 'react';
import { MetricCard } from './MetricCard';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/utils';

interface StatItem {
  id: string;
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

interface StatGridProps {
  stats: StatItem[];
  className?: string;
}

export function StatGrid({ stats, className }: StatGridProps) {
  return (
    <div className={cn("grid gap-4 md:grid-cols-2 lg:grid-cols-4", className)}>
      {stats.map((stat) => (
        <MetricCard key={stat.id} {...stat} />
      ))}
    </div>
  );
}
