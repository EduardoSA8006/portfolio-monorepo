import type { StackItem } from '@/core/domain/stack';

export const stack: StackItem[] = [
  // Linguagens
  { name: 'Dart', category: 'Linguagens', icon: 'dart', level: 5 },
  { name: 'Python', category: 'Linguagens', icon: 'python', level: 4 },
  { name: 'JavaScript', category: 'Linguagens', icon: 'javascript', level: 4 },
  { name: 'Java', category: 'Linguagens', icon: 'java', level: 2 },
  { name: 'C++', category: 'Linguagens', icon: 'cpp', level: 2 },
  { name: 'C#', category: 'Linguagens', icon: 'csharp', level: 2 },
  { name: 'Lua', category: 'Linguagens', icon: 'lua', level: 2 },

  // Frameworks
  { name: 'Flutter', category: 'Frameworks', icon: 'flutter', level: 5 },
  { name: 'FastAPI', category: 'Frameworks', icon: 'fastapi', level: 5 },
  { name: 'React', category: 'Frameworks', icon: 'react', level: 4 },
  { name: 'Vue.js', category: 'Frameworks', icon: 'vue', level: 2 },

  // Backend & Infra
  { name: 'PostgreSQL', category: 'Backend & Infra', icon: 'postgresql', level: 4 },
  { name: 'Redis', category: 'Backend & Infra', icon: 'redis', level: 4 },
  { name: 'JWT / Auth', category: 'Backend & Infra', icon: 'jwt', level: 4 },
  { name: 'REST APIs', category: 'Backend & Infra', icon: 'rest', level: 5 },
  { name: 'Firebase', category: 'Backend & Infra', icon: 'firebase', level: 3 },

  // Ferramentas
  { name: 'Git', category: 'Ferramentas', icon: 'git', level: 5 },
  { name: 'Linux / Ubuntu', category: 'Ferramentas', icon: 'linux', level: 4 },
  { name: 'Terminal / Shell', category: 'Ferramentas', icon: 'terminal', level: 4 },
  { name: 'Docker', category: 'Ferramentas', icon: 'docker', level: 3 },
  { name: 'ESP32 / IoT', category: 'Ferramentas', icon: 'esp32', level: 2 },
];
