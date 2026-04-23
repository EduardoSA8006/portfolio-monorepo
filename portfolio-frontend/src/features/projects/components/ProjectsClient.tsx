'use client';

import { useMemo, useState } from 'react';
import type { Project } from '@/core/domain/project';
import { ProjectGrid } from '@/features/projects/components/ProjectGrid';
import { ProjectFilters, type ProjectFilter } from '@/features/projects/components/ProjectFilters';

export function ProjectsClient({ projects }: { projects: Project[] }) {
  const [filter, setFilter] = useState<ProjectFilter>('Todos');
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return projects.filter((p) => {
      const byCat = filter === 'Todos' || p.category === filter;
      const byQuery =
        q.length === 0 ||
        p.title.toLowerCase().includes(q) ||
        p.summary.toLowerCase().includes(q) ||
        p.stack.some((s) => s.toLowerCase().includes(q));
      return byCat && byQuery;
    });
  }, [projects, filter, query]);

  return (
    <>
      <ProjectFilters
        filter={filter}
        onFilter={setFilter}
        query={query}
        onQuery={setQuery}
        total={projects.length}
        visible={filtered.length}
      />
      <ProjectGrid projects={filtered} />
    </>
  );
}
