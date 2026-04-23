'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, ArrowUpRight, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/core/utils';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { Button } from '@/shared/ui/Button';
import { localProjects } from '@/features/projects/data/projects';
import type { Project } from '@/core/domain/project';

const AUTO_ADVANCE_MS = 6000;

export function ProjectsPreview() {
  const projects = localProjects.filter((p) => p.featured).slice(0, 3);
  const total = projects.length;
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(0);
  const [paused, setPaused] = useState(false);
  const reduceMotion = useReducedMotion();

  const goTo = useCallback(
    (target: number) => {
      setDir(target > index ? 1 : -1);
      setIndex((target + total) % total);
    },
    [index, total],
  );

  const prev = useCallback(() => {
    setDir(-1);
    setIndex((i) => (i - 1 + total) % total);
  }, [total]);

  const next = useCallback(() => {
    setDir(1);
    setIndex((i) => (i + 1) % total);
  }, [total]);

  useEffect(() => {
    if (paused || reduceMotion || total < 2) return;
    const id = setTimeout(() => {
      setDir(1);
      setIndex((i) => (i + 1) % total);
    }, AUTO_ADVANCE_MS);
    return () => clearTimeout(id);
  }, [index, paused, reduceMotion, total]);

  const project = projects[index]!;

  return (
    <section id="projetos" className="relative py-24 md:py-32">
      <Container>
        <div className="flex items-end justify-between">
          <SectionHeader
            eyebrow="/ TRABALHO SELECIONADO"
            title="Projetos em destaque."
            className="mb-0"
          />
          <div className="hidden items-center gap-4 md:flex">
            <span className="font-mono text-[10px] tracking-[0.18em] text-[var(--text-muted)] uppercase">
              {String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}
            </span>
            <Button href="/projetos" variant="ghost" icon={<ArrowRight size={16} />}>
              Ver todos
            </Button>
          </div>
        </div>

        <div
          className="relative mt-12"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
          onFocusCapture={() => setPaused(true)}
          onBlurCapture={() => setPaused(false)}
        >
          <div className="relative overflow-hidden">
            <AnimatePresence mode="wait" custom={dir}>
              <motion.div
                key={project.slug}
                custom={dir}
                initial={{ opacity: 0, x: dir === 0 ? 0 : dir * 48 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: dir * -48 }}
                transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              >
                <ProjectSlide project={project} />
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mt-10 flex items-center justify-center gap-4">
            <button
              onClick={prev}
              aria-label="Projeto anterior"
              className="rounded-full border border-white/10 bg-white/[0.03] p-2.5 text-white transition-colors hover:border-[var(--blue-500)]/40 hover:bg-[var(--blue-500)]/10"
              data-cursor="link"
            >
              <ChevronLeft size={16} />
            </button>
            <div className="flex items-center gap-2">
              {projects.map((p, i) => (
                <button
                  key={p.slug}
                  onClick={() => goTo(i)}
                  aria-label={`Ir para projeto ${i + 1}: ${p.title}`}
                  aria-current={i === index ? 'true' : undefined}
                  className={cn(
                    'h-1.5 rounded-full transition-all duration-300',
                    i === index
                      ? 'w-8 bg-[var(--blue-400)] shadow-[0_0_10px_rgba(96,165,250,0.5)]'
                      : 'w-2 bg-white/20 hover:bg-white/40',
                  )}
                  data-cursor="link"
                />
              ))}
            </div>
            <button
              onClick={next}
              aria-label="Próximo projeto"
              className="rounded-full border border-white/10 bg-white/[0.03] p-2.5 text-white transition-colors hover:border-[var(--blue-500)]/40 hover:bg-[var(--blue-500)]/10"
              data-cursor="link"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        <div className="mt-10 flex justify-center md:hidden">
          <Button href="/projetos" variant="ghost" icon={<ArrowRight size={16} />}>
            Ver todos os projetos
          </Button>
        </div>
      </Container>
    </section>
  );
}

function ProjectSlide({ project }: { project: Project }) {
  return (
    <Link
      href={`/projetos/${project.slug}`}
      data-cursor="link"
      className="group grid gap-8 md:grid-cols-2 md:items-center md:gap-12"
    >
      <div className="relative aspect-[16/10] overflow-hidden rounded-xl border border-white/[0.08]">
        <Image
          src={project.cover}
          alt={project.title}
          fill
          sizes="(max-width: 768px) 100vw, 50vw"
          className="object-cover transition-transform duration-700 group-hover:scale-[1.04]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
      </div>

      <div>
        <div className="flex items-center gap-3 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
          <span>{project.category}</span>
          <span className="h-px w-5 bg-white/20" />
          <span>{project.year}</span>
        </div>
        <h3 className="mt-4 text-3xl font-semibold tracking-[-0.02em] text-white md:text-4xl">
          {project.title}
        </h3>
        <p className="mt-4 max-w-lg text-base leading-relaxed text-[var(--text-secondary)]">
          {project.summary}
        </p>
        <div className="mt-5 flex flex-wrap gap-1.5">
          {project.stack.slice(0, 5).map((s) => (
            <span
              key={s}
              className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 font-mono text-[10px] text-[var(--text-secondary)]"
            >
              {s}
            </span>
          ))}
        </div>
        <div className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-[var(--blue-400)] transition-colors group-hover:text-[var(--blue-300)]">
          Ver case study
          <ArrowUpRight
            size={14}
            className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
          />
        </div>
      </div>
    </Link>
  );
}
