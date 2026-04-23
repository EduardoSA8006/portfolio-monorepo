import Image from 'next/image';
import { cn } from '@/core/utils';

export function MobileMockup({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'relative mx-auto aspect-[9/19] w-[240px] overflow-hidden rounded-[36px] border-[10px] border-[#12131a] bg-black shadow-[0_30px_60px_-20px_rgba(0,0,0,0.8)]',
        className,
      )}
    >
      <div
        aria-hidden
        className="absolute top-2 left-1/2 z-10 h-5 w-24 -translate-x-1/2 rounded-full bg-[#12131a]"
      />
      <Image src={src} alt={alt} fill sizes="240px" className="object-cover" />
    </div>
  );
}
