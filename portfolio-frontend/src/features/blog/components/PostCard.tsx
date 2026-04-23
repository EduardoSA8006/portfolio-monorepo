import Link from 'next/link';
import Image from 'next/image';
import { Clock } from 'lucide-react';
import type { Post } from '@/core/domain/post';
import { formatDate } from '@/core/utils';

export function PostCard({ post }: { post: Post }) {
  return (
    <Link
      href={`/blog/${post.slug}`}
      data-cursor="link"
      className="group flex h-full flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02] transition-colors hover:border-white/[0.18] hover:bg-white/[0.04]"
    >
      <div className="relative aspect-[16/10] overflow-hidden">
        <Image
          src={post.cover}
          alt={post.title}
          fill
          sizes="(max-width: 768px) 100vw, 33vw"
          className="object-cover transition-transform duration-700 group-hover:scale-[1.05]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
      </div>
      <div className="flex flex-1 flex-col p-5">
        <div className="flex flex-wrap items-center gap-3 font-mono text-[10px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
          <span>{formatDate(post.date)}</span>
          <span className="h-px w-4 bg-white/15" />
          <span className="inline-flex items-center gap-1">
            <Clock size={10} /> {post.readingTime} min
          </span>
        </div>
        <h3 className="mt-3 text-lg font-semibold leading-snug tracking-[-0.015em] text-white transition-colors group-hover:text-[var(--blue-300)]">
          {post.title}
        </h3>
        <p className="mt-2 line-clamp-3 flex-1 text-sm text-[var(--text-secondary)]">{post.excerpt}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {post.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-md border border-[var(--blue-500)]/25 bg-[var(--blue-500)]/10 px-2 py-0.5 font-mono text-[10px] text-[var(--blue-300)]"
            >
              #{tag}
            </span>
          ))}
        </div>
      </div>
    </Link>
  );
}
