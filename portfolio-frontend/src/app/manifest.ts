import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Eduardo Alves · Desenvolvedor Fullstack',
    short_name: 'Eduardo Alves',
    description:
      'Desenvolvedor fullstack com foco em Flutter, FastAPI e React. Apps, APIs e produtos completos — do banco ao deploy.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#05080f',
    theme_color: '#05080f',
    lang: 'pt-BR',
    categories: ['productivity', 'developer'],
    icons: [
      {
        src: '/icons/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/icons/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/icons/icon-maskable-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  };
}
