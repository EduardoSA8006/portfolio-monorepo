import type { ComponentType, SVGProps } from 'react';
import { Network, Shield, Terminal, Cpu } from 'lucide-react';
import {
  SiDart,
  SiPython,
  SiJavascript,
  SiCplusplus,
  SiSharp,
  SiLua,
  SiFlutter,
  SiReact,
  SiVuedotjs,
  SiFastapi,
  SiPostgresql,
  SiRedis,
  SiFirebase,
  SiGit,
  SiLinux,
  SiDocker,
} from 'react-icons/si';
import { FaJava } from 'react-icons/fa';

type IconRenderer = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>;

const MAP: Record<string, IconRenderer> = {
  // Linguagens
  dart: SiDart,
  python: SiPython,
  javascript: SiJavascript,
  java: FaJava,
  cpp: SiCplusplus,
  csharp: SiSharp,
  lua: SiLua,

  // Frameworks
  flutter: SiFlutter,
  react: SiReact,
  vue: SiVuedotjs,
  fastapi: SiFastapi,

  // Backend & Infra
  postgresql: SiPostgresql,
  redis: SiRedis,
  firebase: SiFirebase,
  jwt: Shield,
  rest: Network,

  // Ferramentas
  git: SiGit,
  linux: SiLinux,
  docker: SiDocker,
  terminal: Terminal,
  esp32: Cpu,
};

export function TechIcon({
  name,
  size = 36,
  className,
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  const Icon = MAP[name];
  if (!Icon) return null;
  return <Icon size={size} className={className} aria-hidden />;
}

export function hasTechIcon(name: string): boolean {
  return name in MAP;
}
