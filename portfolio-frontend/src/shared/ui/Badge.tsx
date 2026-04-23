import { cn } from '@/core/utils';

export function Badge({
  children,
  tone = 'blue',
  className,
}: {
  children: React.ReactNode;
  tone?: 'blue' | 'neutral' | 'success';
  className?: string;
}) {
  const tones = {
    blue: 'bg-[var(--blue-500)]/10 text-[var(--blue-300)] border-[var(--blue-500)]/30',
    neutral: 'bg-white/[0.04] text-[var(--text-secondary)] border-white/10',
    success: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] tracking-[0.15em] uppercase',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function AvailabilityBadge() {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
      </span>
      Disponível
    </span>
  );
}
