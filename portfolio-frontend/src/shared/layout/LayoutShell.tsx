'use client';

import { useEffect, useState } from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import { ScrollProgress } from './ScrollProgress';
import { CustomCursor } from './CustomCursor';
import { CommandPalette } from './CommandPalette';
import { KonamiEasterEgg } from './KonamiEasterEgg';
import { ToastProvider } from '@/shared/ui/ToastProvider';
import { ParticleCanvas } from '@/shared/effects/ParticleCanvas';
import { ThemeProvider } from '@/shared/theme/ThemeProvider';

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((p) => !p);
      }
      if (e.key === 'Escape') setPaletteOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <ThemeProvider>
      <ParticleCanvas />
      <ScrollProgress />
      <CustomCursor />
      <Header onCommandOpen={() => setPaletteOpen(true)} />
      <main id="main" className="pt-16">
        {children}
      </main>
      <Footer />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <KonamiEasterEgg />
      <ToastProvider />
    </ThemeProvider>
  );
}
