import { cn } from '@/core/utils';

export function AuroraBg({
  className,
  intensity = 'base',
}: {
  className?: string;
  intensity?: 'subtle' | 'base' | 'strong';
}) {
  const opacities = {
    subtle: { main: 0.35, secondary: 0.25, accent: 0.15 },
    base: { main: 0.55, secondary: 0.45, accent: 0.3 },
    strong: { main: 0.75, secondary: 0.6, accent: 0.4 },
  }[intensity];

  return (
    <div
      aria-hidden
      className={cn('pointer-events-none absolute inset-0 overflow-hidden', className)}
    >
      <div
        className="absolute rounded-full blur-[80px]"
        style={{
          width: 480,
          height: 480,
          top: -140,
          left: -120,
          background: 'var(--aurora-blob-1)',
          opacity: opacities.main,
        }}
      />
      <div
        className="absolute rounded-full blur-[80px]"
        style={{
          width: 400,
          height: 400,
          bottom: -100,
          right: -90,
          background: 'var(--aurora-blob-2)',
          opacity: opacities.secondary,
        }}
      />
      <div
        className="absolute rounded-full blur-[80px]"
        style={{
          width: 300,
          height: 300,
          top: '38%',
          left: '55%',
          background: 'var(--aurora-blob-3)',
          opacity: opacities.accent,
        }}
      />
    </div>
  );
}
