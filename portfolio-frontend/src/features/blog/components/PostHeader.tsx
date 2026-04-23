import Image from 'next/image';
import Link from 'next/link';
import { ChevronLeft, Clock } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import type { Post } from '@/core/domain/post';
import { formatDate } from '@/core/utils';

export function PostHeader({ post }: { post: Post }) {
  return (
    <header className="relative overflow-hidden pt-12 pb-10 md:pt-16">
      <AuroraBg intensity="subtle" />
      <GridBg />
      <Container size="narrow">
        <Link
          href="/blog"
          className="mb-8 inline-flex items-center gap-1 font-mono text-xs text-[var(--text-secondary)] transition-colors hover:text-white"
          data-cursor="link"
        >
          <ChevronLeft size={14} /> / blog
        </Link>
        <div className="flex flex-wrap gap-2">
          {post.tags.map((t) => (
            <span
              key={t}
              className="rounded-md border border-[var(--blue-500)]/25 bg-[var(--blue-500)]/10 px-2 py-0.5 font-mono text-[10px] text-[var(--blue-300)]"
            >
              #{t}
            </span>
          ))}
        </div>
        <h1 className="mt-5 text-3xl leading-[1.1] font-semibold tracking-[-0.03em] text-white md:text-5xl">
          {post.title}
        </h1>
        <div className="mt-6 flex flex-wrap items-center gap-3 font-mono text-[10px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
          <span>{post.author}</span>
          <span className="h-px w-4 bg-white/15" />
          <span>{formatDate(post.date)}</span>
          <span className="h-px w-4 bg-white/15" />
          <span className="inline-flex items-center gap-1">
            <Clock size={10} /> {post.readingTime} min de leitura
          </span>
        </div>
        <div className="relative mt-10 aspect-[16/9] overflow-hidden rounded-xl border border-white/[0.08]">
          <Image
            src={post.cover}
            alt={post.title}
            fill
            priority
            sizes="(max-width: 768px) 100vw, 768px"
            className="object-cover"
          />
        </div>
      </Container>
    </header>
  );
}
