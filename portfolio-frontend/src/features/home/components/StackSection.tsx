'use client';

import { useState } from 'react';
import { Code2, Boxes, Database, Wrench } from 'lucide-react';
import { cn } from '@/core/utils';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { TechIcon } from '@/features/stack/components/TechIcon';
import { stack } from '@/features/stack/data/stack';
import type { StackCategory, StackItem } from '@/core/domain/stack';

type TabKey = StackCategory;

const TABS: { key: TabKey; label: string; Icon: typeof Code2 }[] = [
  { key: 'Linguagens', label: 'Linguagens', Icon: Code2 },
  { key: 'Frameworks', label: 'Frameworks', Icon: Boxes },
  { key: 'Backend & Infra', label: 'Backend & Infra', Icon: Database },
  { key: 'Ferramentas', label: 'Ferramentas', Icon: Wrench },
];

export function StackSection() {
  const [active, setActive] = useState<TabKey>('Linguagens');
  const filtered = stack.filter((s) => s.category === active);

  return (
    <section id="stack" className="relative py-24 md:py-32">
      <Container>
        <SectionHeader
          eyebrow="/ STACK"
          title="Ferramentas que uso."
          description="Trabalho com o que entrega melhor resultado para cada contexto — não com o que está na moda."
          align="center"
          className="mx-auto text-center"
        />

        <div className="mb-10 flex flex-wrap justify-center gap-2 md:gap-3">
          {TABS.map((tab) => {
            const isActive = active === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActive(tab.key)}
                data-cursor="link"
                aria-pressed={isActive}
                className={cn(
                  'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors duration-200',
                  isActive
                    ? 'text-white text-on-primary shadow-[0_10px_30px_-10px_rgba(59,130,246,0.55)]'
                    : 'border border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]',
                )}
                style={isActive ? { background: 'var(--gradient-btn)' } : undefined}
              >
                <tab.Icon size={14} className={isActive ? 'text-white text-on-primary' : 'text-[var(--blue-400)]'} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div
          key={active}
          className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
        >
          {filtered.map((item) => (
            <StackCard key={item.name} item={item} />
          ))}
        </div>
      </Container>
    </section>
  );
}

function StackCard({ item }: { item: StackItem }) {
  const percent = (item.level / 5) * 100;

  return (
    <div className="group relative flex flex-col rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 transition-colors duration-200 hover:border-[var(--blue-500)]/30 hover:bg-white/[0.04]">
      <div
        aria-hidden
        className="absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        style={{
          background:
            'radial-gradient(circle at 50% 0%, rgba(59,130,246,0.12), transparent 70%)',
        }}
      />

      <div className="relative flex flex-1 flex-col items-center text-center">
        <div className="mb-4 flex h-10 w-10 items-center justify-center text-[var(--blue-400)]">
          <TechIcon name={item.icon} size={36} />
        </div>
        <div className="text-sm font-semibold text-[var(--text-primary)]">{item.name}</div>
      </div>

      <div className="relative mt-5 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full"
          style={{ width: `${percent}%`, background: 'var(--gradient-btn)' }}
        />
      </div>
    </div>
  );
}
