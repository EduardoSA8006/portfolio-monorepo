'use client';

import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/core/utils';

export function TextReveal({
  children,
  className,
  delay = 0,
  as: Component = 'span',
}: {
  children: string;
  className?: string;
  delay?: number;
  as?: React.ElementType;
}) {
  const Tag = Component as React.ElementType<React.HTMLAttributes<HTMLElement>>;
  const reduceMotion = useReducedMotion();
  if (reduceMotion) {
    return <Tag className={className}>{children}</Tag>;
  }

  const words = children.split(' ');
  return (
    <Tag className={cn('inline-block', className)}>
      {words.map((word, i) => (
        <span key={i} className="inline-block overflow-hidden align-bottom">
          <motion.span
            className="inline-block"
            initial={{ y: '110%' }}
            animate={{ y: 0 }}
            transition={{
              duration: 0.7,
              delay: delay + i * 0.06,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            {word}
            {i < words.length - 1 && '\u00A0'}
          </motion.span>
        </span>
      ))}
    </Tag>
  );
}
