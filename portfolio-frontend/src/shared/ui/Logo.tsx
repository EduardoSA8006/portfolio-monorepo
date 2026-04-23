import { cn } from '@/core/utils';

type LogoSize = 'sm' | 'md' | 'lg' | 'xl';

const sizeClasses: Record<LogoSize, string> = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-xl',
  xl: 'text-3xl md:text-4xl',
};

export function Logo({
  size = 'sm',
  glow = false,
  className,
}: {
  size?: LogoSize;
  glow?: boolean;
  className?: string;
}) {
  return (
    <span
      aria-label="Eduardo.dev"
      className={cn(
        'inline-flex items-baseline font-mono font-semibold tracking-tight text-[var(--text-primary)] select-none whitespace-nowrap',
        sizeClasses[size],
        className,
      )}
    >
      <span
        className="text-[var(--logo-accent)]"
        style={glow ? { textShadow: 'var(--logo-accent-glow)' } : undefined}
        aria-hidden
      >
        &lt;
      </span>
      <span>Eduardo</span>
      <span className="text-[var(--text-secondary)]" aria-hidden>
        .
      </span>
      <span>dev</span>
      <span
        className="text-[var(--logo-accent)]"
        style={glow ? { textShadow: 'var(--logo-accent-glow)' } : undefined}
        aria-hidden
      >
        /&gt;
      </span>
    </span>
  );
}
