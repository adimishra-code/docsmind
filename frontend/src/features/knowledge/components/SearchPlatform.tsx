import React, { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { useWorkspaceStore, type SortKey } from '@/store/useWorkspaceStore';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Search, LayoutGrid, List, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

const SORT_LABELS: Record<SortKey, string> = {
  date: 'Date added',
  name: 'Name',
  size: 'Size',
};

export function SearchPlatform() {
  const { viewMode, setViewMode, setSearchQuery, sortKey, sortDir, setSortKey, setSortDir } = useWorkspaceStore();
  const [localQuery, setLocalQuery] = useState('');

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setSearchQuery(localQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [localQuery, setSearchQuery]);

  return (
    <div className="flex items-center gap-3">
      <div className="relative w-72">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search knowledge..."
          className="pl-8 bg-background"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
        />
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <ArrowUpDown className="h-4 w-4" />
            <span className="hidden sm:inline">{SORT_LABELS[sortKey]}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          <DropdownMenuLabel>Sort by</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={sortKey} onValueChange={(v) => setSortKey(v as SortKey)}>
            <DropdownMenuRadioItem value="date">Date added</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="name">Name</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="size">Size</DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
          <DropdownMenuSeparator />
          <DropdownMenuLabel>Direction</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={sortDir} onValueChange={(v) => setSortDir(v as 'asc' | 'desc')}>
            <DropdownMenuRadioItem value="asc">
              <ArrowUp className="mr-2 h-3.5 w-3.5" /> Ascending
            </DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="desc">
              <ArrowDown className="mr-2 h-3.5 w-3.5" /> Descending
            </DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>

      <ToggleGroup type="single" value={viewMode} onValueChange={(val) => val && setViewMode(val as 'grid' | 'list')}>
        <ToggleGroupItem value="grid" aria-label="Grid view">
          <LayoutGrid className="h-4 w-4" />
        </ToggleGroupItem>
        <ToggleGroupItem value="list" aria-label="List view">
          <List className="h-4 w-4" />
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  );
}
