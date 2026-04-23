import type { MetadataRoute } from 'next';
import { getAllProjects } from '@/features/projects/data/projects';
import { getAllPostSlugs } from '@/features/blog/lib/mdx';

const BASE = 'https://eduardoalves.online';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const [projects, postSlugs] = await Promise.all([getAllProjects(), getAllPostSlugs()]);

  const staticRoutes = ['', '/projetos', '/blog', '/sobre', '/contato'].map((path) => ({
    url: `${BASE}${path}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: path === '' ? 1 : 0.8,
  }));

  const projectRoutes = projects.map((p) => ({
    url: `${BASE}/projetos/${p.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }));

  const postRoutes = postSlugs.map((slug) => ({
    url: `${BASE}/blog/${slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  return [...staticRoutes, ...projectRoutes, ...postRoutes];
}
