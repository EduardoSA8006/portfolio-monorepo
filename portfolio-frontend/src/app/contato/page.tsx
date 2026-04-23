import type { Metadata } from 'next';
import { Mail, ArrowUpRight } from 'lucide-react';
import { GithubIcon, LinkedinIcon, InstagramIcon } from '@/shared/ui/BrandIcons';
import { Container } from '@/shared/ui/Container';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { GradientText } from '@/shared/effects/GradientText';
import { ContactForm } from '@/features/contact/components/ContactForm';
import { profile } from '@/core/config/profile';

export const metadata: Metadata = {
  title: 'Contato',
  description:
    'Fale comigo sobre seu projeto. Respondo em até 24h. Disponível para projetos web e mobile — remoto ou presencial em Rondônia.',
};

const MailTileIcon = ({ width, height }: { width: number; height: number }) => (
  <Mail width={width} height={height} />
);

const socials = [
  {
    label: 'Email',
    handle: profile.email,
    href: `mailto:${profile.email}`,
    Icon: MailTileIcon,
    domain: 'mailto',
    color: '#60a5fa',
    glow: 'rgba(96,165,250,0.55)',
    external: false,
  },
  {
    label: 'LinkedIn',
    handle: profile.handles.linkedin,
    href: profile.social.linkedin,
    Icon: LinkedinIcon,
    domain: 'linkedin.com',
    color: '#0A66C2',
    glow: 'rgba(10,102,194,0.55)',
    external: true,
  },
  {
    label: 'GitHub',
    handle: profile.handles.github,
    href: profile.social.github,
    Icon: GithubIcon,
    domain: 'github.com',
    color: '#ffffff',
    glow: 'rgba(255,255,255,0.35)',
    external: true,
  },
  {
    label: 'Instagram',
    handle: profile.handles.instagram,
    href: profile.social.instagram,
    Icon: InstagramIcon,
    domain: 'instagram.com',
    color: '#E1306C',
    glow: 'rgba(225,48,108,0.55)',
    external: true,
  },
];

export default function ContatoPage() {
  return (
    <>
      <section className="relative overflow-hidden pt-20 pb-24 md:pt-24 md:pb-32">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            maskImage:
              'linear-gradient(to bottom, black 0%, black calc(100% - 180px), transparent 100%)',
            WebkitMaskImage:
              'linear-gradient(to bottom, black 0%, black calc(100% - 180px), transparent 100%)',
          }}
        >
          <AuroraBg intensity="subtle" />
          <GridBg />
        </div>

        <Container className="relative z-10">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-3 font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              <span className="h-px w-8 bg-[var(--blue-500)]" />
              / CONTATO
              <span className="h-px w-8 bg-[var(--blue-500)]" />
            </div>
            <h1
              className="text-3xl leading-[1.02] font-extrabold tracking-[-0.035em] text-white md:text-5xl lg:text-6xl"
              style={{ textAlign: 'center', textAlignLast: 'center' }}
            >
              Vamos construir <br className="hidden md:block" />
              <GradientText>algo juntos.</GradientText>
            </h1>
            <p
              className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-[var(--text-secondary)] md:text-lg"
              style={{ textAlign: 'center', textAlignLast: 'center' }}
            >
              Aberto a oportunidades, freelance e colaborações. Conta sobre seu projeto —
              respondo em até 24h.
            </p>
          </div>

          <div className="mx-auto mt-14 max-w-4xl md:mt-16">
            <div className="relative overflow-hidden rounded-2xl border border-white/[0.1] bg-[var(--bg-glass)] p-6 backdrop-blur-xl md:p-10">
              <div
                aria-hidden
                className="pointer-events-none absolute -top-20 -right-20 h-48 w-48 rounded-full opacity-30 blur-3xl"
                style={{ background: 'var(--gradient-btn)' }}
              />
              <div
                aria-hidden
                className="pointer-events-none absolute -bottom-24 -left-24 h-56 w-56 rounded-full opacity-20 blur-3xl"
                style={{ background: 'var(--gradient-btn)' }}
              />

              <div className="relative">
                <div className="mb-6 flex items-center justify-between gap-4">
                  <div>
                    <div className="font-mono text-[10px] tracking-[0.2em] text-[var(--blue-300)] uppercase">
                      / MENSAGEM DIRETA
                    </div>
                    <h2 className="mt-1.5 text-xl font-semibold tracking-[-0.02em] text-white md:text-2xl">
                      Envie sua mensagem
                    </h2>
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 font-mono text-[9px] tracking-[0.18em] text-emerald-300 uppercase">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    </span>
                    online
                  </span>
                </div>

                <ContactForm />

                <p
                  className="mt-5 text-center text-xs text-[var(--text-muted)]"
                  style={{ textAlign: 'center', textAlignLast: 'center' }}
                >
                  Seus dados ficam entre nós. Sem listas, sem spam.
                </p>
              </div>
            </div>
          </div>

          <div className="mx-auto mt-20 max-w-5xl md:mt-24">
            <div className="mb-10 text-center">
              <div
                className="mb-3 font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase"
                style={{ textAlign: 'center', textAlignLast: 'center' }}
              >
                / REDES SOCIAIS
              </div>
              <h2
                className="text-3xl font-semibold tracking-[-0.03em] text-white md:text-4xl"
                style={{ textAlign: 'center', textAlignLast: 'center' }}
              >
                Ou me encontre por aqui.
              </h2>
              <p
                className="mx-auto mt-3 max-w-md text-sm text-[var(--text-secondary)] md:text-base"
                style={{ textAlign: 'center', textAlignLast: 'center' }}
              >
                Prefere mensagens mais rápidas? Me chame em qualquer uma dessas.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {socials.map((s) => (
                <a
                  key={s.label}
                  href={s.href}
                  {...(s.external
                    ? { target: '_blank', rel: 'noopener noreferrer' }
                    : {})}
                  data-cursor="link"
                  className="group relative flex items-center gap-4 overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-4 transition-all duration-300 hover:-translate-y-0.5 hover:bg-white/[0.04]"
                >
                  <span
                    aria-hidden
                    className="pointer-events-none absolute inset-x-0 top-0 h-px opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                    style={{ background: `linear-gradient(90deg, transparent, ${s.glow}, transparent)` }}
                  />
                  <span
                    aria-hidden
                    className="pointer-events-none absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                    style={{ boxShadow: `inset 0 0 0 1px ${s.glow}` }}
                  />

                  <div
                    className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] transition-transform duration-300 group-hover:scale-105"
                    style={{ color: s.color }}
                  >
                    <s.Icon width={18} height={18} />
                    <span
                      aria-hidden
                      className="absolute inset-0 rounded-lg opacity-0 blur-md transition-opacity duration-300 group-hover:opacity-60"
                      style={{ background: `radial-gradient(circle, ${s.glow} 0%, transparent 70%)` }}
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[15px] font-semibold text-white">{s.label}</span>
                      <span className="font-mono text-[9px] tracking-[0.15em] text-white/25 uppercase">
                        {s.domain}
                      </span>
                    </div>
                    <div className="truncate font-mono text-[11px] tracking-[0.02em] text-[var(--text-secondary)]">
                      {s.handle}
                    </div>
                  </div>

                  <ArrowUpRight
                    size={16}
                    className="shrink-0 text-white/25 transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white"
                  />
                </a>
              ))}
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 font-mono text-[10px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
              <span>preferência por email para propostas formais</span>
              <span className="text-white/15">·</span>
              <span>{profile.locationDetail}</span>
            </div>
          </div>
        </Container>
      </section>
    </>
  );
}
