import { Star, GitPullRequest, GitCommit, Flame } from 'lucide-react';
import { cn } from '@/core/utils';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { GlassCard } from '@/shared/ui/GlassCard';
import { ScrollReveal } from '@/shared/effects/ScrollReveal';
import { github } from '@/features/home/data/github';

function contribColor(level: number) {
  const palette = [
    'bg-white/[0.04]',
    'bg-[var(--blue-500)]/20',
    'bg-[var(--blue-500)]/45',
    'bg-[var(--blue-500)]/70',
    'bg-[var(--blue-400)]',
  ];
  return palette[level] ?? palette[0];
}

export function GithubStats() {
  return (
    <section id="github" className="relative py-24 md:py-32">
      <Container>
        <SectionHeader
          eyebrow="/ ATIVIDADE"
          title="Código em produção contínua."
          description="Atividade pública no GitHub. Dados do último ano, atualizados automaticamente."
          align="center"
          className="mx-auto text-center"
        />

        <div className="grid gap-6 md:grid-cols-[2fr_1fr]">
          <ScrollReveal>
            <GlassCard>
              <div className="mb-4 flex items-center justify-between">
                <span className="font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
                  {'// último ano'}
                </span>
                <span className="font-mono text-[10px] text-[var(--text-muted)]">
                  {github.contributions.reduce((a, b) => a + b, 0)} contribs
                </span>
              </div>
              <div
                className="grid gap-[3px]"
                style={{ gridTemplateColumns: 'repeat(52, minmax(0, 1fr))' }}
              >
                {github.contributions.map((lvl, i) => (
                  <span
                    key={i}
                    className={cn('aspect-square rounded-[2px]', contribColor(lvl))}
                    aria-hidden
                  />
                ))}
              </div>
              <div className="mt-4 flex items-center justify-end gap-2 font-mono text-[10px] text-[var(--text-muted)]">
                menos
                <span className={cn('inline-block h-2.5 w-2.5 rounded-[2px]', contribColor(0))} />
                <span className={cn('inline-block h-2.5 w-2.5 rounded-[2px]', contribColor(1))} />
                <span className={cn('inline-block h-2.5 w-2.5 rounded-[2px]', contribColor(2))} />
                <span className={cn('inline-block h-2.5 w-2.5 rounded-[2px]', contribColor(3))} />
                <span className={cn('inline-block h-2.5 w-2.5 rounded-[2px]', contribColor(4))} />
                mais
              </div>
            </GlassCard>
          </ScrollReveal>

          <ScrollReveal delay={0.08}>
            <div className="grid grid-cols-2 gap-3">
              <StatCard icon={<GitCommit size={14} />} value={github.stats.commitsYear} label="commits" />
              <StatCard icon={<GitPullRequest size={14} />} value={github.stats.pullRequests} label="PRs" />
              <StatCard icon={<Star size={14} />} value={github.stats.stars} label="stars" />
              <StatCard icon={<Flame size={14} />} value={`${github.stats.streak}d`} label="streak" />
            </div>
          </ScrollReveal>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {github.topRepos.map((repo, i) => (
            <ScrollReveal key={repo.name} delay={i * 0.05}>
              <GlassCard hover className="h-full">
                <div className="flex items-center gap-2 font-mono text-xs font-medium text-white">
                  <span className="h-2 w-2 rounded-full" style={{ background: repo.languageColor }} />
                  {repo.name}
                </div>
                <p className="mt-3 text-sm text-[var(--text-secondary)]">{repo.description}</p>
                <div className="mt-4 flex items-center gap-4 font-mono text-[10px] text-[var(--text-muted)]">
                  <span className="inline-flex items-center gap-1">
                    <Star size={10} /> {repo.stars}
                  </span>
                  <span>{repo.language}</span>
                </div>
              </GlassCard>
            </ScrollReveal>
          ))}
        </div>
      </Container>
    </section>
  );
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
}) {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[var(--bg-glass)] p-4 backdrop-blur-[8px]">
      <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.15em] text-[var(--blue-400)] uppercase">
        {icon}
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">{value}</div>
    </div>
  );
}
