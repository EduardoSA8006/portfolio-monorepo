import Image from 'next/image';
import { Container } from '@/shared/ui/Container';

export function CaseStudyGallery({
  images,
  isMobile = false,
}: {
  images: string[];
  isMobile?: boolean;
}) {
  if (images.length === 0) return null;

  return (
    <section className="py-16 md:py-20">
      <Container>
        <div className="mb-10 font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
          / galeria
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {images.map((src, i) => (
            <div
              key={src + i}
              className={
                isMobile
                  ? 'flex items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.02] p-8'
                  : 'relative aspect-[16/10] overflow-hidden rounded-xl border border-white/[0.08]'
              }
            >
              {isMobile ? (
                <div className="relative mx-auto aspect-[9/19] w-[240px] overflow-hidden rounded-[36px] border-[10px] border-[#12131a] bg-black shadow-[0_30px_60px_-20px_rgba(0,0,0,0.8)]">
                  <div
                    aria-hidden
                    className="absolute top-2 left-1/2 z-10 h-5 w-24 -translate-x-1/2 rounded-full bg-[#12131a]"
                  />
                  <Image src={src} alt={`Mockup ${i + 1}`} fill sizes="240px" className="object-cover" />
                </div>
              ) : (
                <Image
                  src={src}
                  alt={`Imagem ${i + 1}`}
                  fill
                  sizes="(max-width: 768px) 100vw, 50vw"
                  className="object-cover"
                />
              )}
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
