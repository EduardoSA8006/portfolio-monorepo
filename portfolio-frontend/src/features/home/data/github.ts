function generateContributions(seed = 42): number[] {
  const out: number[] = [];
  let rand = seed;
  for (let i = 0; i < 364; i++) {
    rand = (rand * 9301 + 49297) % 233280;
    const r = rand / 233280;
    let val = 0;
    if (r > 0.3) val = 1;
    if (r > 0.55) val = 2;
    if (r > 0.75) val = 3;
    if (r > 0.92) val = 4;
    out.push(val);
  }
  return out;
}

export const github = {
  username: 'eduardosilva',
  contributions: generateContributions(),
  topRepos: [
    {
      name: 'portfolio-template',
      description: 'Template profissional de portfólio em Next.js 15 com tema escuro e azul.',
      stars: 342,
      language: 'TypeScript',
      languageColor: '#3178c6',
    },
    {
      name: 'react-native-glass-ui',
      description: 'Kit de componentes com glassmorphism para React Native + Expo.',
      stars: 218,
      language: 'TypeScript',
      languageColor: '#3178c6',
    },
    {
      name: 'next-blog-starter',
      description: 'Starter MDX com Shiki, OG dinâmica e SEO em dia.',
      stars: 167,
      language: 'TypeScript',
      languageColor: '#3178c6',
    },
  ],
  stats: {
    commitsYear: 820,
    pullRequests: 124,
    stars: 450,
    streak: 47,
  },
};
