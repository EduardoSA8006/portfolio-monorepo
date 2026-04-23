import type { Metadata } from 'next';
import Image from 'next/image';
import * as Icons from 'lucide-react';
import { ArrowRight, MapPin, Mail, Clock, Sparkles } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { Button } from '@/shared/ui/Button';
import { GlassCard } from '@/shared/ui/GlassCard';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { GradientText } from '@/shared/effects/GradientText';
import { ScrollReveal } from '@/shared/effects/ScrollReveal';
import { profile } from '@/core/config/profile';

export const metadata: Metadata = {
  title: 'Sobre',
  description:
    'Desenvolvedor web e mobile, 5 anos de experiência. Bio, timeline de carreira, valores e trajetória.',
};

const quickFacts = [
  { icon: MapPin, label: 'Base', value: profile.location },
  { icon: Sparkles, label: 'Status', value: profile.availability },
  { icon: Clock, label: 'Resposta', value: profile.responseTime },
  { icon: Mail, label: 'E-mail', value: profile.email },
];

export default function SobrePage() {
  return (
    <>
      <section className="relative overflow-hidden pt-10 pb-16 md:pt-14 md:pb-20">
        <AuroraBg intensity="subtle" />
        <GridBg />

        <Container className="relative z-10">
          <div className="mb-10 flex items-center gap-3 font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
            <span className="h-px w-8 bg-[var(--blue-500)]" />
            / SOBRE
          </div>

          <div className="grid items-start gap-12 md:grid-cols-[1fr_300px] md:gap-14 lg:grid-cols-[1fr_340px]">
            <div>
              <p className="mb-4 font-mono text-sm text-[var(--blue-300)] md:text-base">
                Olá, me chamo
              </p>
              <h1 className="text-[36px] leading-[0.95] font-extrabold tracking-[-0.035em] text-white md:text-[52px] lg:text-[64px]">
                {profile.name}.
              </h1>
              <p className="mt-3 text-xl font-normal tracking-[-0.01em] text-[var(--text-secondary)] md:text-2xl lg:text-3xl">
                <GradientText>{profile.role}</GradientText> · Mobile
              </p>

              <p className="mt-8 max-w-xl text-base leading-relaxed text-[var(--text-secondary)] md:text-lg">
                {profile.tagline} Construo apps em Flutter e backends em FastAPI,
                com foco em produto, arquitetura e código que sobrevive ao tempo.
              </p>

              <div className="mt-8 grid grid-cols-2 gap-3 md:max-w-xl md:gap-4">
                {quickFacts.map(({ icon: Icon, label, value }) => (
                  <div
                    key={label}
                    className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 backdrop-blur-sm md:p-4"
                  >
                    <div className="mb-1.5 flex items-center gap-2 font-mono text-[9px] tracking-[0.18em] text-[var(--blue-300)] uppercase">
                      <Icon size={11} />
                      {label}
                    </div>
                    <div className="truncate text-sm font-medium text-white md:text-[15px]">
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button href="/contato" icon={<ArrowRight size={16} />} size="lg">
                  Trabalhar juntos
                </Button>
                <Button href="/projetos" variant="ghost" size="lg">
                  Ver projetos
                </Button>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-[320px] md:mx-0 md:max-w-none md:sticky md:top-24">
              <div
                aria-hidden
                className="absolute -inset-4 rounded-[28px] opacity-35 blur-[42px]"
                style={{ background: 'var(--gradient-btn)' }}
              />
              <div className="relative aspect-[3/4] overflow-hidden rounded-2xl border border-white/[0.1] shadow-[0_30px_80px_-20px_rgba(0,0,0,0.85)]">
                <Image
                  src={profile.avatar}
                  alt={`Foto de ${profile.name}`}
                  fill
                  priority
                  sizes="(max-width: 768px) 80vw, 340px"
                  className="object-cover"
                />
                <div
                  aria-hidden
                  className="absolute inset-0"
                  style={{
                    background:
                      'linear-gradient(180deg, rgba(5,8,15,0) 55%, rgba(5,8,15,0.5) 85%, rgba(5,8,15,0.9) 100%)',
                  }}
                />
                <CornerMark position="tl" />
                <CornerMark position="tr" />
                <CornerMark position="bl" />
                <CornerMark position="br" />

                <div className="absolute right-3 bottom-3 left-3">
                  <div className="flex items-center justify-between rounded-lg border border-white/[0.1] bg-black/50 px-3 py-2 backdrop-blur-xl">
                    <span className="font-mono text-[9px] tracking-[0.18em] text-white/60 uppercase">
                      {profile.shortName.toLowerCase()}.dev
                    </span>
                    <span className="inline-flex items-center gap-1.5 font-mono text-[9px] tracking-[0.15em] text-emerald-300 uppercase">
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      </span>
                      online
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Container>
      </section>

      <section className="border-y border-white/[0.06] bg-white/[0.01] py-6 md:py-7">
        <Container>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-8">
            {profile.stats.map((s, i) => (
              <ScrollReveal key={s.label} delay={i * 0.05}>
                <div className="text-center">
                  <div className="text-2xl font-extrabold tracking-[-0.03em] text-white md:text-3xl">
                    {s.value}
                  </div>
                  <div className="mt-1.5 font-mono text-[9px] tracking-[0.18em] text-[var(--text-secondary)] uppercase md:text-[10px]">
                    {s.label}
                  </div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-28">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ BIOGRAFIA"
            title={
              <>
                Minha <GradientText>História</GradientText> de <GradientText>vida</GradientText>.
              </>
            }
          />
          <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-3">
            {profile.bio.map((text, i) => (
              <ScrollReveal key={i} delay={i * 0.08}>
                <div className="group relative h-full rounded-xl border border-white/[0.06] bg-white/[0.02] p-6 transition-colors hover:border-white/[0.12] hover:bg-white/[0.04]">
                  <div className="mb-4 font-mono text-[10px] tracking-[0.2em] text-[var(--blue-400)] uppercase">
                    / 0{i + 1}
                  </div>
                  <p className="text-sm leading-relaxed text-[var(--text-secondary)] md:text-base">
                    {text}
                  </p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ VALORES"
            title={
              <>
                O que <GradientText>guia</GradientText> meu <GradientText>trabalho</GradientText>.
                </>
            }
        
            description="Princípios que aplico em todo projeto, do primeiro rascunho ao deploy em produção."
          />
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {profile.values.map((v, i) => {
              const Icon = (Icons as unknown as Record<string, Icons.LucideIcon>)[
                v.icon.charAt(0).toUpperCase() + v.icon.slice(1)
              ] as Icons.LucideIcon | undefined;
              return (
                <ScrollReveal key={v.title} delay={i * 0.05}>
                  <GlassCard hover className="h-full">
                    <div className="mb-4 flex items-center justify-between">
                      <div
                        className="flex h-11 w-11 items-center justify-center rounded-lg text-white text-on-primary"
                        style={{ background: 'var(--gradient-btn)' }}
                        aria-hidden
                      >
                        {Icon ? <Icon size={18} /> : null}
                      </div>
                      <span className="font-mono text-[10px] tracking-[0.2em] text-white/30 uppercase">
                        0{i + 1}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-white">{v.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                      {v.body}
                    </p>
                  </GlassCard>
                </ScrollReveal>
              );
            })}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ TRAJETÓRIA"
            title={<>
            De <GradientText>idéias</GradientText> para <GradientText>produtos</GradientText>.
            </>}
            description="Cada etapa abriu porta para a próxima."
          />
          <div className="relative">
            <div
              aria-hidden
              className="absolute top-0 left-4 h-full w-px bg-gradient-to-b from-[var(--blue-500)]/30 via-white/[0.06] to-transparent md:left-6"
            />
            <ol className="space-y-8 md:space-y-10">
              {profile.timeline.map((item, i) => (
                <ScrollReveal key={i} delay={i * 0.04}>
                  <li className="relative pl-12 md:pl-16">
                    <div
                      className="absolute top-1 left-2 flex h-5 w-5 items-center justify-center rounded-full border-2 border-[var(--bg-base)] md:left-4"
                      style={{ background: 'var(--blue-500)' }}
                      aria-hidden
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-white" />
                    </div>
                    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 transition-colors hover:border-white/[0.12] hover:bg-white/[0.04] md:p-6">
                      <div className="mb-2 flex flex-wrap items-center gap-3">
                        <span className="rounded-md border border-[var(--blue-500)]/30 bg-[var(--blue-500)]/10 px-2.5 py-1 font-mono text-[10px] tracking-[0.15em] text-[var(--blue-300)] uppercase">
                          {item.period}
                        </span>
                        <span className="font-mono text-[10px] tracking-[0.15em] text-white/40 uppercase">
                          {item.company}
                        </span>
                      </div>
                      <h3 className="text-xl font-semibold text-white">{item.role}</h3>
                      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)] md:text-[15px]">
                        {item.description}
                      </p>
                    </div>
                  </li>
                </ScrollReveal>
              ))}
            </ol>
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ CARREIRA"
            title="Experiência profissional."
            description="Empresas e projetos que marcaram minha caminhada."
          />
          <div className="mx-auto grid max-w-5xl gap-5 md:grid-cols-2">
            {profile.career.map((job, i) => (
              <ScrollReveal key={`${job.company}-${i}`} delay={i * 0.06}>
                <div className="group relative h-full overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 transition-colors hover:border-white/[0.15] hover:bg-white/[0.04]">
                  <div
                    aria-hidden
                    className="absolute top-0 right-0 h-24 w-24 rounded-bl-full opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-40"
                    style={{ background: 'var(--gradient-btn)' }}
                  />
                  <div className="relative">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <span className="rounded-md border border-[var(--blue-500)]/30 bg-[var(--blue-500)]/10 px-2.5 py-1 font-mono text-[10px] tracking-[0.15em] text-[var(--blue-300)] uppercase">
                        {job.period}
                      </span>
                      <div
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white text-on-primary"
                        style={{ background: 'var(--gradient-btn)' }}
                        aria-hidden
                      >
                        <Icons.Briefcase size={16} />
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold text-white">{job.role}</h3>
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-[var(--text-secondary)]">
                      <span className="font-medium text-white/80">{job.company}</span>
                      <span className="text-white/30">·</span>
                      <span className="font-mono text-[11px] tracking-[0.12em] text-white/50 uppercase">
                        {job.location}
                      </span>
                    </div>
                    <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
                      {job.description}
                    </p>
                    {job.tech.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-1.5">
                        {job.tech.map((t) => (
                          <span
                            key={t}
                            className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] tracking-[0.05em] text-[var(--text-secondary)]"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ CONQUISTAS"
            title="Maratonas e reconhecimentos."
            description="Competições, hackathons e premiações ao longo da jornada."
          />
          <div className="mx-auto grid max-w-5xl gap-5 md:grid-cols-2 lg:grid-cols-3">
            {profile.achievements.map((a, i) => (
              <ScrollReveal key={`${a.title}-${i}`} delay={i * 0.05}>
                <div className="group relative h-full overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 transition-colors hover:border-amber-400/30 hover:bg-white/[0.04]">
                  <div
                    aria-hidden
                    className="absolute -top-10 -right-10 h-28 w-28 rounded-full opacity-0 blur-3xl transition-opacity duration-300 group-hover:opacity-60"
                    style={{ background: 'radial-gradient(circle, #fbbf24 0%, transparent 70%)' }}
                  />
                  <div className="relative">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-amber-400/30 bg-amber-400/10 text-amber-300">
                        <Icons.Trophy size={18} />
                      </div>
                      <span className="rounded-md border border-amber-400/30 bg-amber-400/10 px-2.5 py-1 font-mono text-[10px] tracking-[0.15em] text-amber-300 uppercase">
                        {a.placement}
                      </span>
                    </div>
                    <div className="font-mono text-[10px] tracking-[0.18em] text-white/40 uppercase">
                      {a.year} · {a.organization}
                    </div>
                    <h3 className="mt-2 text-lg font-semibold text-white">{a.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                      {a.description}
                    </p>
                  </div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ INTERESSES"
            title="Fora do trabalho."
            description="O que alimenta a curiosidade e me mantém afiado."
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {profile.interests.map((item, i) => {
              const key =
                item.icon.charAt(0).toUpperCase() +
                item.icon
                  .slice(1)
                  .replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
              const Icon = (Icons as unknown as Record<string, Icons.LucideIcon>)[
                key
              ] as Icons.LucideIcon | undefined;
              return (
                <ScrollReveal key={item.title} delay={i * 0.04}>
                  <div className="group h-full rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 transition-colors hover:border-[var(--blue-500)]/30 hover:bg-white/[0.04]">
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-[var(--blue-300)] transition-colors group-hover:border-[var(--blue-500)]/40 group-hover:text-[var(--blue-200)]">
                      {Icon ? <Icon size={18} /> : null}
                    </div>
                    <h3 className="text-base font-semibold text-white">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-[var(--text-secondary)]">
                      {item.body}
                    </p>
                  </div>
                </ScrollReveal>
              );
            })}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ FORMAÇÃO"
            title="Educação formal."
            description="Base acadêmica que sustenta minha prática."
          />
          <div className="mx-auto grid max-w-4xl gap-4 md:grid-cols-2">
            {profile.education.map((e, i) => (
              <GlassCard key={i} hover>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
                      {e.period}
                    </div>
                    <h3 className="mt-2 text-lg font-semibold text-white">{e.degree}</h3>
                    <p className="text-sm text-[var(--text-secondary)]">{e.institution}</p>
                  </div>
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-white text-on-primary"
                    style={{ background: 'var(--gradient-btn)' }}
                    aria-hidden
                  >
                    <Icons.GraduationCap size={18} />
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-24">
        <Container>
          <SectionHeader
            align="center"
            eyebrow="/ CERTIFICADOS"
            title="Cursos e certificações."
            description="Aprendizado contínuo — o que fiz fora da escola."
          />
          <div className="mx-auto grid max-w-5xl gap-3 md:grid-cols-2">
            {profile.certifications.map((c, i) => {
              const isLink = c.url && c.url !== '#';
              const Wrapper: React.ElementType = isLink ? 'a' : 'div';
              const wrapperProps = isLink
                ? { href: c.url, target: '_blank', rel: 'noopener noreferrer' }
                : {};
              return (
                <ScrollReveal key={`${c.title}-${i}`} delay={i * 0.04}>
                  <Wrapper
                    {...wrapperProps}
                    className="group flex h-full items-start gap-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-5 transition-colors hover:border-[var(--blue-500)]/30 hover:bg-white/[0.04]"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-[var(--blue-300)] transition-colors group-hover:border-[var(--blue-500)]/40 group-hover:text-[var(--blue-200)]">
                      <Icons.Award size={16} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
                        <span>{c.year}</span>
                        <span className="text-white/20">·</span>
                        <span className="text-white/40">{c.hours}</span>
                      </div>
                      <h3 className="mt-1 text-sm font-semibold text-white md:text-base">
                        {c.title}
                      </h3>
                      <p className="text-xs text-[var(--text-secondary)] md:text-sm">
                        {c.institution}
                      </p>
                    </div>
                    {isLink && (
                      <Icons.ExternalLink
                        size={14}
                        className="shrink-0 text-white/30 transition-colors group-hover:text-[var(--blue-300)]"
                        aria-hidden
                      />
                    )}
                  </Wrapper>
                </ScrollReveal>
              );
            })}
          </div>
        </Container>
      </section>

      <section className="py-20 md:py-28">
        <Container>
          <div className="relative overflow-hidden rounded-2xl border border-white/[0.1] bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-10 text-center md:p-16">
            <div
              aria-hidden
              className="absolute -top-24 left-1/2 h-64 w-64 -translate-x-1/2 rounded-full opacity-40 blur-3xl"
              style={{ background: 'var(--gradient-btn)' }}
            />
            <div className="relative">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 font-mono text-[10px] tracking-[0.2em] text-emerald-300 uppercase">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
                {profile.availability}
              </div>
              <h2 className="text-3xl leading-[1.05] font-semibold tracking-[-0.03em] text-white md:text-5xl">
                Tem um projeto em mente? <br className="hidden md:block" />
                <GradientText>Vamos construir juntos.</GradientText>
              </h2>
              <p className="mx-auto mt-5 max-w-lg text-base text-[var(--text-secondary)] md:text-lg">
                Entre em contato comigo pelas plataformas disponiveis. {profile.responseTime}.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Button href="/contato" icon={<ArrowRight size={16} />} size="lg">
                  Ir ao contato
                </Button>
                <Button href="/projetos" variant="ghost" size="lg">
                  Ver projetos
                </Button>
              </div>
            </div>
          </div>
        </Container>
      </section>
    </>
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
