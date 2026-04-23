'use client';

import { Link2 } from 'lucide-react';
import { toast } from 'sonner';
import { LinkedinIcon, XIcon } from '@/shared/ui/BrandIcons';

export function ShareBar({ title, url }: { title: string; url: string }) {
  const twitter = `https://x.com/intent/tweet?text=${encodeURIComponent(`${title} — `)}&url=${encodeURIComponent(url)}`;
  const linkedin = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;

  const onCopy = () => {
    navigator.clipboard.writeText(url);
    toast.success('Link copiado');
  };

  return (
    <div className="mt-14 flex items-center gap-3 border-t border-white/[0.06] pt-8">
      <span className="font-mono text-[10px] tracking-[0.18em] text-[var(--text-muted)] uppercase">
        / compartilhar
      </span>
      <div className="flex items-center gap-2">
        <a
          href={twitter}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Compartilhar no X"
          className="rounded-md border border-white/10 bg-white/[0.03] p-2 text-[var(--text-secondary)] hover:text-white"
          data-cursor="link"
        >
          <XIcon width={14} height={14} />
        </a>
        <a
          href={linkedin}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Compartilhar no LinkedIn"
          className="rounded-md border border-white/10 bg-white/[0.03] p-2 text-[var(--text-secondary)] hover:text-white"
          data-cursor="link"
        >
          <LinkedinIcon width={14} height={14} />
        </a>
        <button
          onClick={onCopy}
          aria-label="Copiar link"
          className="rounded-md border border-white/10 bg-white/[0.03] p-2 text-[var(--text-secondary)] hover:text-white"
          data-cursor="link"
        >
          <Link2 size={14} />
        </button>
      </div>
    </div>
  );
}
