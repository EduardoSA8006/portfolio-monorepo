import Image from 'next/image';
import Link from 'next/link';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const MDXComponents: Record<string, any> = {
  a: ({ href = '', children }: { href?: string; children?: React.ReactNode }) => {
    const isExternal = href.startsWith('http');
    if (isExternal) {
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    }
    return <Link href={href}>{children}</Link>;
  },
  img: (props: React.ImgHTMLAttributes<HTMLImageElement>) => (
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    <img {...props} className="rounded-lg border border-white/[0.08]" />
  ),
  Callout: ({
    type = 'info',
    children,
  }: {
    type?: 'info' | 'warning' | 'success';
    children: React.ReactNode;
  }) => {
    const tones = {
      info: 'border-[var(--blue-500)]/40 bg-[var(--blue-500)]/10 text-[var(--blue-200)]',
      warning: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
      success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
    };
    return (
      <aside className={`my-6 rounded-xl border p-4 text-sm ${tones[type]}`}>
        {children}
      </aside>
    );
  },
  NextImage: Image,
};
