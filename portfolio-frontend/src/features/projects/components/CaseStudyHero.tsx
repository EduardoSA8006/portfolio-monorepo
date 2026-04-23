import Image from 'next/image';
import Link from 'next/link';
import { ChevronLeft, ExternalLink } from 'lucide-react';
import { GithubIcon } from '@/shared/ui/BrandIcons';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Container } from '@/shared/ui/Container';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { GradientText } from '@/shared/effects/GradientText';
import type { Project } from '@/core/domain/project';

export function CaseStudyHero({ project }: { project: Project }) {
  return (
    <section className="relative overflow-hidden pt-12 pb-16 md:pt-16">
      <AuroraBg intensity="subtle" />
      <GridBg />
      <Container>
        <Link
          href="/projetos"
          className="mb-8 inline-flex items-center gap-1 font-mono text-xs text-[var(--text-secondary)] transition-colors hover:text-white"
          data-cursor="link"
        >
          <ChevronLeft size={14} /> / projetos
        </Link>

        <div className="flex flex-wrap items-center gap-3">
          <Badge tone="blue">{project.category}</Badge>
          <span className="font-mono text-[10px] tracking-[0.18em] text-[var(--text-muted)] uppercase">
            {project.year} · {project.duration} · {project.role}
          </span>
        </div>

        <h1 className="mt-6 max-w-4xl text-4xl leading-[1.02] font-semibold tracking-[-0.035em] text-white md:text-6xl">
          {project.title}
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-[var(--text-secondary)]">
          {project.summary}
        </p>

        <div className="mt-8 flex flex-wrap gap-1.5">
          {project.stack.map((s) => (
            <span
              key={s}
              className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1 font-mono text-[10px] text-[var(--text-secondary)]"
            >
              {s}
            </span>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          {project.liveUrl && (
            <Button href={project.liveUrl} external icon={<ExternalLink size={14} />}>
              Ver ao vivo
            </Button>
          )}
          {project.repoUrl && (
            <Button href={project.repoUrl} external variant="ghost" icon={<GithubIcon width={14} height={14} />}>
              Repositório
            </Button>
          )}
        </div>

        <div className="relative mt-14 aspect-[16/9] overflow-hidden rounded-xl border border-white/[0.08]">
          <Image
            src={project.cover}
            alt={project.title}
            fill
            priority
            sizes="(max-width: 768px) 100vw, 1152px"
            className="object-cover"
            style={{ viewTransitionName: `project-cover-${project.slug}` }}
          />
        </div>

        <div className="mt-4 text-right font-mono text-[10px] text-[var(--text-muted)]">
          <GradientText>/ case study</GradientText>
        </div>
      </Container>
    </section>
  );
}
