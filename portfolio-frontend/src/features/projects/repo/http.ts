import type { Project } from '@/core/domain/project';
import type { ProjectsRepo } from './types';

/**
 * HTTP implementation (stub). See ../API_CONTRACT.md for the expected
 * backend shape. Activate by pointing PROJECTS_API_URL and switching
 * the export in ./index.ts.
 */
const API_URL = process.env.PROJECTS_API_URL ?? process.env.NEXT_PUBLIC_PROJECTS_API_URL ?? '';
const REVALIDATE_SECONDS = 300;

async function request<T>(path: string, tag: string): Promise<T> {
  if (!API_URL) throw new Error('PROJECTS_API_URL is not configured');
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: REVALIDATE_SECONDS, tags: ['projects', tag] },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

export const httpProjectsRepo: ProjectsRepo = {
  async getAll() {
    return request<Project[]>('/projects', 'list');
  },
  async getBySlug(slug) {
    try {
      return await request<Project>(`/projects/${encodeURIComponent(slug)}`, `project:${slug}`);
    } catch {
      return null;
    }
  },
  async getFeatured(limit = 3) {
    return request<Project[]>(`/projects?featured=1&limit=${limit}`, `featured:${limit}`);
  },
  async getNext(slug) {
    try {
      return await request<Project>(`/projects/${encodeURIComponent(slug)}/next`, `next:${slug}`);
    } catch {
      return null;
    }
  },
};
