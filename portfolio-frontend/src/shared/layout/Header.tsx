'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Command, Menu } from 'lucide-react';
import { cn } from '@/core/utils';
import { navLinks } from '@/core/config/navigation';
import { AvailabilityBadge } from '@/shared/ui/Badge';
import { Logo } from '@/shared/ui/Logo';
import { SettingsMenu } from '@/shared/theme/SettingsMenu';
import { MobileMenu } from './MobileMenu';

export function Header({ onCommandOpen }: { onCommandOpen: () => void }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <>
      <header
        className={cn(
          'fixed top-0 right-0 left-0 z-50 border-b transition-[background-color,border-color,backdrop-filter] duration-500',
          scrolled
            ? 'border-white/[0.06] bg-[var(--bg-base)]/75 backdrop-blur-xl'
            : 'border-transparent bg-transparent',
        )}
      >
        <div className="relative mx-auto flex h-16 max-w-6xl items-center justify-between px-6 md:px-10">
          <Link
            href="/"
            aria-label="Ir para a home"
            className="inline-flex items-center transition-opacity hover:opacity-80"
            data-cursor="link"
          >
            <Logo size="sm" glow />
          </Link>

          <nav
            aria-label="Navegação principal"
            className="pointer-events-none absolute left-1/2 hidden -translate-x-1/2 items-center gap-10 font-mono text-xs md:flex"
          >
            {navLinks.map((link) => {
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'group pointer-events-auto relative py-1 transition-colors duration-200',
                    active
                      ? 'text-white'
                      : 'text-[var(--text-secondary)] hover:text-white',
                  )}
                  data-cursor="link"
                >
                  {link.label}
                  <span
                    aria-hidden
                    className={cn(
                      'absolute -bottom-1 left-0 h-[1.5px] rounded-full bg-[var(--blue-400)] transition-all duration-300',
                      active
                        ? 'w-full opacity-100'
                        : 'w-0 opacity-0 group-hover:w-full group-hover:opacity-60',
                    )}
                    style={
                      active
                        ? { boxShadow: '0 0 10px rgba(96,165,250,0.5)' }
                        : undefined
                    }
                  />
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <div className="hidden md:block">
              <AvailabilityBadge />
            </div>
            <SettingsMenu className="hidden md:inline-flex" />
            <button
              onClick={onCommandOpen}
              aria-label="Abrir busca rápida (Ctrl/Cmd + K)"
              className="hidden items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 font-mono text-[10px] text-[var(--text-secondary)] transition-all duration-200 hover:border-[var(--blue-500)]/40 hover:bg-[var(--blue-500)]/10 hover:text-white md:flex"
              data-cursor="link"
            >
              <Command size={12} />
              <span>K</span>
            </button>
            <button
              onClick={() => setMobileOpen(true)}
              aria-label="Abrir menu"
              className="rounded-md p-2 text-white transition-colors hover:bg-white/5 md:hidden"
            >
              <Menu size={18} />
            </button>
          </div>
        </div>
      </header>
      <MobileMenu open={mobileOpen} onClose={() => setMobileOpen(false)} />
    </>
  );
}
