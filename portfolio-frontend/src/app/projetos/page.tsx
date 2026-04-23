import type { Metadata } from 'next';
import { Container } from '@/shared/ui/Container';
import { SectionHeader } from '@/shared/ui/SectionHeader';
import { AuroraBg } from '@/shared/ui/AuroraBg';
import { GridBg } from '@/shared/ui/GridBg';
import { getAllProjects } from '@/features/projects/data/projects';
import { ProjectsClient } from '@/features/projects/components/ProjectsClient';

export const metadata: Metadata = {
  title: 'Projetos',
  description:
    'Seleção de trabalhos recentes — web, mobile e fullstack. Fintech, e-commerce, produtividade e mais.',
  alternates: { canonical: '/projetos' },
};

export default async function ProjectsPage() {
  const projects = await getAllProjects();
  return (
    <section className="relative overflow-hidden py-24 md:py-32">
      <AuroraBg intensity="subtle" />
      <GridBg />
      <Container>
        <SectionHeader
          eyebrow="/ TRABALHO"
          title="Projetos."
          description={`Seleção de ${projects.length} projetos recentes em web, mobile e fullstack. Filtre por categoria ou busque por stack.`}
        />
        <ProjectsClient projects={projects} />
      </Container>
    </section>
  );
}
