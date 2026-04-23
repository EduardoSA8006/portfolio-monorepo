import { localProjectsRepo } from './local';
// import { httpProjectsRepo } from './http';

/**
 * Single source of truth for project data. Swap to `httpProjectsRepo`
 * (and set PROJECTS_API_URL) to migrate the site off local data
 * without touching any page, component or sitemap.
 */
export const projectsRepo = localProjectsRepo;

export type { ProjectsRepo } from './types';
