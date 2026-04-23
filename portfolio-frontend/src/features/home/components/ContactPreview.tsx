import { ArrowRight } from 'lucide-react';
import { Container } from '@/shared/ui/Container';
import { GlassCard } from '@/shared/ui/GlassCard';
import { Button } from '@/shared/ui/Button';
import { GradientText } from '@/shared/effects/GradientText';
import { ScrollReveal } from '@/shared/effects/ScrollReveal';
import { FaProjectDiagram } from 'react-icons/fa';

export function ContactPreview() {
  return (
    <section id="contato" className="relative py-24 md:py-32">
      <Container>
        <ScrollReveal>
          <GlassCard className="mx-auto max-w-3xl text-center">
            <div className="font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
              / VAMOS CONVERSAR
            </div>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-white md:text-5xl">
              Tem um projeto em mente?
              <br />
              <GradientText>Vamos construir juntos.</GradientText>
            </h2>
            <p className="mx-auto mt-5 max-w-lg text-base text-[var(--text-secondary)]">
              Projetos freela, consultoria e contratos. Respondo em até 24 horas úteis.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button href="/contato" icon={<ArrowRight size={16} />} size="lg">
                Ir ao contato
              </Button>
              <Button
                href={`/projetos`}
                variant="ghost"
                size="lg"
                icon={<FaProjectDiagram size={16} />}
              >
                Projetos
              </Button>
            </div>
          </GlassCard>
        </ScrollReveal>
      </Container>
    </section>
  );
}
