import { localMdxRepo } from './local';
// import { httpPostsRepo } from './http';

/**
 * The single source of truth for blog data. Swap to `httpPostsRepo`
 * (and set BLOG_API_URL) to migrate the site off local MDX without
 * touching any page, component or sitemap — every call site already
 * awaits the same PostsRepo contract.
 */
export const postsRepo = localMdxRepo;

export type { PostsRepo } from './types';
