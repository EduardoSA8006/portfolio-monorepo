'use client';

import { Search } from 'lucide-react';
import { Chip } from '@/shared/ui/Chip';

export function PostFilters({
  query,
  onQuery,
  tags,
  activeTags,
  onToggleTag,
  onClear,
  total,
  visible,
}: {
  query: string;
  onQuery: (q: string) => void;
  tags: string[];
  activeTags: string[];
  onToggleTag: (tag: string) => void;
  onClear: () => void;
  total: number;
  visible: number;
}) {
  const hasFilters = query.length > 0 || activeTags.length > 0;
  return (
    <div className="mb-10 space-y-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:max-w-sm">
          <Search
            size={14}
            className="absolute top-1/2 left-3 -translate-y-1/2 text-[var(--text-muted)]"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Buscar no blog..."
            className="w-full rounded-lg border border-white/10 bg-white/[0.03] py-2 pr-3 pl-9 text-sm text-white placeholder:text-[var(--text-muted)] focus:border-[var(--blue-500)]/40 focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
          <span>{visible}/{total}</span>
          {hasFilters && (
            <button
              onClick={onClear}
              className="text-[var(--blue-400)] hover:text-[var(--blue-300)]"
              data-cursor="link"
            >
              Limpar
            </button>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Chip key={tag} active={activeTags.includes(tag)} onClick={() => onToggleTag(tag)}>
            #{tag}
          </Chip>
        ))}
      </div>
    </div>
  );
}
