import Link from 'next/link';
import Image from 'next/image';
import { ArrowUpRight } from 'lucide-react';
import { Badge } from '@/shared/ui/Badge';
import type { Project } from '@/core/domain/project';

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projetos/${project.slug}`}
      data-cursor="link"
      className="group flex flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] transition-colors hover:border-white/[0.18] hover:bg-white/[0.04]"
    >
      <div className="relative aspect-[16/10] overflow-hidden">
        <Image
          src={project.cover}
          alt={project.title}
          fill
          sizes="(max-width: 768px) 100vw, 33vw"
          className="object-cover transition-transform duration-700 group-hover:scale-[1.06]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
        <div className="absolute top-4 left-4">
          <Badge tone="blue">{project.category}</Badge>
        </div>
        <div className="absolute top-4 right-4 flex items-center gap-1 font-mono text-[10px] tracking-[0.15em] text-white/80">
          {project.year}
        </div>
      </div>

      <div className="p-5">
        <h3 className="flex items-center justify-between gap-2 text-lg font-semibold tracking-[-0.015em] text-white">
          {project.title}
          <ArrowUpRight
            size={16}
            className="shrink-0 text-[var(--text-muted)] transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-[var(--blue-400)]"
          />
        </h3>
        <p className="mt-2 line-clamp-2 text-sm text-[var(--text-secondary)]">{project.summary}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {project.stack.slice(0, 3).map((s) => (
            <span
              key={s}
              className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 font-mono text-[10px] text-[var(--text-secondary)]"
            >
              {s}
            </span>
          ))}
          {project.stack.length > 3 && (
            <span className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 font-mono text-[10px] text-[var(--text-muted)]">
              +{project.stack.length - 3}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
