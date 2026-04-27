export type LoginSuccess = {
  status: "ok";
  csrf_token: string;
  message?: string;
};

export type LoginMfaRequired = {
  status: "mfa_required";
  mfa_challenge_token: string;
  message?: string;
};

export type LoginResponse = LoginSuccess | LoginMfaRequired;

export type AuthErrorCode =
  | "AUTH_INVALID_CREDENTIALS"
  | "AUTH_CAPTCHA_REQUIRED"
  | "AUTH_CAPTCHA_INVALID"
  | "AUTH_TOO_MANY_ATTEMPTS"
  | "AUTH_MFA_CHALLENGE_INVALID"
  | "AUTH_TOTP_INVALID";

export type AuthErrorPayload = {
  error: AuthErrorCode | string;
  detail: string;
};

export type AuthConfig = {
  hcaptcha_site_key: string;
};
