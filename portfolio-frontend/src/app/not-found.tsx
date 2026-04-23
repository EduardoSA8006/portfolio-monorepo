import { Container } from '@/shared/ui/Container';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { GradientText } from '@/shared/effects/GradientText';
import { Button } from '@/shared/ui/Button';

export default function NotFound() {
  return (
    <section className="relative flex min-h-[70vh] items-center overflow-hidden py-24">
      <AuroraBg />
      <GridBg />
      <Container>
        <div className="text-center">
          <div className="font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
            / 404
          </div>
          <h1 className="mt-4 text-6xl font-semibold tracking-[-0.03em] text-white md:text-8xl">
            <GradientText>Rota não encontrada.</GradientText>
          </h1>
          <p className="mx-auto mt-5 max-w-lg text-[var(--text-secondary)]">
            A página que você procura não existe ou foi movida. Pode ser um typo no link ou ela simplesmente não tem mais casa.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button href="/">Voltar para home</Button>
            <Button href="/projetos" variant="ghost">
              Ver projetos
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
