"use client";

import { useCallback, useState } from "react";

import { AuthApiError, login } from "./api";
import type { AuthErrorCode } from "./types";

export type LoginState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string; code: AuthErrorCode | string }
  | { kind: "mfa_required"; challengeToken: string }
  | { kind: "success"; csrfToken: string };

const ERROR_MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: "E-mail ou senha inválidos.",
  AUTH_CAPTCHA_REQUIRED: "Resolva o captcha para continuar.",
  AUTH_CAPTCHA_INVALID: "Verificação do captcha falhou. Tente novamente.",
  AUTH_TOO_MANY_ATTEMPTS:
    "Muitas tentativas. Tente novamente em alguns minutos.",
};

export function useLogin() {
  const [state, setState] = useState<LoginState>({ kind: "idle" });

  const submit = useCallback(
    async (args: {
      email: string;
      password: string;
      captchaToken?: string | null;
    }) => {
      setState({ kind: "submitting" });
      try {
        const result = await login({
          email: args.email,
          password: args.password,
          captcha_token: args.captchaToken ?? null,
        });
        if (result.status === "mfa_required") {
          setState({
            kind: "mfa_required",
            challengeToken: result.mfa_challenge_token,
          });
          return;
        }
        setState({ kind: "success", csrfToken: result.csrf_token });
      } catch (err) {
        if (err instanceof AuthApiError) {
          const code = err.payload.error;
          setState({
            kind: "error",
            code,
            message:
              ERROR_MESSAGES[code] ?? err.payload.detail ?? "Erro de autenticação.",
          });
          return;
        }
        setState({
          kind: "error",
          code: "NETWORK",
          message: "Algo deu errado. Tente novamente.",
        });
      }
    },
    [],
  );

  const reset = useCallback(() => setState({ kind: "idle" }), []);

  return { state, submit, reset };
}

export function shouldShowCaptcha(state: LoginState): boolean {
  if (state.kind !== "error") return false;
  return state.code !== "AUTH_TOO_MANY_ATTEMPTS";
}
