'use client';

import { useEffect, useState } from 'react';

interface Heading {
  id: string;
  text: string;
  level: number;
}

export function TableOfContents() {
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('.prose h2, .prose h3'));

    const timer = setTimeout(() => {
      setHeadings(
        nodes.map((node) => ({
          id: node.id,
          text: node.textContent ?? '',
          level: Number(node.tagName.slice(1)),
        })),
      );
    }, 0);

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: '-80px 0px -70% 0px' },
    );

    nodes.forEach((n) => observer.observe(n));
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  if (headings.length === 0) return null;

  return (
    <nav aria-label="Sumário" className="sticky top-24 hidden lg:block">
      <div className="mb-3 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
        / sumário
      </div>
      <ul className="space-y-1 border-l border-white/[0.08] text-sm">
        {headings.map((h) => (
          <li key={h.id}>
            <a
              href={`#${h.id}`}
              className={`block border-l-2 py-1 pl-3 transition-colors ${
                activeId === h.id
                  ? 'border-[var(--blue-500)] text-white'
                  : 'border-transparent text-[var(--text-secondary)] hover:text-white'
              } ${h.level === 3 ? 'pl-5' : ''}`}
              data-cursor="link"
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
