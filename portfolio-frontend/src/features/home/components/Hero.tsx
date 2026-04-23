'use client';

import dynamic from 'next/dynamic';
import Image from 'next/image';
import { ArrowRight, ChevronDown, Download } from 'lucide-react';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { TextReveal } from '@/shared/effects/TextReveal';
import { Button } from '@/shared/ui/Button';
import { Container } from '@/shared/ui/Container';
import { profile } from '@/core/config/profile';

const Hero3D = dynamic(() => import('@/shared/effects/Hero3D'), { ssr: false });

export function Hero() {
  return (
    <section className="relative -mt-16 flex min-h-[90vh] items-center overflow-hidden pt-[7.5rem] pb-28">
      <AuroraBg intensity="subtle" />
      <GridBg />
      <Hero3D />

      <Container className="relative z-10 grid gap-12 md:grid-cols-[1.25fr_1fr] md:items-center">
        <div>
          <div className="mb-6 flex items-center gap-3 font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
            <span className="h-px w-6 bg-[var(--blue-500)]" />
            / ARIQUEMES · RO · BRASIL
          </div>

          <h1 className="text-white">
            <TextReveal className="block text-base font-normal tracking-normal text-[var(--text-secondary)] md:text-lg">
              Desenvolvedor
            </TextReveal>
            <TextReveal
              delay={0.1}
              className="mt-2 block text-4xl leading-[0.95] font-extrabold tracking-[-0.035em] text-[var(--blue-400)] md:mt-3 md:text-5xl lg:text-6xl xl:text-[64px]"
            >
              {profile.name}
            </TextReveal>
            <TextReveal
              delay={0.22}
              className="mt-3 block text-xl font-normal text-[var(--text-secondary)] md:text-2xl lg:text-3xl"
            >
              Mobile &amp; Fullstack
            </TextReveal>
          </h1>

          <p className="mt-8 max-w-xl text-base leading-relaxed text-[var(--text-secondary)] md:text-lg">
            {profile.bioShort}
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Button href="/projetos" icon={<ArrowRight size={16} />} size="lg">
              Ver projetos
            </Button>
            <Button
              href={profile.cvUrl}
              variant="ghost"
              size="lg"
              icon={<Download size={16} />}
              download
            >
              Baixar currículo
            </Button>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[380px] md:ml-auto">
          <div className="relative aspect-[3/4] overflow-hidden rounded-2xl border border-white/[0.12] shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)]">
            <Image
              src={profile.avatar}
              alt={`Foto de ${profile.name}`}
              fill
              priority
              sizes="(max-width: 768px) 80vw, 380px"
              className="object-cover"
            />
            <div
              aria-hidden
              className="absolute inset-0"
              style={{
                background:
                  'linear-gradient(180deg, rgba(5,8,15,0) 40%, rgba(5,8,15,0.55) 75%, rgba(5,8,15,0.92) 100%)',
              }}
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-2xl"
              style={{
                background: 'linear-gradient(135deg, rgba(96,165,250,0.08) 0%, transparent 55%)',
                mixBlendMode: 'overlay',
              }}
            />

            <CornerMark position="tl" />
            <CornerMark position="tr" />
            <CornerMark position="bl" />
            <CornerMark position="br" />

            <div className="absolute right-4 bottom-4 left-4">
              <div className="rounded-xl border border-white/[0.1] bg-black/40 p-4 backdrop-blur-xl">
                <div className="mb-3 flex items-center justify-between">
                  <span className="font-mono text-[9px] tracking-[0.18em] text-[var(--blue-300)] uppercase">
                    {'// resultados'}
                  </span>
                  <span className="inline-flex items-center gap-1.5 font-mono text-[9px] tracking-[0.15em] text-emerald-300 uppercase">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    </span>
                    live
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {profile.stats.map((stat) => (
                    <div key={stat.label}>
                      <div className="text-xl font-semibold tracking-[-0.025em] text-white text-on-primary">
                        {stat.value}
                      </div>
                      <div className="mt-0.5 text-[10px] leading-tight text-[var(--text-secondary)]">
                        {stat.label}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

        </div>
      </Container>

      <div className="pointer-events-none absolute bottom-6 left-1/2 hidden -translate-x-1/2 flex-col items-center gap-1.5 md:flex">
        <span className="font-mono text-[9px] tracking-[0.3em] text-white/35 uppercase">scroll</span>
        <ChevronDown size={14} className="animate-bounce text-[var(--blue-400)]/70" />
      </div>

     
    </section>
  );
}

function CornerMark({ position }: { position: 'tl' | 'tr' | 'bl' | 'br' }) {
  const placement: Record<typeof position, string> = {
    tl: 'top-3 left-3',
    tr: 'top-3 right-3',
    bl: 'bottom-3 left-3',
    br: 'bottom-3 right-3',
  };
  const rotate: Record<typeof position, number> = {
    tl: 0,
    tr: 90,
    br: 180,
    bl: 270,
  };
  return (
    <span
      aria-hidden
      className={`pointer-events-none absolute h-3.5 w-3.5 ${placement[position]}`}
      style={{ transform: `rotate(${rotate[position]}deg)` }}
    >
      <span className="absolute top-0 left-0 h-[1.5px] w-full rounded-full bg-[var(--blue-300)]/75" />
      <span className="absolute top-0 left-0 h-full w-[1.5px] rounded-full bg-[var(--blue-300)]/75" />
    </span>
  );
}
