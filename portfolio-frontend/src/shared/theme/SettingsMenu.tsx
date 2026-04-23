'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Settings2, Moon, Sun, Check, Globe } from 'lucide-react';
import { cn } from '@/core/utils';
import { useTheme, type ThemeColor } from './ThemeProvider';

const COLOR_SWATCHES: Record<ThemeColor, string> = {
  blue: '#3b82f6',
  purple: '#8b5cf6',
};

export function SettingsMenu({ className }: { className?: string }) {
  const { color, mode, setColor, setMode } = useTheme();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Abrir menu de personalização"
        aria-expanded={open}
        className={cn(
          'inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1.5 font-mono text-[10px] text-[var(--text-secondary)] transition-all duration-200',
          'hover:border-[var(--blue-500)]/40 hover:bg-[var(--blue-500)]/10 hover:text-[var(--text-primary)]',
          open && 'border-[var(--blue-500)]/40 bg-[var(--blue-500)]/10 text-[var(--text-primary)]',
        )}
        data-cursor="link"
      >
        <Settings2 size={12} className={cn('transition-transform duration-300', open && 'rotate-90')} />
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{
            background: COLOR_SWATCHES[color],
            boxShadow: `0 0 8px ${COLOR_SWATCHES[color]}`,
          }}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            className="absolute right-0 z-50 mt-2 w-64 origin-top-right overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-surface)]/95 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.5)] backdrop-blur-xl"
            role="menu"
          >
            <div className="px-4 py-3">
              <div className="font-mono text-[9px] tracking-[0.18em] text-[var(--text-muted)] uppercase">
                / Personalização
              </div>
            </div>

            <Section label="Tema">
              <Option
                active={mode === 'dark'}
                onClick={() => setMode('dark')}
                icon={<Moon size={13} />}
                label="Escuro"
              />
              <Option
                active={mode === 'light'}
                onClick={() => setMode('light')}
                icon={<Sun size={13} />}
                label="Claro"
              />
            </Section>

            <Section label="Cor">
              <Option
                active={color === 'blue'}
                onClick={() => setColor('blue')}
                icon={<Swatch color={COLOR_SWATCHES.blue} />}
                label="Azul"
              />
              <Option
                active={color === 'purple'}
                onClick={() => setColor('purple')}
                icon={<Swatch color={COLOR_SWATCHES.purple} />}
                label="Roxo"
              />
            </Section>

            <Section label="Idioma" last>
              <Option
                active
                onClick={() => {}}
                icon={<Globe size={13} />}
                label="Português"
                hint="PT-BR"
              />
              <Option
                disabled
                onClick={() => {}}
                icon={<Globe size={13} />}
                label="English"
                hint="em breve"
              />
            </Section>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Section({
  label,
  children,
  last = false,
}: {
  label: string;
  children: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div className={cn('px-2 pb-2', !last && 'border-b border-[var(--border)]')}>
      <div className="px-2 py-2 font-mono text-[9px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
        {label}
      </div>
      <div className="flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

function Option({
  active = false,
  disabled = false,
  onClick,
  icon,
  label,
  hint,
}: {
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  hint?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      role="menuitemradio"
      aria-checked={active}
      className={cn(
        'flex items-center gap-3 rounded-md px-3 py-2 text-sm text-[var(--text-primary)] transition-colors',
        !disabled && 'hover:bg-[var(--surface-raised-hover)]',
        active && 'bg-[var(--blue-500)]/10 text-[var(--blue-400)]',
        disabled && 'cursor-not-allowed opacity-40',
      )}
      data-cursor={disabled ? undefined : 'link'}
    >
      <span className={cn('shrink-0', active ? 'text-[var(--blue-400)]' : 'text-[var(--text-muted)]')}>
        {icon}
      </span>
      <span className="flex-1 text-left">{label}</span>
      {hint && (
        <span className="font-mono text-[9px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
          {hint}
        </span>
      )}
      {active && !hint && <Check size={12} className="text-[var(--blue-400)]" />}
    </button>
  );
}

function Swatch({ color }: { color: string }) {
  return (
    <span
      aria-hidden
      className="inline-block h-3 w-3 rounded-full"
      style={{ background: color, boxShadow: `0 0 8px ${color}` }}
    />
  );
}
