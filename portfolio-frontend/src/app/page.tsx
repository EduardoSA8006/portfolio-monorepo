import { Hero } from '@/features/home/components/Hero';
import { AboutPreview } from '@/features/home/components/AboutPreview';
import { StackSection } from '@/features/home/components/StackSection';
import { ProjectsPreview } from '@/features/home/components/ProjectsPreview';
import { GithubStats } from '@/features/home/components/GithubStats';
import { TestimonialsSection } from '@/features/home/components/TestimonialsSection';
import { BlogPreview } from '@/features/home/components/BlogPreview';
import { ContactPreview } from '@/features/home/components/ContactPreview';
import { JsonLd } from '@/shared/seo/JsonLd';
import { personJsonLd } from '@/core/utils/seo';

export default function HomePage() {
  return (
    <>
      <JsonLd data={personJsonLd()} />
      <Hero />
      <AboutPreview />
      <StackSection />
      <ProjectsPreview />
      <GithubStats />
      <TestimonialsSection />
      <BlogPreview />
      <ContactPreview />
    </>
  );
}
