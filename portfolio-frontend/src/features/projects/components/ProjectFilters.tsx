'use client';

import { Search } from 'lucide-react';
import { Chip } from '@/shared/ui/Chip';

const CATEGORIES = ['Todos', 'Web', 'Mobile', 'Fullstack'] as const;
export type ProjectFilter = (typeof CATEGORIES)[number];

export function ProjectFilters({
  filter,
  onFilter,
  query,
  onQuery,
  total,
  visible,
}: {
  filter: ProjectFilter;
  onFilter: (f: ProjectFilter) => void;
  query: string;
  onQuery: (q: string) => void;
  total: number;
  visible: number;
}) {
  return (
    <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="relative w-full md:max-w-sm">
        <Search
          size={14}
          className="absolute top-1/2 left-3 -translate-y-1/2 text-[var(--text-muted)]"
        />
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Buscar por nome ou stack..."
          className="w-full rounded-lg border border-white/10 bg-white/[0.03] py-2 pr-3 pl-9 text-sm text-white placeholder:text-[var(--text-muted)] focus:border-[var(--blue-500)]/40 focus:outline-none"
        />
      </div>
      <div className="flex items-center gap-2">
        {CATEGORIES.map((c) => (
          <Chip key={c} active={filter === c} onClick={() => onFilter(c)}>
            {c}
          </Chip>
        ))}
        <span className="ml-2 font-mono text-[10px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
          {visible}/{total}
        </span>
      </div>
    </div>
  );
}
