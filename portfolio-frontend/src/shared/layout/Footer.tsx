import Link from 'next/link';
import { ArrowUp, Mail, MapPin } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { GithubIcon, LinkedinIcon, InstagramIcon } from '@/shared/ui/BrandIcons';
import { Logo } from '@/shared/ui/Logo';
import { profile } from '@/core/config/profile';
import { footerLinks } from '@/core/config/navigation';

const SOCIAL_ICONS = {
  GitHub: GithubIcon,
  LinkedIn: LinkedinIcon,
  Instagram: InstagramIcon,
} as const;

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="relative mt-24 border-t border-white/[0.06] pt-12 pb-8">
      <div
        aria-hidden
        className="pointer-events-none absolute top-0 left-1/2 h-px w-[70%] max-w-3xl -translate-x-1/2"
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, rgba(96,165,250,0.5) 50%, transparent 100%)',
        }}
      />

      <Container>
        <div className="grid grid-cols-2 gap-8 md:grid-cols-[1.4fr_1fr_1fr_1.2fr] md:gap-12">
          <div className="col-span-2 md:col-span-1">
            <Link
              href="/"
              aria-label="Ir para a home"
              className="inline-flex items-center transition-opacity hover:opacity-80"
            >
              <Logo size="md" glow />
            </Link>
            <p
              className="mt-4 max-w-xs text-sm leading-relaxed text-[var(--text-secondary)]"
              style={{ textAlign: 'left' }}
            >
              {profile.tagline}
            </p>

            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              </span>
              {profile.availability}
            </div>

            <div className="mt-5 flex items-center gap-2.5">
              <SocialIcon href={profile.social.github} label="GitHub" Icon={GithubIcon} />
              <SocialIcon href={profile.social.linkedin} label="LinkedIn" Icon={LinkedinIcon} />
              <SocialIcon href={profile.social.instagram} label="Instagram" Icon={InstagramIcon} />
            </div>
          </div>

          <div>
            <h4 className="mb-4 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              / Navegação
            </h4>
            <ul className="space-y-2.5 text-sm">
              {footerLinks.nav.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="group inline-flex items-center gap-2 text-[var(--text-secondary)] transition-colors hover:text-white"
                    data-cursor="link"
                  >
                    <span className="h-px w-0 bg-[var(--blue-400)] transition-all duration-300 group-hover:w-3" />
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              / Social
            </h4>
            <ul className="space-y-2.5 text-sm">
              {footerLinks.social.map((link) => {
                const Icon = SOCIAL_ICONS[link.label as keyof typeof SOCIAL_ICONS];
                return (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group inline-flex items-center gap-2 text-[var(--text-secondary)] transition-colors hover:text-white"
                      data-cursor="link"
                    >
                      {Icon && <Icon width={12} height={12} className="opacity-60" />}
                      <span>{link.label}</span>
                      <span className="text-[var(--text-muted)] transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[var(--blue-400)]">
                        ↗
                      </span>
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              / Contato
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li>
                <a
                  href={`mailto:${profile.email}`}
                  className="group inline-flex items-start gap-2 text-[var(--text-secondary)] transition-colors hover:text-white"
                  data-cursor="link"
                >
                  <Mail size={12} className="mt-0.5 shrink-0 opacity-60" />
                  <span className="break-all">{profile.email}</span>
                </a>
              </li>
              <li className="inline-flex items-start gap-2 text-[var(--text-secondary)]">
                <MapPin size={12} className="mt-0.5 shrink-0 opacity-60" />
                <span>
                  {profile.location}
                  <br />
                  <span className="text-xs text-[var(--text-muted)]">
                    {profile.locationDetail}
                  </span>
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-start justify-between gap-3 border-t border-white/[0.06] pt-5 font-mono text-[10px] tracking-[0.1em] text-[var(--text-muted)] uppercase md:flex-row md:items-center">
          <div>
            © {year}{' '}
            <span className="text-[var(--text-secondary)]">{profile.name}</span> · todos os direitos reservados
          </div>
          <div className="flex items-center gap-4">
            <span>
              Construído com Next.js e muito café.
            </span>
            <a
              href="#"
              aria-label="Voltar ao topo"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-white transition-colors hover:border-[var(--blue-500)]/40 hover:bg-[var(--blue-500)]/10"
              data-cursor="link"
              onClick={(e) => {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            >
              <ArrowUp size={12} />
            </a>
          </div>
        </div>
      </Container>
    </footer>
  );
}

function SocialIcon({
  href,
  label,
  Icon,
}: {
  href: string;
  label: string;
  Icon: (props: { width: number; height: number; className?: string }) => React.ReactElement;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      className="group relative flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-[var(--text-secondary)] transition-all duration-200 hover:border-[var(--blue-500)]/40 hover:bg-[var(--blue-500)]/10 hover:text-white"
      data-cursor="link"
    >
      <Icon width={14} height={14} />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-lg opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          boxShadow: '0 0 16px rgba(59,130,246,0.35)',
        }}
      />
    </a>
  );
}
