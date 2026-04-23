'use client';

import { useEffect } from 'react';
import { Button } from '@/shared/ui/Button';
import { Container } from '@/shared/ui/Container';
import { AuroraBg } from '@/shared/ui/AuroraBg';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <section className="relative flex min-h-[70vh] items-center overflow-hidden py-24">
      <AuroraBg intensity="subtle" />
      <Container>
        <div className="mx-auto max-w-xl text-center">
          <div className="font-mono text-[11px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
            / erro inesperado
          </div>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.03em] text-white md:text-5xl">
            Algo quebrou por aqui.
          </h1>
          <p className="mt-4 text-[var(--text-secondary)]">
            Já foi registrado automaticamente. Tente recarregar ou volte para a home.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Button onClick={() => reset()}>Tentar novamente</Button>
            <Button href="/" variant="ghost">
              Voltar à home
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
