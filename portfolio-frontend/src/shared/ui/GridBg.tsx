import { cn } from '@/core/utils';

export function GridBg({
  className,
  size = 48,
  fade = 'radial',
}: {
  className?: string;
  size?: number;
  fade?: 'radial' | 'top' | 'bottom' | 'none';
}) {
  const maskMap = {
    radial: 'radial-gradient(ellipse at center, black 30%, transparent 80%)',
    top: 'linear-gradient(to bottom, black 0%, transparent 100%)',
    bottom: 'linear-gradient(to top, black 0%, transparent 100%)',
    none: 'none',
  };
  return (
    <div
      aria-hidden
      className={cn('pointer-events-none absolute inset-0', className)}
      style={{
        backgroundImage:
          'linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)',
        backgroundSize: `${size}px ${size}px`,
        WebkitMaskImage: maskMap[fade],
        maskImage: maskMap[fade],
      }}
    />
  );
}
