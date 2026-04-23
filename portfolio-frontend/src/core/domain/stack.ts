export type StackCategory = 'Linguagens' | 'Frameworks' | 'Backend & Infra' | 'Ferramentas';

export interface StackItem {
  name: string;
  category: StackCategory;
  icon: string;
  level: 1 | 2 | 3 | 4 | 5;
}
