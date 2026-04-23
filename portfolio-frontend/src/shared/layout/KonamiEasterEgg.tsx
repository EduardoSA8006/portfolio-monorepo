'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'sonner';

const SEQUENCE = [
  'ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a',
];
const CHARS = 'アイウエオカキクケコサシスセソタチツテト0123456789';

export function KonamiEasterEgg() {
  const [active, setActive] = useState(false);
  const buf = useRef<string[]>([]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      const next = [...buf.current, key].slice(-SEQUENCE.length);
      buf.current = next;
      if (next.length === SEQUENCE.length && next.every((k, i) => k === SEQUENCE[i])) {
        setActive(true);
        toast.success('Easter egg desbloqueado ✨');
        setTimeout(() => setActive(false), 5000);
        buf.current = [];
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          aria-hidden
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="pointer-events-none fixed inset-0 z-[120] overflow-hidden"
        >
          {/* eslint-disable react-hooks/purity */}
          {Array.from({ length: 60 }).map((_, i) => (
            <motion.span
              key={i}
              initial={{ y: '-10%', opacity: 0 }}
              animate={{ y: '110%', opacity: [0, 1, 1, 0] }}
              transition={{
                duration: 2 + Math.random() * 2,
                delay: Math.random() * 4,
                ease: 'linear',
              }}
              style={{
                position: 'absolute',
                left: `${(i / 60) * 100}%`,
                fontFamily: 'var(--font-mono), monospace',
                color: '#60a5fa',
                fontSize: 14,
                textShadow: '0 0 8px rgba(96,165,250,0.6)',
              }}
            >
              {CHARS[Math.floor(Math.random() * CHARS.length)]}
            </motion.span>
          ))}
          {/* eslint-enable react-hooks/purity */}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
