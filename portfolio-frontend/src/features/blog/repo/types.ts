import type { Post } from '@/core/domain/post';

/**
 * Contract for blog post access. The current implementation reads local
 * MDX files; a future implementation will fetch from an HTTP backend.
 * All methods are async by contract so swapping the implementation
 * never changes call sites.
 */
export interface PostsRepo {
  getAllSlugs(): Promise<string[]>;
  getAll(): Promise<Post[]>;
  getBySlug(slug: string): Promise<Post | null>;
  getRecent(limit?: number): Promise<Post[]>;
  getAllTags(): Promise<string[]>;
}
