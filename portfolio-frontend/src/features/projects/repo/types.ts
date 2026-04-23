import type { Project } from '@/core/domain/project';

/**
 * Contract for project access. Local implementation reads from a
 * static array; HTTP implementation fetches from a backend API.
 */
export interface ProjectsRepo {
  getAll(): Promise<Project[]>;
  getBySlug(slug: string): Promise<Project | null>;
  getFeatured(limit?: number): Promise<Project[]>;
  getNext(slug: string): Promise<Project | null>;
}
