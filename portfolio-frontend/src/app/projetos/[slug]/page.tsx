import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import * as Icons from 'lucide-react';
import { CaseStudyHero } from '@/features/projects/components/CaseStudyHero';
import { CaseStudySection } from '@/features/projects/components/CaseStudySection';
import { CaseStudyGallery } from '@/features/projects/components/CaseStudyGallery';
import { NextProjectCta } from '@/features/projects/components/NextProjectCta';
import {
  getAllProjects,
  getNextProject,
  getProjectBySlug,
} from '@/features/projects/data/projects';
import { JsonLd } from '@/shared/seo/JsonLd';
import { breadcrumbJsonLd, creativeWorkJsonLd } from '@/core/utils/seo';

export async function generateStaticParams() {
  const all = await getAllProjects();
  return all.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const project = await getProjectBySlug(slug);
  if (!project) return {};
  return {
    title: project.title,
    description: project.summary,
    keywords: project.stack,
    alternates: { canonical: `/projetos/${project.slug}` },
    openGraph: {
      title: project.title,
      description: project.summary,
      type: 'article',
      url: `/projetos/${project.slug}`,
      images: [
        {
          url: `/api/og?title=${encodeURIComponent(project.title)}&subtitle=${encodeURIComponent(project.category)}&eyebrow=${encodeURIComponent(`Case study · ${project.year}`)}`,
          width: 1200,
          height: 630,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: project.title,
      description: project.summary,
    },
  };
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const project = await getProjectBySlug(slug);
  if (!project) notFound();
  const next = await getNextProject(slug);
  if (!next) notFound();

  return (
    <>
      <JsonLd
        data={[
          creativeWorkJsonLd(project),
          breadcrumbJsonLd([
            { name: 'Home', url: '/' },
            { name: 'Projetos', url: '/projetos' },
            { name: project.title, url: `/projetos/${project.slug}` },
          ]),
        ]}
      />
      <CaseStudyHero project={project} />

      <CaseStudySection eyebrow="/ desafio" title="O problema">
        <p className="text-lg leading-relaxed text-[var(--text-secondary)]">{project.challenge}</p>
      </CaseStudySection>

      <CaseStudySection eyebrow="/ abordagem" title="Como resolvi">
        <div className="grid gap-5">
          {project.approach.map((a) => {
            const Icon = (Icons as unknown as Record<string, Icons.LucideIcon>)[
              a.icon.charAt(0).toUpperCase() + a.icon.slice(1)
            ] as Icons.LucideIcon | undefined;
            return (
              <div
                key={a.title}
                className="flex gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-5"
              >
                <div
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-white text-on-primary"
                  style={{ background: 'var(--gradient-btn)' }}
                  aria-hidden
                >
                  {Icon ? <Icon size={18} /> : null}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">{a.title}</h3>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">{a.body}</p>
                </div>
              </div>
            );
          })}
        </div>
      </CaseStudySection>

      <CaseStudySection eyebrow="/ resultado" title="Impacto medido">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {project.results.map((r) => (
            <div key={r.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
              <div className="text-3xl font-semibold tracking-[-0.02em] text-white md:text-4xl">
                {r.value}
              </div>
              <div className="mt-1 text-xs text-[var(--text-secondary)]">{r.label}</div>
            </div>
          ))}
        </div>
      </CaseStudySection>

      <CaseStudyGallery images={project.gallery} isMobile={project.category === 'Mobile'} />

      <NextProjectCta next={next} />
    </>
  );
}
