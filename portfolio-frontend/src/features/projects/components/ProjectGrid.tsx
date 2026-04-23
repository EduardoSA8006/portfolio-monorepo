'use client';

import { motion, AnimatePresence } from 'framer-motion';
import type { Project } from '@/core/domain/project';
import { ProjectCard } from './ProjectCard';

export function ProjectGrid({ projects }: { projects: Project[] }) {
  if (projects.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
        <p className="text-sm text-[var(--text-secondary)]">
          Nenhum projeto encontrado com esses filtros.
        </p>
      </div>
    );
  }

  return (
    <motion.div layout className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <AnimatePresence mode="popLayout">
        {projects.map((p) => (
          <motion.div
            key={p.slug}
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <ProjectCard project={p} />
          </motion.div>
        ))}
      </AnimatePresence>
    </motion.div>
  );
}
