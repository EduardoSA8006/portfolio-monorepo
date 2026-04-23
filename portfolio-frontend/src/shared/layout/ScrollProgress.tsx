'use client';

import { motion, useScroll, useSpring } from 'framer-motion';

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 24, restDelta: 0.001 });

  return (
    <motion.div
      aria-hidden
      className="fixed top-0 right-0 left-0 z-[60] h-[2px] origin-left"
      style={{ scaleX, background: 'var(--gradient-btn)' }}
    />
  );
}
