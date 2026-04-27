"use client";

import dynamic from "next/dynamic";
import { forwardRef, type Ref } from "react";

const HCaptcha = dynamic(() => import("@hcaptcha/react-hcaptcha"), { ssr: false });

type Props = {
  siteKey: string;
  onVerify: (token: string) => void;
  onExpire?: () => void;
};

export const HCaptchaWidget = forwardRef(function HCaptchaWidget(
  { siteKey, onVerify, onExpire }: Props,
  ref: Ref<unknown>,
) {
  if (!siteKey) {
    return (
      <div className="rounded border border-dashed border-neutral-700 px-3 py-2 text-xs text-neutral-500">
        hCaptcha disabled (dev mode) —{" "}
        <button type="button" className="underline" onClick={() => onVerify("dev-bypass-token")}>
          simulate verify
        </button>
      </div>
    );
  }
  return (
    <HCaptcha
      // @ts-expect-error — dynamic() typings do not forward ref generic
      ref={ref}
      sitekey={siteKey}
      onVerify={onVerify}
      onExpire={onExpire}
    />
  );
});
