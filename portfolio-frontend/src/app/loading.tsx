import { Container } from '@/shared/ui/Container';

export default function Loading() {
  return (
    <section className="py-24 md:py-32">
      <Container>
        <div className="animate-pulse space-y-6">
          <div className="h-4 w-24 rounded bg-white/[0.06]" />
          <div className="h-12 w-3/4 rounded bg-white/[0.08]" />
          <div className="h-5 w-1/2 rounded bg-white/[0.04]" />
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-64 rounded-xl bg-white/[0.04]" />
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
