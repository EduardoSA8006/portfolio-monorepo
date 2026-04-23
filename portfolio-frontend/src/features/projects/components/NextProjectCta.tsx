import Link from 'next/link';
import Image from 'next/image';
import { ArrowUpRight } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import type { Project } from '@/core/domain/project';

export function NextProjectCta({ next }: { next: Project }) {
  return (
    <section className="border-t border-white/[0.06] py-16 md:py-20">
      <Container>
        <Link
          href={`/projetos/${next.slug}`}
          data-cursor="link"
          className="group flex flex-col items-start justify-between gap-8 md:flex-row md:items-center"
        >
          <div>
            <div className="font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              / próximo projeto
            </div>
            <h3 className="mt-3 text-3xl font-semibold tracking-[-0.02em] text-white transition-colors group-hover:text-[var(--blue-300)] md:text-5xl">
              {next.title}
              <ArrowUpRight className="ml-2 inline-block transition-transform group-hover:translate-x-1 group-hover:-translate-y-1" size={32} />
            </h3>
            <p className="mt-3 max-w-lg text-[var(--text-secondary)]">{next.summary}</p>
          </div>
          <div className="relative hidden aspect-[16/10] w-[280px] overflow-hidden rounded-xl border border-white/[0.08] md:block">
            <Image src={next.cover} alt={next.title} fill sizes="280px" className="object-cover transition-transform duration-700 group-hover:scale-[1.06]" />
          </div>
        </Link>
      </Container>
    </section>
  );
}
