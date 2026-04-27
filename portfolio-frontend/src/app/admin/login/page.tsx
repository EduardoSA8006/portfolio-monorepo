"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchAuthConfig } from "@/features/admin/auth/api";
import { HCaptchaWidget } from "@/features/admin/auth/hcaptcha-widget";
import { shouldShowCaptcha, useLogin } from "@/features/admin/auth/use-login";

export default function AdminLoginPage() {
  const router = useRouter();
  const { state, submit } = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [siteKey, setSiteKey] = useState<string>("");

  useEffect(() => {
    fetchAuthConfig()
      .then((cfg) => setSiteKey(cfg.hcaptcha_site_key))
      .catch(() => setSiteKey(""));
  }, []);

  useEffect(() => {
    if (state.kind === "success") {
      router.replace("/admin");
    }
  }, [state, router]);

  // Reset the captcha token after each submit attempt — hCaptcha tokens are
  // single-use, so a failed submit must force a fresh challenge.
  useEffect(() => {
    if (state.kind === "error") setCaptchaToken(null);
  }, [state]);

  const captchaRequired = shouldShowCaptcha(state);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">Admin login</h1>
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          submit({ email, password, captchaToken });
        }}
      >
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
        </label>

        {captchaRequired && (
          <HCaptchaWidget
            siteKey={siteKey}
            onVerify={(token) => setCaptchaToken(token)}
            onExpire={() => setCaptchaToken(null)}
          />
        )}

        {state.kind === "error" && (
          <p className="text-sm text-red-400" role="alert">
            {state.message}
          </p>
        )}

        <button
          type="submit"
          disabled={state.kind === "submitting" || (captchaRequired && !captchaToken)}
          className="rounded bg-neutral-100 px-4 py-2 text-neutral-900 disabled:opacity-50"
        >
          {state.kind === "submitting" ? "Entrando..." : "Entrar"}
        </button>

        {state.kind === "mfa_required" && (
          <p className="text-sm text-amber-400">
            MFA required. (UI for TOTP challenge not yet implemented.)
          </p>
        )}
      </form>
    </main>
  );
}
