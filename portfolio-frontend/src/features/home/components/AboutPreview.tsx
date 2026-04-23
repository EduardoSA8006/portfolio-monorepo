import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { Button } from '@/shared/ui/Button';
import { ScrollReveal } from '@/shared/effects/ScrollReveal';
import { profile } from '@/core/config/profile';

export function AboutPreview() {
  return (
    <section id="sobre" className="relative py-24 md:py-32">
      <Container>
        <div className="grid gap-14 md:grid-cols-[auto_1fr] md:items-center md:gap-16">
          <ScrollReveal>
            <figure className="relative mx-auto w-[280px] md:mx-0">
              <div
                aria-hidden
                className="absolute -inset-2 rounded-[22px] opacity-25 blur-2xl"
                style={{ background: 'var(--gradient-btn)' }}
              />
              <div className="relative aspect-[3/4] overflow-hidden rounded-2xl border border-white/[0.1] shadow-[0_24px_60px_-20px_rgba(0,0,0,0.7)]">
                <Image
                  src={profile.avatar}
                  alt={`Foto de ${profile.name}`}
                  fill
                  sizes="280px"
                  className="object-cover"
                />
                <div
                  aria-hidden
                  className="absolute inset-0"
                  style={{
                    background:
                      'linear-gradient(180deg, rgba(5,8,15,0) 60%, rgba(5,8,15,0.35) 100%)',
                  }}
                />
              </div>

              <figcaption className="relative mt-5 flex items-center gap-3 border-t border-white/[0.08] pt-4">
                <span
                  aria-hidden
                  className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--blue-500)]"
                  style={{ boxShadow: '0 0 10px rgba(59,130,246,0.7)' }}
                />
                <div>
                  <div className="text-base font-semibold tracking-tight text-white">
                    Eduardo Alves
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] tracking-[0.18em] text-[var(--text-secondary)] uppercase">
                    Desenvolvedor de Software
                  </div>
                </div>
              </figcaption>
            </figure>
          </ScrollReveal>

          <ScrollReveal delay={0.1}>
            <SectionHeader
              eyebrow="/ SOBRE"
              title="Design + engenharia em um só ofício."
              className="mb-10"
            />
            <div className="max-w-2xl space-y-5 text-base leading-[1.75] text-[var(--text-secondary)] md:text-lg">
              {profile.bio.slice(0, 2).map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
            <div className="mt-12">
              <Button href="/sobre" variant="ghost" size="lg" icon={<ArrowRight size={16} />}>
                Página completa
              </Button>
            </div>
          </ScrollReveal>
        </div>
      </Container>
    </section>
  );
}
