import { profile } from '@/core/config/profile';
import type { Post } from '@/core/domain/post';
import type { Project } from '@/core/domain/project';

export const SITE_URL = 'https://eduardoalves.online';
export const SITE_NAME = 'Eduardo Alves';
export const SITE_LOCALE = 'pt_BR';
export const DEFAULT_OG = `${SITE_URL}/images/og-default.png`;

export function absUrl(path: string): string {
  return path.startsWith('http') ? path : `${SITE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}

export function personJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Person',
    name: profile.name,
    alternateName: profile.fullName,
    jobTitle: profile.role,
    description: profile.bioShort,
    url: SITE_URL,
    image: DEFAULT_OG,
    email: `mailto:${profile.email}`,
    address: {
      '@type': 'PostalAddress',
      addressLocality: 'Ariquemes',
      addressRegion: 'RO',
      addressCountry: 'BR',
    },
    knowsAbout: [
      'Flutter',
      'FastAPI',
      'React',
      'Next.js',
      'TypeScript',
      'Python',
      'PostgreSQL',
      'Redis',
      'Linux',
    ],
    sameAs: [profile.social.github, profile.social.linkedin, profile.social.instagram],
  };
}

export function articleJsonLd(post: Post) {
  const url = absUrl(`/blog/${post.slug}`);
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.excerpt,
    image: [post.cover.startsWith('http') ? post.cover : absUrl(post.cover)],
    datePublished: post.date,
    dateModified: post.date,
    author: {
      '@type': 'Person',
      name: post.author,
      url: SITE_URL,
    },
    publisher: {
      '@type': 'Person',
      name: SITE_NAME,
      url: SITE_URL,
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': url },
    url,
    keywords: post.tags.join(', '),
    inLanguage: 'pt-BR',
  };
}

export function creativeWorkJsonLd(project: Project) {
  const url = absUrl(`/projetos/${project.slug}`);
  return {
    '@context': 'https://schema.org',
    '@type': 'CreativeWork',
    name: project.title,
    description: project.summary,
    image: [project.cover.startsWith('http') ? project.cover : absUrl(project.cover)],
    dateCreated: String(project.year),
    genre: project.category,
    keywords: project.stack.join(', '),
    creator: {
      '@type': 'Person',
      name: profile.name,
      url: SITE_URL,
    },
    url,
    inLanguage: 'pt-BR',
  };
}

export function breadcrumbJsonLd(items: Array<{ name: string; url: string }>) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: absUrl(item.url),
    })),
  };
}
