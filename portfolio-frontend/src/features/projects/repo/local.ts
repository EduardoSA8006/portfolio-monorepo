import type { Project } from '@/core/domain/project';
import type { ProjectsRepo } from './types';

const UNSPLASH = (query: string, w = 1600, h = 900) =>
  `https://images.unsplash.com/${query}?auto=format&fit=crop&w=${w}&h=${h}&q=80`;

export const projects: Project[] = [
  {
    slug: 'nexus-bank',
    title: 'Nexus Bank',
    category: 'Fullstack',
    year: 2025,
    duration: '4 meses',
    role: 'Lead Developer',
    summary:
      'Plataforma de internet banking para fintech com 50k+ usuários. Dashboard, transferências, investimentos e relatórios.',
    cover: UNSPLASH('photo-1551288049-bebda4e38f71'),
    gallery: [
      UNSPLASH('photo-1551288049-bebda4e38f71'),
      UNSPLASH('photo-1579621970563-ebec7560ff3e'),
      UNSPLASH('photo-1560472354-b33ff0c44a43'),
    ],
    stack: ['Next.js', 'tRPC', 'PostgreSQL', 'Prisma', 'Tailwind', 'Framer Motion'],
    challenge:
      'A Nexus Bank precisava migrar um dashboard legado em jQuery para uma stack moderna sem interromper operações. O sistema processa milhares de transações diárias e exigia latência baixíssima em todos os painéis.',
    approach: [
      {
        icon: 'zap',
        title: 'Performance radical',
        body: 'Server Components + streaming para carregar o dashboard em <1s. Consultas otimizadas com Prisma + Redis cache.',
      },
      {
        icon: 'layers',
        title: 'Arquitetura modular',
        body: 'Cada painel é um módulo independente. Feature flags com GrowthBook permitem rollouts graduais.',
      },
      {
        icon: 'shield',
        title: 'Segurança em camadas',
        body: 'MFA obrigatório, rate limiting, CSP restritivo, auditoria de todas ações sensíveis.',
      },
    ],
    results: [
      { value: '98', label: 'Lighthouse Performance' },
      { value: '3x', label: 'mais rápido que v1' },
      { value: '50k', label: 'usuários ativos' },
      { value: '<1s', label: 'tempo de carregamento' },
    ],
    liveUrl: 'https://example.com',
    repoUrl: 'https://github.com/eduardosilva',
    featured: true,
  },
  {
    slug: 'fitpulse',
    title: 'FitPulse',
    category: 'Mobile',
    year: 2025,
    duration: '3 meses',
    role: 'Senior Mobile Developer',
    summary:
      'App de fitness com planos personalizados, tracking de treinos e integração com wearables. Disponível em iOS e Android.',
    cover: UNSPLASH('photo-1571019613454-1cb2f99b2d8b'),
    gallery: [
      UNSPLASH('photo-1571019613454-1cb2f99b2d8b'),
      UNSPLASH('photo-1534438327276-14e5300c3a48'),
      UNSPLASH('photo-1517836357463-d25dfeac3438'),
    ],
    stack: ['React Native', 'Expo', 'Reanimated 3', 'Zustand', 'Supabase'],
    challenge:
      'Construir um app fitness com animações fluidas de 60fps mesmo em dispositivos Android de gama média, integrando Apple HealthKit e Google Fit.',
    approach: [
      {
        icon: 'zap',
        title: 'Animações nativas',
        body: 'Todas as animações em Reanimated 3 (UI thread). Lottie para micro-interações. Zero jank.',
      },
      {
        icon: 'heart',
        title: 'Integração wearables',
        body: 'HealthKit (iOS) + Google Fit (Android) via bridges nativas custom.',
      },
      {
        icon: 'users',
        title: 'Offline-first',
        body: 'Sincronização via MMKV + React Query com background sync.',
      },
    ],
    results: [
      { value: '4.8', label: 'estrelas na App Store' },
      { value: '60fps', label: 'animações consistentes' },
      { value: '25k', label: 'downloads em 3 meses' },
      { value: '92%', label: 'retenção D7' },
    ],
    liveUrl: 'https://example.com',
    featured: true,
  },
  {
    slug: 'atlas-crm',
    title: 'Atlas CRM',
    category: 'Fullstack',
    year: 2024,
    duration: '6 meses',
    role: 'Full-Stack Developer',
    summary:
      'Plataforma de CRM B2B com app companion mobile. Pipeline, automações, integração com WhatsApp e relatórios em tempo real.',
    cover: UNSPLASH('photo-1460925895917-afdab827c52f'),
    gallery: [
      UNSPLASH('photo-1460925895917-afdab827c52f'),
      UNSPLASH('photo-1551288049-bebda4e38f71'),
    ],
    stack: ['Next.js', 'React Native', 'Node.js', 'PostgreSQL', 'Redis', 'BullMQ'],
    challenge:
      'CRM completo com web dashboard e app mobile que pudessem operar offline e sincronizar quando online. Automações via webhooks e filas.',
    approach: [
      {
        icon: 'layers',
        title: 'Monorepo Turbo',
        body: 'Web + mobile + API em um só monorepo. Código compartilhado (schema, types, client) via packages.',
      },
      {
        icon: 'zap',
        title: 'Automação com filas',
        body: 'BullMQ + Redis processam webhooks, envios de email e notificações push. Retry automático.',
      },
      {
        icon: 'users',
        title: 'Real-time updates',
        body: 'WebSockets via Supabase Realtime. Múltiplos usuários veem mudanças instantaneamente.',
      },
    ],
    results: [
      { value: '12', label: 'empresas usando em produção' },
      { value: '99.9%', label: 'uptime' },
      { value: '300ms', label: 'p95 de resposta da API' },
    ],
    liveUrl: 'https://example.com',
    repoUrl: 'https://github.com/eduardosilva',
    featured: true,
  },
  {
    slug: 'brewly',
    title: 'Brewly',
    category: 'Web',
    year: 2024,
    duration: '2 meses',
    role: 'Frontend Developer',
    summary:
      'E-commerce headless de cafés especiais. Integração Shopify + Next.js, checkout customizado e sistema de assinatura.',
    cover: UNSPLASH('photo-1509042239860-f550ce710b93'),
    gallery: [
      UNSPLASH('photo-1509042239860-f550ce710b93'),
      UNSPLASH('photo-1447933601403-0c6688de566e'),
    ],
    stack: ['Next.js', 'Shopify Storefront API', 'Tailwind', 'Stripe', 'Sanity CMS'],
    challenge:
      'Migrar loja do tema padrão Shopify para uma experiência premium custom sem perder SEO nem receita.',
    approach: [
      {
        icon: 'zap',
        title: 'Lighthouse 98',
        body: 'Next.js + next/image + ISR + font optimization. Saiu de 60 para 98.',
      },
      {
        icon: 'sparkles',
        title: 'UX premium',
        body: 'Animações sutis, cart drawer custom, busca instantânea com Algolia.',
      },
    ],
    results: [
      { value: '98', label: 'Lighthouse Performance' },
      { value: '+40%', label: 'conversão em 30 dias' },
      { value: '-60%', label: 'bounce rate' },
    ],
    liveUrl: 'https://example.com',
  },
  {
    slug: 'lumen-notes',
    title: 'Lumen Notes',
    category: 'Mobile',
    year: 2024,
    duration: '4 meses',
    role: 'Solo Developer',
    summary:
      'App de notas com sincronização E2E criptografada, markdown editor e widgets para iOS/Android.',
    cover: UNSPLASH('photo-1517842645767-c639042777db'),
    gallery: [
      UNSPLASH('photo-1517842645767-c639042777db'),
      UNSPLASH('photo-1484480974693-6ca0a78fb36b'),
    ],
    stack: ['React Native', 'Expo', 'MMKV', 'Supabase', 'Reanimated 3'],
    challenge:
      'App de notas rápido como Apple Notes mas com sync criptografado end-to-end entre dispositivos.',
    approach: [
      {
        icon: 'shield',
        title: 'E2E com libsodium',
        body: 'Criptografia client-side. Servidor nunca vê conteúdo.',
      },
      {
        icon: 'zap',
        title: 'Editor nativo',
        body: 'Editor Markdown custom em TextInput nativo. Zero lag até em notas de 10k+ caracteres.',
      },
    ],
    results: [
      { value: '4.7', label: 'estrelas App Store' },
      { value: '<50ms', label: 'latência do editor' },
    ],
    repoUrl: 'https://github.com/eduardosilva',
  },
  {
    slug: 'orbit-analytics',
    title: 'Orbit Analytics',
    category: 'Web',
    year: 2023,
    duration: '5 meses',
    role: 'Senior Frontend Developer',
    summary:
      'Dashboard B2B de analytics para SaaS. Migração Vue 2 → Next.js com melhoria drástica de performance.',
    cover: UNSPLASH('photo-1551288049-bebda4e38f71'),
    gallery: [
      UNSPLASH('photo-1551288049-bebda4e38f71'),
      UNSPLASH('photo-1460925895917-afdab827c52f'),
    ],
    stack: ['Next.js', 'TypeScript', 'D3.js', 'TanStack Query', 'Tailwind'],
    challenge:
      'Dashboard legado em Vue 2 com performance ruim em datasets grandes. Cliente queria Next.js + charts mais performáticos.',
    approach: [
      {
        icon: 'zap',
        title: 'Canvas rendering',
        body: 'Charts com 100k+ pontos renderizados via canvas (não SVG). Scroll fluido.',
      },
      {
        icon: 'layers',
        title: 'Migração incremental',
        body: 'Strangler pattern: Next.js por rota, Vue coexistiu em legacy routes durante 3 meses.',
      },
    ],
    results: [
      { value: '10x', label: 'mais rápido em datasets grandes' },
      { value: '0', label: 'downtime durante migração' },
      { value: '-45%', label: 'bundle size' },
    ],
    liveUrl: 'https://example.com',
  },
];

export const localProjectsRepo: ProjectsRepo = {
  async getAll() {
    return projects;
  },
  async getBySlug(slug) {
    return projects.find((p) => p.slug === slug) ?? null;
  },
  async getFeatured(limit = 3) {
    return projects.filter((p) => p.featured).slice(0, limit);
  },
  async getNext(slug) {
    const idx = projects.findIndex((p) => p.slug === slug);
    if (idx === -1) return null;
    const next = (idx + 1) % projects.length;
    return projects[next] ?? null;
  },
};
