'use client';

import { Command } from 'cmdk';
import { AnimatePresence, motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import {
  ArrowRight,
  Mail,
  FileDown,
  Palette,
  Moon,
  Sun,
  Home,
  FolderOpen,
  BookOpen,
  User,
  Phone,
} from 'lucide-react';
import { GithubIcon, LinkedinIcon } from '@/shared/ui/BrandIcons';
import { toast } from 'sonner';
import { profile } from '@/core/config/profile';
import { localProjects } from '@/features/projects/data/projects';
import { useTheme } from '@/shared/theme/ThemeProvider';

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const featured = localProjects.filter((p) => p.featured).slice(0, 3);
  const { color, mode, setColor, setMode } = useTheme();

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const run = (fn: () => void) => {
    onClose();
    fn();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="fixed top-24 left-1/2 z-[90] w-[92%] max-w-xl -translate-x-1/2"
          >
            <Command
              label="Command Menu"
              className="overflow-hidden rounded-2xl border border-white/[0.1] bg-[var(--bg-surface)]/95 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)] backdrop-blur-2xl"
            >
              <div className="border-b border-white/[0.06] px-4 py-3">
                <Command.Input
                  placeholder="Buscar por página, projeto ou ação..."
                  className="w-full bg-transparent text-base text-white placeholder:text-[var(--text-muted)] focus:outline-none"
                />
              </div>
              <Command.List className="max-h-[420px] overflow-y-auto p-2">
                <Command.Empty className="py-10 text-center text-sm text-[var(--text-muted)]">
                  Nenhum resultado encontrado.
                </Command.Empty>

                <Command.Group heading="Navegar" className="text-xs text-[var(--text-muted)]">
                  <Item icon={<Home size={14} />} label="Home" onSelect={() => run(() => router.push('/'))} />
                  <Item icon={<FolderOpen size={14} />} label="Projetos" onSelect={() => run(() => router.push('/projetos'))} />
                  <Item icon={<BookOpen size={14} />} label="Blog" onSelect={() => run(() => router.push('/blog'))} />
                  <Item icon={<User size={14} />} label="Sobre" onSelect={() => run(() => router.push('/sobre'))} />
                  <Item icon={<Phone size={14} />} label="Contato" onSelect={() => run(() => router.push('/contato'))} />
                </Command.Group>

                <Command.Group heading="Projetos em destaque" className="text-xs text-[var(--text-muted)]">
                  {featured.map((p) => (
                    <Item
                      key={p.slug}
                      icon={<ArrowRight size={14} />}
                      label={p.title}
                      hint={p.category}
                      onSelect={() => run(() => router.push(`/projetos/${p.slug}`))}
                    />
                  ))}
                </Command.Group>

                <Command.Group heading="Ações" className="text-xs text-[var(--text-muted)]">
                  <Item
                    icon={<Mail size={14} />}
                    label="Copiar email"
                    hint={profile.email}
                    onSelect={() =>
                      run(() => {
                        navigator.clipboard.writeText(profile.email);
                        toast.success('Email copiado para a área de transferência');
                      })
                    }
                  />
                  <Item
                    icon={<GithubIcon width={14} height={14} />}
                    label="Abrir GitHub"
                    onSelect={() => run(() => window.open(profile.social.github, '_blank'))}
                  />
                  <Item
                    icon={<LinkedinIcon width={14} height={14} />}
                    label="Abrir LinkedIn"
                    onSelect={() => run(() => window.open(profile.social.linkedin, '_blank'))}
                  />
                  <Item
                    icon={<FileDown size={14} />}
                    label="Baixar CV"
                    onSelect={() =>
                      run(() => toast.info('CV será adicionado em breve (mock)'))
                    }
                  />
                  <Item
                    icon={<Moon size={14} />}
                    label={mode === 'dark' ? 'Tema: Escuro (atual)' : 'Tema: Escuro'}
                    hint="modo"
                    onSelect={() =>
                      run(() => {
                        setMode('dark');
                        toast.success('Tema escuro ativado');
                      })
                    }
                  />
                  <Item
                    icon={<Sun size={14} />}
                    label={mode === 'light' ? 'Tema: Claro (atual)' : 'Tema: Claro'}
                    hint="modo"
                    onSelect={() =>
                      run(() => {
                        setMode('light');
                        toast.success('Tema claro ativado');
                      })
                    }
                  />
                  <Item
                    icon={<Palette size={14} />}
                    label={color === 'blue' ? 'Cor: Azul (atual)' : 'Cor: Azul'}
                    hint="primário"
                    onSelect={() =>
                      run(() => {
                        setColor('blue');
                        toast.success('Cor primária alterada para azul');
                      })
                    }
                  />
                  <Item
                    icon={<Palette size={14} />}
                    label={color === 'purple' ? 'Cor: Roxo (atual)' : 'Cor: Roxo'}
                    hint="alternativo"
                    onSelect={() =>
                      run(() => {
                        setColor('purple');
                        toast.success('Cor primária alterada para roxo');
                      })
                    }
                  />
                </Command.Group>
              </Command.List>
              <div className="flex items-center justify-between border-t border-white/[0.06] px-4 py-2 font-mono text-[10px] text-[var(--text-muted)]">
                <span>↑↓ navegar · ↵ selecionar · esc fechar</span>
                <span>Command Palette</span>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function Item({
  icon,
  label,
  hint,
  onSelect,
}: {
  icon: React.ReactNode;
  label: string;
  hint?: string;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-[var(--text-primary)] transition-colors data-[selected=true]:bg-white/[0.06] data-[selected=true]:text-white"
    >
      <span className="text-[var(--blue-400)]">{icon}</span>
      <span className="flex-1">{label}</span>
      {hint && <span className="font-mono text-[10px] text-[var(--text-muted)]">{hint}</span>}
    </Command.Item>
  );
}
