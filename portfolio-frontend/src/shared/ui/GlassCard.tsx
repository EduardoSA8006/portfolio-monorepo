import { cn } from '@/core/utils';

export function GlassCard({
  children,
  className,
  hover = false,
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-white/[0.08] bg-[var(--bg-glass)] p-6 backdrop-blur-[8px]',
        'shadow-[0_30px_60px_-20px_rgba(0,0,0,0.6)]',
        hover && 'transition-all duration-300 hover:border-white/[0.15] hover:bg-white/[0.06]',
        className,
      )}
    >
      {children}
    </div>
  );
}
