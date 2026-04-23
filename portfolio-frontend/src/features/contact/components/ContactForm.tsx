'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Send } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/core/utils';
import { contactSchema, type ContactInput } from '@/features/contact/lib/validation';

export function ContactForm() {
  const [submitting, setSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ContactInput>({ resolver: zodResolver(contactSchema) });

  const onSubmit = async (data: ContactInput) => {
    setSubmitting(true);
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error('failed');
      toast.success('Mensagem enviada! (mock) Retorno em até 24h.');
      reset();
    } catch {
      toast.error('Falha ao enviar. Tente novamente.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="grid gap-5 md:grid-cols-2">
        <Field label="Nome" error={errors.name?.message}>
          <input
            {...register('name')}
            type="text"
            placeholder="Seu nome completo"
            className={inputCls(!!errors.name)}
            autoComplete="name"
          />
        </Field>
        <Field label="Email" error={errors.email?.message}>
          <input
            {...register('email')}
            type="email"
            placeholder="seu@email.com"
            className={inputCls(!!errors.email)}
            autoComplete="email"
          />
        </Field>
      </div>
      <Field label="Assunto" error={errors.subject?.message}>
        <input
          {...register('subject')}
          type="text"
          placeholder="Sobre o que você quer conversar?"
          className={inputCls(!!errors.subject)}
        />
      </Field>
      <Field label="Mensagem" error={errors.message?.message}>
        <textarea
          {...register('message')}
          rows={6}
          placeholder="Conta sobre seu projeto, prazos, orçamento..."
          className={inputCls(!!errors.message)}
        />
      </Field>

      <button
        type="submit"
        disabled={submitting}
        data-cursor="link"
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-medium text-white text-on-primary transition-all disabled:opacity-50"
        style={{
          background: 'var(--gradient-btn)',
          boxShadow: 'var(--shadow-glow)',
        }}
      >
        {submitting ? 'Enviando…' : (
          <>
            <Send size={16} />
            Enviar mensagem
          </>
        )}
      </button>
    </form>
  );
}

function Field({
  label,
  children,
  error,
}: {
  label: string;
  children: React.ReactNode;
  error?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block font-mono text-[10px] tracking-[0.18em] text-[var(--blue-400)] uppercase">
        {label}
      </label>
      {children}
      {error && <p className="mt-1.5 text-xs text-rose-300">{error}</p>}
    </div>
  );
}

function inputCls(hasError: boolean) {
  return cn(
    'w-full rounded-lg border bg-[var(--surface-raised)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] transition-colors focus:outline-none',
    hasError
      ? 'border-rose-500/40 focus:border-rose-500/60'
      : 'border-white/10 focus:border-[var(--blue-500)]/50',
  );
}
