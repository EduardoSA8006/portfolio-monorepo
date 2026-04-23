import type { Post } from '@/core/domain/post';
import type { PostsRepo } from './types';

/**
 * HTTP implementation (stub). Plug this in when the backend is live.
 * Expected endpoints are documented in ../API_CONTRACT.md.
 *
 * To activate: set NEXT_PUBLIC_BLOG_API_URL and switch the export in
 * ./index.ts from localMdxRepo to httpPostsRepo.
 */
const API_URL = process.env.BLOG_API_URL ?? process.env.NEXT_PUBLIC_BLOG_API_URL ?? '';
const REVALIDATE_SECONDS = 300;

async function request<T>(path: string, tag: string): Promise<T> {
  if (!API_URL) throw new Error('BLOG_API_URL is not configured');
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: REVALIDATE_SECONDS, tags: ['posts', tag] },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

export const httpPostsRepo: PostsRepo = {
  async getAllSlugs() {
    return request<string[]>('/posts/slugs', 'slugs');
  },
  async getAll() {
    return request<Post[]>('/posts', 'list');
  },
  async getBySlug(slug) {
    try {
      return await request<Post>(`/posts/${encodeURIComponent(slug)}`, `post:${slug}`);
    } catch {
      return null;
    }
  },
  async getRecent(limit = 3) {
    return request<Post[]>(`/posts?limit=${limit}`, `recent:${limit}`);
  },
  async getAllTags() {
    return request<string[]>('/posts/tags', 'tags');
  },
};
