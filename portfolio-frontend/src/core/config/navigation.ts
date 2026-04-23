export const navLinks = [
  { href: '/', label: 'Início' },
  { href: '/projetos', label: 'Projetos' },
  { href: '/blog', label: 'Blog' },
  { href: '/sobre', label: 'Sobre' },
  { href: '/contato', label: 'Contato' },
] as const;

export const footerLinks = {
  nav: [
    { href: '/', label: 'Home' },
    { href: '/projetos', label: 'Projetos' },
    { href: '/blog', label: 'Blog' },
    { href: '/sobre', label: 'Sobre' },
    { href: '/contato', label: 'Contato' },
  ],
  social: [
    { href: 'https://github.com/EduardoSA8006', label: 'GitHub', external: true },
    { href: 'https://www.linkedin.com/in/eduardo8006', label: 'LinkedIn', external: true },
    { href: 'https://www.instagram.com/eduardo__8006', label: 'Instagram', external: true },
  ],
  legal: [
    { href: '/privacidade', label: 'Privacidade' },
    { href: '/termos', label: 'Termos' },
  ],
} as const;
