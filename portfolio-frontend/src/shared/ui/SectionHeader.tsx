import { cn } from '@/core/utils';

export function SectionHeader({
  eyebrow,
  title,
  description,
  align = 'left',
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: string;
  align?: 'left' | 'center';
  className?: string;
}) {
  return (
    <div
      className={cn(
        'mb-14 max-w-3xl',
        align === 'center' && 'mx-auto text-center',
        className,
      )}
    >
      {eyebrow && (
        <div
          className={cn(
            'mb-4 flex items-center gap-3 font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase',
            align === 'center' && 'justify-center',
          )}
        >
          <span className="h-px w-6 bg-[var(--blue-500)]" />
          {eyebrow}
        </div>
      )}
      <h2 className="text-3xl leading-[1.05] font-semibold tracking-[-0.03em] text-white md:text-5xl">
        {title}
      </h2>
      {description && (
        <p
          className={cn(
            'mt-5 text-base leading-relaxed text-[var(--text-secondary)] md:text-lg',
            align === 'center' && 'text-center',
          )}
          style={
            align === 'center'
              ? { textAlign: 'center', textAlignLast: 'center' }
              : undefined
          }
        >
          {description}
        </p>
      )}
    </div>
  );
}
