import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { MDXRemote } from 'next-mdx-remote/rsc';
import rehypeSlug from 'rehype-slug';
import rehypeAutolinkHeadings from 'rehype-autolink-headings';
import rehypePrettyCode from 'rehype-pretty-code';
import remarkGfm from 'remark-gfm';
import { Container } from '@/shared/ui/Container';
import { PostHeader } from '@/features/blog/components/PostHeader';
import { TableOfContents } from '@/features/blog/components/TableOfContents';
import { ShareBar } from '@/features/blog/components/ShareBar';
import { MDXComponents } from '@/features/blog/components/MDXComponents';
import { getAllPostSlugs, getPostBySlug, getAllPosts } from '@/features/blog/lib/mdx';
import { PostCard } from '@/features/blog/components/PostCard';
import { JsonLd } from '@/shared/seo/JsonLd';
import { articleJsonLd, breadcrumbJsonLd } from '@/core/utils/seo';

export async function generateStaticParams() {
  const slugs = await getAllPostSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.excerpt,
    keywords: post.tags,
    authors: [{ name: post.author, url: 'https://eduardoalves.online' }],
    alternates: { canonical: `/blog/${post.slug}` },
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: 'article',
      publishedTime: post.date,
      modifiedTime: post.date,
      authors: [post.author],
      tags: post.tags,
      url: `/blog/${post.slug}`,
      images: [
        {
          url: `/api/og?title=${encodeURIComponent(post.title)}&subtitle=${encodeURIComponent(post.excerpt)}&eyebrow=${encodeURIComponent('Blog')}`,
          width: 1200,
          height: 630,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.excerpt,
    },
  };
}

export default async function PostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) notFound();

  const nextPosts = (await getAllPosts()).filter((p) => p.slug !== slug).slice(0, 2);

  const siteUrl = 'https://eduardoalves.online';
  const postUrl = `${siteUrl}/blog/${post.slug}`;

  return (
    <>
      <JsonLd
        data={[
          articleJsonLd(post),
          breadcrumbJsonLd([
            { name: 'Home', url: '/' },
            { name: 'Blog', url: '/blog' },
            { name: post.title, url: `/blog/${post.slug}` },
          ]),
        ]}
      />
      <PostHeader post={post} />

      <Container size="narrow">
        <div className="grid gap-10 py-10 lg:grid-cols-[220px_1fr]">
          <TableOfContents />
          <article className="prose">
            <MDXRemote
              source={post.content}
              components={MDXComponents}
              options={{
                mdxOptions: {
                  remarkPlugins: [remarkGfm],
                  rehypePlugins: [
                    rehypeSlug,
                    [rehypeAutolinkHeadings, { behavior: 'wrap' }],
                    [rehypePrettyCode, { theme: 'github-dark-dimmed', keepBackground: false }],
                  ],
                },
              }}
            />
            <ShareBar title={post.title} url={postUrl} />
          </article>
        </div>
      </Container>

      <section className="border-t border-white/[0.06] py-16">
        <Container>
          <div className="mb-8 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
            / continue lendo
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            {nextPosts.map((p) => (
              <PostCard key={p.slug} post={p} />
            ))}
          </div>
        </Container>
      </section>
    </>
  );
}
