import type { Metadata, Viewport } from 'next';
import { cookies } from 'next/headers';
import { Inter, JetBrains_Mono } from 'next/font/google';
import Script from 'next/script';
import './globals.css';
import { LayoutShell } from '@/shared/layout/LayoutShell';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
  weight: ['400', '500', '600', '700', '800'],
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
  weight: ['400', '500'],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://eduardoalves.online'),
  title: {
    default: 'Eduardo Alves · Desenvolvedor Fullstack',
    template: '%s · Eduardo Alves',
  },
  description:
    'Desenvolvedor fullstack com foco em Flutter, FastAPI e React. Apps, APIs e produtos completos — do banco ao deploy.',
  keywords: [
    'desenvolvedor fullstack',
    'Flutter',
    'FastAPI',
    'React',
    'Next.js',
    'TypeScript',
    'Python',
    'Eduardo Alves',
    'Ariquemes',
    'Rondônia',
    'desenvolvedor Brasil',
  ],
  authors: [{ name: 'Eduardo Alves', url: 'https://eduardoalves.online' }],
  creator: 'Eduardo Alves',
  publisher: 'Eduardo Alves',
  alternates: {
    canonical: '/',
    languages: {
      'pt-BR': '/',
      'x-default': '/',
    },
    types: {
      'application/rss+xml': '/blog/rss.xml',
    },
  },
  openGraph: {
    type: 'website',
    locale: 'pt_BR',
    siteName: 'Eduardo Alves',
    url: 'https://eduardoalves.online',
    images: [{ url: '/images/og-default.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    creator: '@eduardo__8006',
    site: '@eduardo__8006',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    google: 'google-site-verification=REPLACE_ME',
    other: {
      'msvalidate.01': 'REPLACE_ME',
    },
  },
  category: 'technology',
  icons: {
    icon: '/icons/icon-192.png',
    apple: '/icons/icon-192.png',
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#05080f' },
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
  ],
  colorScheme: 'dark light',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const theme = cookieStore.get('theme')?.value || 'blue';
  const themeMode = cookieStore.get('theme-mode')?.value || 'dark';

  return (
    <html
      lang="pt-BR"
      className={`${inter.variable} ${jetbrains.variable}`}
      data-theme={theme}
      data-theme-mode={themeMode}
      suppressHydrationWarning
    >
      <body>
        <Script id="theme-init" strategy="beforeInteractive">
          {`(function(){try{var c=localStorage.getItem('theme');if(c==='blue'||c==='purple')document.documentElement.setAttribute('data-theme',c);var m=localStorage.getItem('theme-mode');if(m==='dark'||m==='light')document.documentElement.setAttribute('data-theme-mode',m);}catch(e){}})();`}
        </Script>
        <a href="#main" className="skip-link">Pular para conteúdo</a>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
