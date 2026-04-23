import { Container } from '@/shared/ui/Container';
import { cn } from '@/core/utils';

export function CaseStudySection({
  eyebrow,
  title,
  children,
  className,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('py-16 md:py-20', className)}>
      <Container>
        <div className="grid gap-10 md:grid-cols-[240px_1fr]">
          <div className="shrink-0">
            <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              {eyebrow}
            </div>
            <h2 className="text-2xl font-semibold tracking-[-0.02em] text-white md:text-3xl">
              {title}
            </h2>
          </div>
          <div className="max-w-3xl">{children}</div>
        </div>
      </Container>
    </section>
  );
}
