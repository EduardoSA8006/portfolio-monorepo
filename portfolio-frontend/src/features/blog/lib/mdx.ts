/**
 * Thin async wrappers over the blog repository. Kept for call-site
 * familiarity — internally everything delegates to postsRepo, so
 * swapping the repo implementation (local MDX <-> HTTP backend)
 * propagates here for free.
 */
import { postsRepo } from '@/features/blog/repo';

export const getAllPostSlugs = () => postsRepo.getAllSlugs();
export const getAllPosts = () => postsRepo.getAll();
export const getPostBySlug = (slug: string) => postsRepo.getBySlug(slug);
export const getRecentPosts = (limit = 3) => postsRepo.getRecent(limit);
export const getAllTags = () => postsRepo.getAllTags();
