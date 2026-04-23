import { cn } from '@/core/utils';

export function Chip({
  children,
  active = false,
  onClick,
  className,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  const Component = onClick ? 'button' : 'span';
  return (
    <Component
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs transition-colors',
        active
          ? 'border-[var(--blue-500)]/50 bg-[var(--blue-500)]/15 text-[var(--blue-300)]'
          : 'border-white/10 bg-white/[0.03] text-[var(--text-secondary)] hover:border-white/20 hover:text-white',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      {children}
    </Component>
  );
}
