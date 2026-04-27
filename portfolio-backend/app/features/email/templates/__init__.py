"""
Email templates — Jinja2-rendered, one template pair per event.

Public API (kept stable across the f-string → Jinja2 migration):

  * EmailContent — dataclass returned by every render.
  * TEMPLATES    — id → (subject_fn, html_template, text_template) registry,
                   used by the Celery task to materialize a render from a
                   JSON payload (template_id + context dict).
  * render(template_id, context) → EmailContent

  * Convenience wrappers used by the service layer (and in tests):
    - two_factor_code, login_notification, admin_recovery_notice
    - security_event(event_type=..., ...) — picks the per-event template
      from `security/<event_type>.{html,txt}.j2`, falling back to
      `security/_generic.*` for an unknown event type.

Why Jinja2 instead of f-strings: HTML emails want inheritance (a shared
header/footer/macro library) and proper auto-escaping. Plain f-strings
encourage hand-built HTML strings that cannot reuse layout and forget
to escape user-supplied IPs / user-agents in the body. The `.txt.j2`
twin keeps the multipart/alternative path lossless for clients that
strip HTML.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    select_autoescape,
)

_TEMPLATE_DIR = Path(__file__).parent

# Two environments:
#   - HTML: autoescape on so an attacker-supplied user-agent cannot
#     inject markup into the alert body.
#   - Text: autoescape OFF (plain text doesn't need it, and "&amp;"
#     instead of "&" in a security alert reads as a bug).
_html_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html.j2",), default_for_string=False),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)
_text_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # noqa: S701 — plain text body, escaping &/< is wrong
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text_body: str
    html_body: str | None = None


# ───────────────────────────────────────────────────────────────────────────
# Severity classification — drives the header color in the HTML template.
# ───────────────────────────────────────────────────────────────────────────
#
# `info`     — neutral slate header. Transactional notices (codes, login
#              confirmations).
# `warning`  — amber header. Suspicious-but-not-conclusive (failed MFA,
#              session sweeps).
# `critical` — red header. Forgery / lockout / second-factor disabled /
#              full admin reset.

_SEVERITY_BY_EVENT = {
    "cookie_signature_invalid": "critical",
    "login_lockout_triggered": "critical",
    "totp_disabled": "critical",
    "email_2fa_disabled": "critical",
    "admin_recovery": "critical",
    "login_mfa_failed": "warning",
    "login_email_code_failed": "warning",
    "totp_disable_failed": "warning",
    "totp_confirm_failed": "warning",
    "email_2fa_disable_failed": "warning",
    "sessions_cleared": "warning",
}


def severity_for(event_type: str) -> str:
    return _SEVERITY_BY_EVENT.get(event_type, "warning")


def _isoformat_utc(dt: datetime | str | None) -> str:
    """Normalize whatever the caller passed (datetime, ISO string, None) to a
    human-friendly UTC string. Templates render `when_str` directly."""
    if dt is None:
        dt = datetime.now(UTC)
    elif isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _render_pair(
    *,
    html_template: str,
    text_template: str,
    context: dict,
) -> tuple[str, str]:
    text = _text_env.get_template(text_template).render(**context)
    html = _html_env.get_template(html_template).render(**context)
    return text, html


# ───────────────────────────────────────────────────────────────────────────
# Convenience wrappers (transactional)
# ───────────────────────────────────────────────────────────────────────────


def two_factor_code(*, name: str, code: str, ttl_minutes: int) -> EmailContent:
    subject = f"[Portfolio] Code {code} - expires in {ttl_minutes} min"
    ctx = {"name": name, "code": code, "ttl_minutes": ttl_minutes}
    text, html = _render_pair(
        html_template="two_factor_code.html.j2",
        text_template="two_factor_code.txt.j2",
        context=ctx,
    )
    return EmailContent(subject=subject, text_body=text, html_body=html)


def login_notification(
    *,
    name: str,
    ip: str,
    user_agent: str | None,
    when: datetime | str | None = None,
) -> EmailContent:
    subject = "[Portfolio] New sign-in to your admin account"
    ctx = {
        "name": name,
        "ip": ip,
        "user_agent": user_agent,
        "when_str": _isoformat_utc(when),
    }
    text, html = _render_pair(
        html_template="login_notification.html.j2",
        text_template="login_notification.txt.j2",
        context=ctx,
    )
    return EmailContent(subject=subject, text_body=text, html_body=html)


def admin_recovery_notice(
    *, name: str, ip: str | None, when: datetime | str | None = None
) -> EmailContent:
    subject = "[Portfolio][SECURITY] Admin password + TOTP were reset"
    ctx = {
        "name": name,
        "ip": ip or "(local console)",
        "when_str": _isoformat_utc(when),
    }
    text, html = _render_pair(
        html_template="admin_recovery_notice.html.j2",
        text_template="admin_recovery_notice.txt.j2",
        context=ctx,
    )
    return EmailContent(subject=subject, text_body=text, html_body=html)


# ───────────────────────────────────────────────────────────────────────────
# Convenience wrappers (per-security-event)
# ───────────────────────────────────────────────────────────────────────────

# Set populated below from the templates that exist on disk. Service /
# Celery use this to fall back gracefully when a new event_type lands
# in audit before its template is added.
_KNOWN_SECURITY_EVENTS: frozenset[str] = frozenset(
    {
        "cookie_signature_invalid",
        "login_lockout_triggered",
        "login_mfa_failed",
        "login_email_code_failed",
        "totp_disabled",
        "totp_disable_failed",
        "totp_confirm_failed",
        "email_2fa_disabled",
        "email_2fa_disable_failed",
        "sessions_cleared",
        "admin_recovery",
    }
)


def _security_template_id(event_type: str) -> str:
    """Return the template_id used by the registry for an event."""
    if event_type in _KNOWN_SECURITY_EVENTS:
        return f"security/{event_type}"
    return "security/_generic"


def security_event(
    *,
    event_type: str,
    ip: str | None = None,
    user_agent: str | None = None,
    when: datetime | str | None = None,
    extra: str | None = None,
) -> EmailContent:
    """Render the per-event security email. Falls back to a generic
    template when `event_type` has no dedicated file yet — so an audit
    fan-out for a brand-new event still produces a useful message."""
    severity = severity_for(event_type)
    is_known = event_type in _KNOWN_SECURITY_EVENTS
    ctx = {
        "event_type": event_type,
        "ip": ip,
        "user_agent": user_agent,
        "when_str": _isoformat_utc(when),
        "extra": extra,
        "severity": severity,
    }
    subject_prefix = "[Portfolio][SECURITY]"
    subject = f"{subject_prefix} {event_type}"

    if is_known:
        html_template = f"security/{event_type}.html.j2"
        text_template = f"security/{event_type}.txt.j2"
    else:
        html_template = "security/_generic.html.j2"
        text_template = "security/_generic.txt.j2"

    text, html = _render_pair(
        html_template=html_template,
        text_template=text_template,
        context=ctx,
    )
    return EmailContent(subject=subject, text_body=text, html_body=html)


# Back-compat alias — older call sites pass `security_alert(...)`. The
# Celery task only addresses templates by id (TEMPLATES dict below); the
# Python alias is for the test surface and any direct caller.
security_alert = security_event


# ───────────────────────────────────────────────────────────────────────────
# Template registry consumed by the Celery task.
#
# Each entry is `template_id → render callable`. The callable accepts
# **context (a JSON dict from the broker) and returns EmailContent.
# Wrapping the wrappers above ensures the Celery worker uses the same
# subject builders + ctx normalization as direct callers.
# ───────────────────────────────────────────────────────────────────────────

def _wrap_security(event_type: str) -> Callable[..., EmailContent]:
    def _render(**ctx) -> EmailContent:
        # Force the event_type so a misaligned id can't render a wrong
        # body for the right id (defense in depth).
        return security_event(**{**ctx, "event_type": event_type})
    return _render


def _wrap_security_generic() -> Callable[..., EmailContent]:
    def _render(**ctx) -> EmailContent:
        return security_event(**ctx)
    return _render


TEMPLATES: dict[str, Callable[..., EmailContent]] = {
    "two_factor_code": two_factor_code,
    "login_notification": login_notification,
    "admin_recovery_notice": admin_recovery_notice,
    "security/_generic": _wrap_security_generic(),
}
for _ev in _KNOWN_SECURITY_EVENTS:
    TEMPLATES[f"security/{_ev}"] = _wrap_security(_ev)


def render(template_id: str, context: dict) -> EmailContent:
    if template_id not in TEMPLATES:
        raise KeyError(f"unknown email template: {template_id!r}")
    return TEMPLATES[template_id](**context)


__all__ = [
    "TEMPLATES",
    "EmailContent",
    "admin_recovery_notice",
    "login_notification",
    "render",
    "security_alert",
    "security_event",
    "severity_for",
    "two_factor_code",
]
