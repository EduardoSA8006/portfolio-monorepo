import { cn } from '@/core/utils';

export function GradientText({
  children,
  className,
  as: Component = 'span',
}: {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
}) {
  const Tag = Component as React.ElementType<React.HTMLAttributes<HTMLElement>>;
  return (
    <Tag
      className={cn('bg-clip-text text-transparent', className)}
      style={{ backgroundImage: 'var(--gradient-text)' }}
    >
      {children}
    </Tag>
  );
}
