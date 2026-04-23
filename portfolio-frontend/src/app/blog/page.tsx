import type { Metadata } from 'next';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { getAllPosts, getAllTags } from '@/features/blog/lib/mdx';
import { BlogClient } from '@/features/blog/components/BlogClient';

export const metadata: Metadata = {
  title: 'Blog',
  description:
    'Artigos técnicos sobre React, Next.js, mobile, performance e design system. Atualizado regularmente.',
  alternates: { canonical: '/blog' },
};

export default async function BlogPage() {
  const [posts, tags] = await Promise.all([getAllPosts(), getAllTags()]);

  return (
    <section className="relative overflow-hidden py-24 md:py-32">
      <AuroraBg intensity="subtle" />
      <GridBg />
      <Container>
        <SectionHeader
          eyebrow="/ BLOG"
          title="Escritos técnicos."
          description={`${posts.length} artigos sobre o que aprendo construindo produtos. Filtre por tag ou busque por termo.`}
        />
        <BlogClient posts={posts} tags={tags} />
      </Container>
    </section>
  );
}
