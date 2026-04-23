import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, Clock } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { Button } from '@/shared/ui/Button';
import { ScrollReveal } from '@/shared/effects/ScrollReveal';
import { getRecentPosts } from '@/features/blog/lib/mdx';
import { formatDate } from '@/core/utils';

export async function BlogPreview() {
  const posts = await getRecentPosts(3);

  return (
    <section id="blog" className="relative py-24 md:py-32">
      <Container>
        <div className="flex items-end justify-between">
          <SectionHeader eyebrow="/ BLOG" title="Escritos recentes." className="mb-0" />
          <Button href="/blog" variant="ghost" icon={<ArrowRight size={16} />} className="hidden md:inline-flex">
            Ver todos
          </Button>
        </div>

        <div className="mt-12 space-y-5">
          {posts.map((post, i) => (
            <ScrollReveal key={post.slug} delay={i * 0.05}>
              <Link
                href={`/blog/${post.slug}`}
                data-cursor="link"
                className="group flex flex-col gap-5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 transition-colors hover:border-white/[0.15] hover:bg-white/[0.04] md:flex-row md:items-center md:p-5"
              >
                <div className="relative aspect-[16/10] w-full overflow-hidden rounded-lg md:aspect-[4/3] md:w-52 md:shrink-0">
                  <Image
                    src={post.cover}
                    alt={post.title}
                    fill
                    sizes="(max-width: 768px) 100vw, 208px"
                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-3 font-mono text-[10px] tracking-[0.15em] text-[var(--text-muted)] uppercase">
                    <span>{formatDate(post.date)}</span>
                    <span className="h-px w-4 bg-white/15" />
                    <span className="inline-flex items-center gap-1">
                      <Clock size={10} /> {post.readingTime} min
                    </span>
                    {post.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className="text-[var(--blue-400)]">
                        #{tag}
                      </span>
                    ))}
                  </div>
                  <h3 className="mt-3 text-xl font-semibold tracking-[-0.02em] text-white md:text-2xl">
                    {post.title}
                  </h3>
                  <p className="mt-2 max-w-2xl text-sm text-[var(--text-secondary)]">
                    {post.excerpt}
                  </p>
                </div>
              </Link>
            </ScrollReveal>
          ))}
        </div>

        <div className="mt-10 flex justify-center md:hidden">
          <Button href="/blog" variant="ghost" icon={<ArrowRight size={16} />}>
            Ver todos os posts
          </Button>
        </div>
      </Container>
    </section>
  );
}
