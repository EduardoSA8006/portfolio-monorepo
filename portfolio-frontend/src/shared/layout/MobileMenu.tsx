'use client';

import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { navLinks } from '@/core/config/navigation';
import { profile } from '@/core/config/profile';
import { AvailabilityBadge } from '@/shared/ui/Badge';
import { Logo } from '@/shared/ui/Logo';

export function MobileMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="fixed top-0 right-0 bottom-0 z-50 flex w-[82%] max-w-sm flex-col border-l border-white/10 bg-[var(--bg-surface)] p-6 md:hidden"
          >
            <div className="flex items-center justify-between">
              <Logo size="sm" />
              <button
                onClick={onClose}
                aria-label="Fechar menu"
                className="rounded-md p-2 text-white hover:bg-white/5"
              >
                <X size={18} />
              </button>
            </div>
            <nav className="mt-10 flex flex-col gap-2">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={onClose}
                  className="rounded-lg px-4 py-3 text-lg font-medium text-white transition-colors hover:bg-white/[0.05]"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
            <div className="mt-auto flex flex-col gap-3 border-t border-white/10 pt-6">
              <AvailabilityBadge />
              <a
                href={`mailto:${profile.email}`}
                className="text-sm text-[var(--text-secondary)] hover:text-white"
              >
                {profile.email}
              </a>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
