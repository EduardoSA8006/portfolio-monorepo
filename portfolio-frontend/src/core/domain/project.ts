export type ProjectCategory = 'Web' | 'Mobile' | 'Fullstack';

export interface ProjectApproach {
  icon: string;
  title: string;
  body: string;
}

export interface ProjectResult {
  value: string;
  label: string;
}

export interface Project {
  slug: string;
  title: string;
  category: ProjectCategory;
  year: number;
  duration: string;
  role: string;
  summary: string;
  cover: string;
  gallery: string[];
  stack: string[];
  challenge: string;
  approach: ProjectApproach[];
  results: ProjectResult[];
  liveUrl?: string;
  repoUrl?: string;
  featured?: boolean;
}
