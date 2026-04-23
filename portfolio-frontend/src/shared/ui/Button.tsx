'use client';

import Link from 'next/link';
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/core/utils';

type Variant = 'primary' | 'ghost' | 'outline';
type Size = 'sm' | 'md' | 'lg';

interface BaseProps {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
  className?: string;
  children: ReactNode;
}

interface ButtonAsButton extends BaseProps, Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className' | 'children'> {
  href?: never;
  external?: never;
}

interface ButtonAsLink extends BaseProps {
  href: string;
  external?: boolean;
  download?: boolean | string;
  onClick?: never;
  type?: never;
  disabled?: never;
}

type ButtonProps = ButtonAsButton | ButtonAsLink;

const variants: Record<Variant, string> = {
  primary:
    'text-white text-on-primary bg-gradient-to-br from-[var(--blue-500)] to-[var(--blue-700)] shadow-[var(--shadow-glow)] hover:brightness-110 active:brightness-95',
  ghost:
    'bg-[var(--surface-raised)] backdrop-blur-md border border-[var(--border)] text-[var(--text-primary)] hover:bg-[var(--surface-raised-hover)]',
  outline:
    'bg-transparent border border-[var(--blue-500)]/40 text-[var(--blue-400)] hover:bg-[var(--blue-500)]/10',
};

const sizes: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-md gap-1.5',
  md: 'px-5 py-2.5 text-sm rounded-lg gap-2',
  lg: 'px-6 py-3 text-base rounded-lg gap-2',
};

const base =
  'inline-flex items-center justify-center font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed select-none';

export const Button = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(
  function Button(props, ref) {
    const { variant = 'primary', size = 'md', icon, className, children } = props;
    const cls = cn(base, variants[variant], sizes[size], className);

    if ('href' in props && props.href) {
      const { external, href, download } = props;
      if (external || download) {
        return (
          <a
            ref={ref as React.Ref<HTMLAnchorElement>}
            href={href}
            target={external ? '_blank' : undefined}
            rel={external ? 'noopener noreferrer' : undefined}
            download={download}
            className={cls}
            data-cursor="link"
          >
            {icon}
            {children}
          </a>
        );
      }
      return (
        <Link
          ref={ref as React.Ref<HTMLAnchorElement>}
          href={href}
          className={cls}
          data-cursor="link"
        >
          {icon}
          {children}
        </Link>
      );
    }

    const { onClick, type = 'button', disabled } = props;
    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        type={type}
        onClick={onClick}
        disabled={disabled}
        className={cls}
        data-cursor="link"
      >
        {icon}
        {children}
      </button>
    );
  },
);
