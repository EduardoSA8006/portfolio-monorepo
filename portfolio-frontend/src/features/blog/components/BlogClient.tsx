'use client';

import { useMemo, useState } from 'react';
import type { Post } from '@/core/domain/post';
import { PostGrid } from '@/features/blog/components/PostGrid';
import { PostFilters } from '@/features/blog/components/PostFilters';

export function BlogClient({ posts, tags }: { posts: Post[]; tags: string[] }) {
  const [query, setQuery] = useState('');
  const [activeTags, setActiveTags] = useState<string[]>([]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return posts.filter((p) => {
      const byQuery =
        q.length === 0 ||
        p.title.toLowerCase().includes(q) ||
        p.excerpt.toLowerCase().includes(q);
      const byTags =
        activeTags.length === 0 || activeTags.every((t) => p.tags.includes(t));
      return byQuery && byTags;
    });
  }, [posts, query, activeTags]);

  return (
    <>
      <PostFilters
        query={query}
        onQuery={setQuery}
        tags={tags}
        activeTags={activeTags}
        onToggleTag={(tag) =>
          setActiveTags((prev) =>
            prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
          )
        }
        onClear={() => {
          setQuery('');
          setActiveTags([]);
        }}
        total={posts.length}
        visible={filtered.length}
      />
      <PostGrid posts={filtered} />
    </>
  );
}
