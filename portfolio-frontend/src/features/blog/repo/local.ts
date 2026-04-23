import fs from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';
import type { PostFrontmatter } from '@/core/domain/post';
import type { PostsRepo } from './types';

const BLOG_DIR = path.join(process.cwd(), 'src', 'features', 'blog', 'content');

function readRaw(slug: string): { content: string; data: Record<string, unknown> } {
  const filePath = path.join(BLOG_DIR, `${slug}.mdx`);
  const raw = fs.readFileSync(filePath, 'utf-8');
  const { content, data } = matter(raw);
  return { content, data };
}

function parseFrontmatter(data: Record<string, unknown>): PostFrontmatter {
  return {
    title: String(data.title ?? ''),
    date: String(data.date ?? ''),
    tags: Array.isArray(data.tags) ? (data.tags as string[]) : [],
    readingTime: Number(data.readingTime ?? 5),
    cover: String(data.cover ?? '/images/blog/default.jpg'),
    excerpt: String(data.excerpt ?? ''),
    author: String(data.author ?? 'Eduardo Alves'),
  };
}

function listSlugs(): string[] {
  if (!fs.existsSync(BLOG_DIR)) return [];
  return fs
    .readdirSync(BLOG_DIR)
    .filter((f) => f.endsWith('.mdx'))
    .map((f) => f.replace(/\.mdx$/, ''));
}

export const localMdxRepo: PostsRepo = {
  async getAllSlugs() {
    return listSlugs();
  },
  async getAll() {
    return listSlugs()
      .map((slug) => {
        const { content, data } = readRaw(slug);
        return { slug, content, ...parseFrontmatter(data) };
      })
      .sort((a, b) => (a.date < b.date ? 1 : -1));
  },
  async getBySlug(slug) {
    try {
      const { content, data } = readRaw(slug);
      return { slug, content, ...parseFrontmatter(data) };
    } catch {
      return null;
    }
  },
  async getRecent(limit = 3) {
    const all = await this.getAll();
    return all.slice(0, limit);
  },
  async getAllTags() {
    const all = await this.getAll();
    const tags = new Set<string>();
    for (const post of all) post.tags.forEach((t) => tags.add(t));
    return Array.from(tags).sort();
  },
};
