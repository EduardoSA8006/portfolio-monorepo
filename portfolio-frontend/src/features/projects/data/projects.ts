/**
 * Async accessors — the canonical way to read projects. Backed by the
 * repository and will transparently pull from an HTTP backend once
 * projectsRepo is switched to httpProjectsRepo.
 */
import { projectsRepo } from '@/features/projects/repo';

export const getAllProjects = () => projectsRepo.getAll();
export const getProjectBySlug = (slug: string) => projectsRepo.getBySlug(slug);
export const getFeaturedProjects = (limit = 3) => projectsRepo.getFeatured(limit);
export const getNextProject = (slug: string) => projectsRepo.getNext(slug);

/**
 * Sync fallback exposing the local seed array. Used ONLY by Client
 * Components that cannot await at render (CommandPalette, home
 * ProjectsPreview carousel). When migrating to a backend, lift these
 * components so a server parent fetches via getFeaturedProjects and
 * passes results as props — then delete this fallback.
 */
export { projects as localProjects } from '@/features/projects/repo/local';
