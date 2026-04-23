'use client';

import { motion, AnimatePresence } from 'framer-motion';
import type { Post } from '@/core/domain/post';
import { PostCard } from './PostCard';

export function PostGrid({ posts }: { posts: Post[] }) {
  if (posts.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
        <p className="text-sm text-[var(--text-secondary)]">Nenhum post encontrado.</p>
      </div>
    );
  }
  return (
    <motion.div layout className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <AnimatePresence mode="popLayout">
        {posts.map((post) => (
          <motion.div
            key={post.slug}
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
          >
            <PostCard post={post} />
          </motion.div>
        ))}
      </AnimatePresence>
    </motion.div>
  );
}
