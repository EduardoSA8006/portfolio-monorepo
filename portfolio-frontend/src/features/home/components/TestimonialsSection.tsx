'use client';

import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Quote } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { GlassCard } from '@/shared/ui/GlassCard';
import { cn } from '@/core/utils';
import { testimonials } from '@/features/home/data/testimonials';

export function TestimonialsSection() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const total = testimonials.length;

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % total), 6000);
    return () => clearInterval(id);
  }, [paused, total]);

  const current = testimonials[index]!;
  const prev = () => setIndex((i) => (i - 1 + total) % total);
  const next = () => setIndex((i) => (i + 1) % total);

  return (
    <section
      id="depoimentos"
      className="relative py-24 md:py-32"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <Container>
        <SectionHeader
          eyebrow="/ DEPOIMENTOS"
          title="O que clientes dizem."
          align="center"
          className="mx-auto text-center"
        />
        <div className="mx-auto max-w-3xl">
          <GlassCard className="relative overflow-hidden">
            <Quote
              className="absolute top-5 right-6 text-[var(--blue-500)]/25"
              size={80}
              aria-hidden
            />
            <AnimatePresence mode="wait">
              <motion.blockquote
                key={index}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="relative"
              >
                <p className="text-lg leading-relaxed text-[var(--text-primary)] md:text-xl">
                  &quot;{current.quote}&quot;
                </p>
                <footer className="mt-6 flex items-center gap-3">
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold text-white text-on-primary"
                    style={{ background: 'var(--gradient-btn)' }}
                    aria-hidden
                  >
                    {current.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">{current.name}</div>
                    <div className="font-mono text-[11px] text-[var(--text-secondary)]">
                      {current.role} · {current.company}
                    </div>
                  </div>
                </footer>
              </motion.blockquote>
            </AnimatePresence>
          </GlassCard>

          <div className="mt-6 flex items-center justify-center gap-4">
            <button
              onClick={prev}
              aria-label="Depoimento anterior"
              className="rounded-full border border-white/10 bg-white/[0.03] p-2 text-white transition-colors hover:border-white/20"
              data-cursor="link"
            >
              <ChevronLeft size={16} />
            </button>
            <div className="flex gap-2">
              {testimonials.map((_, i) => (
                <button
                  key={i}
                  aria-label={`Ir para depoimento ${i + 1}`}
                  onClick={() => setIndex(i)}
                  className={cn(
                    'h-1.5 rounded-full transition-all',
                    i === index ? 'w-6 bg-[var(--blue-400)]' : 'w-1.5 bg-white/20',
                  )}
                  data-cursor="link"
                />
              ))}
            </div>
            <button
              onClick={next}
              aria-label="Próximo depoimento"
              className="rounded-full border border-white/10 bg-white/[0.03] p-2 text-white transition-colors hover:border-white/20"
              data-cursor="link"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </Container>
    </section>
  );
}
