import html
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("veilproof.email")

RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
EMAIL_FROM = (os.getenv("EMAIL_FROM") or "VeilProof <noreply@mail.veilproof.tech>").strip()
EMAIL_REPLY_TO = (os.getenv("EMAIL_REPLY_TO") or "").strip()
DASHBOARD_URL = (os.getenv("DASHBOARD_URL") or "https://veilproof.tech/dashboard").rstrip("/")
DOCS_URL = (os.getenv("DOCS_URL") or "https://veilproof.tech/docs").rstrip("/")
SUPPORT_URL = (os.getenv("SUPPORT_URL") or "https://veilproof.tech/docs").rstrip("/")
SITE_URL = (os.getenv("SITE_URL") or "https://veilproof.tech").rstrip("/")
LOGO_URL = (os.getenv("EMAIL_LOGO_URL") or f"{SITE_URL}/veilproof-logo.png").strip()
SUPPORT_EMAIL = (os.getenv("SUPPORT_EMAIL") or "support@veilproof.tech").strip()
BRAND = "VeilProof"
ACCENT = "#f6821f"
INK = "#0a0c12"
MUTED = "#6b7280"
YEAR = datetime.now(timezone.utc).year


def email_enabled() -> bool:
    return bool(RESEND_API_KEY)


def _esc(value: Optional[str]) -> str:
    return html.escape(str(value or ""), quote=True)


def _display_name(full_name: Optional[str], email: str) -> str:
    name = (full_name or "").strip()
    if name:
        return name.split()[0]
    local = (email or "").split("@", 1)[0].strip()
    return local or "there"


def _greeting_name(full_name: Optional[str], email: str) -> str:
    name = (full_name or "").strip()
    if name:
        return name
    return _display_name(None, email)


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def _font_stack() -> str:
    return (
        "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,"
        "'Apple Color Emoji','Segoe UI Emoji',sans-serif"
    )


def _logo_header() -> str:
    return f"""
<tr>
  <td align="center" style="padding:28px 28px 20px;background:#ffffff;">
    <a href="{_esc(SITE_URL)}" style="text-decoration:none;">
      <img src="{_esc(LOGO_URL)}" alt="{_esc(BRAND)}" width="148" height="auto"
        style="display:block;border:0;outline:none;height:auto;max-width:148px;" />
    </a>
  </td>
</tr>
<tr>
  <td style="padding:0 28px;">
    <div style="height:1px;background:#eceef2;line-height:1px;font-size:1px;">&nbsp;</div>
  </td>
</tr>"""


def _email_footer() -> str:
    reply_hint = (
        f'Questions? Just reply to this email or reach us at '
        f'<a href="mailto:{_esc(SUPPORT_EMAIL)}" style="color:#111827;text-decoration:underline;">'
        f"{_esc(SUPPORT_EMAIL)}</a> — we’re happy to help."
        if SUPPORT_EMAIL
        else f'Questions? Visit <a href="{_esc(SUPPORT_URL)}" style="color:#111827;text-decoration:underline;">Help</a>.'
    )
    return f"""
<tr>
  <td style="padding:0 28px;">
    <div style="height:1px;background:#eceef2;line-height:1px;font-size:1px;">&nbsp;</div>
  </td>
</tr>
<tr>
  <td style="padding:22px 28px 8px;font-size:13px;line-height:1.55;color:#4b5563;text-align:center;">
    {reply_hint}
  </td>
</tr>
<tr>
  <td style="padding:0 28px 28px;font-size:12px;line-height:1.5;color:#9ca3af;text-align:center;">
    © {YEAR} {_esc(BRAND)}
  </td>
</tr>"""


def _shell(title: str, inner_rows: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>{_esc(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:{_font_stack()};color:#111827;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">
    {_esc(title)}
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f4f6;padding:28px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
          style="max-width:560px;background:#ffffff;border-radius:4px;overflow:hidden;">
          {_logo_header()}
          {inner_rows}
          {_email_footer()}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _pill_cta(label: str, url: str) -> str:
    return f"""
<table role="presentation" cellspacing="0" cellpadding="0" style="margin:28px auto 10px;">
  <tr>
    <td align="center" bgcolor="{INK}" style="border-radius:999px;background:{INK};">
      <a href="{_esc(url)}"
        style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:700;line-height:1.2;
        color:#ffffff;text-decoration:none;border-radius:999px;background:{INK};">
        {_esc(label)}
      </a>
    </td>
  </tr>
</table>"""


def _feature_row(title: str, body: str) -> str:
    return f"""
<tr>
  <td valign="top" width="40" style="padding:0 14px 22px 0;">
    <div style="width:28px;height:28px;border-radius:999px;background:#fff4e8;text-align:center;line-height:28px;">
      <span style="color:{ACCENT};font-size:15px;font-weight:700;">✓</span>
    </div>
  </td>
  <td valign="top" style="padding:0 0 22px 0;">
    <div style="font-size:16px;font-weight:700;color:#111827;margin:0 0 4px;">{_esc(title)}</div>
    <div style="font-size:14px;line-height:1.55;color:#4b5563;">{_esc(body)}</div>
  </td>
</tr>"""


def _meta_block(when: str, ip: Optional[str], user_agent: Optional[str]) -> str:
    rows = [f"<tr><td style='padding:4px 0;color:{MUTED};'>When</td><td style='padding:4px 0;'>{_esc(when)}</td></tr>"]
    if ip:
        rows.append(
            f"<tr><td style='padding:4px 0;color:{MUTED};'>IP address</td><td style='padding:4px 0;'>{_esc(ip)}</td></tr>"
        )
    if user_agent:
        ua = user_agent[:160] + ("…" if len(user_agent) > 160 else "")
        rows.append(
            f"<tr><td style='padding:4px 0;color:{MUTED};vertical-align:top;'>Device</td>"
            f"<td style='padding:4px 0;'>{_esc(ua)}</td></tr>"
        )
    return (
        "<table role='presentation' cellspacing='0' cellpadding='0' "
        "style='width:100%;margin:18px 0;padding:14px 16px;background:#f9fafb;"
        "border:1px solid #e5e7eb;border-radius:10px;font-size:13px;'>"
        + "".join(rows)
        + "</table>"
    )


def _wrap_html(title: str, body_html: str) -> str:
    return _shell(
        title,
        f"""
<tr>
  <td style="padding:28px 28px 8px;font-size:15px;line-height:1.55;color:#111827;">
    {body_html}
  </td>
</tr>""",
    )


def send_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    tags: Optional[list] = None,
) -> bool:
    if not email_enabled():
        logger.info("email skipped (no RESEND_API_KEY): to=%s subject=%s", to, subject)
        return False
    if not to:
        return False
    try:
        import resend

        resend.api_key = RESEND_API_KEY
        payload = {
            "from": EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }
        if EMAIL_REPLY_TO:
            payload["reply_to"] = EMAIL_REPLY_TO
        if tags:
            payload["tags"] = [{"name": "category", "value": t} for t in tags[:3]]
        resend.Emails.send(payload)
        return True
    except Exception:
        logger.exception("failed sending email to=%s subject=%s", to, subject)
        return False


def send_welcome_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    signup_method: str = "email",
) -> bool:
    first = _display_name(full_name, to)
    greet = _greeting_name(full_name, to)
    method_line = (
        "You signed up with Google — your account is ready."
        if signup_method == "google"
        else "Your email account is ready."
    )
    subject = f"Welcome to {BRAND} — keep bots out, keep humans moving"
    mark = (
        f'<span style="background:{ACCENT};color:#111827;padding:0 4px;border-radius:2px;'
        f'font-weight:700;">{_esc(BRAND)}</span>'
    )
    badge = (
        f'<span style="display:inline-block;padding:6px 12px;border:1px solid {ACCENT};'
        f'border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.06em;'
        f'color:{ACCENT};text-transform:uppercase;">'
        f'Welcome to <span style="background:{ACCENT};color:{INK};padding:0 4px;border-radius:2px;">'
        f'{_esc(BRAND.upper())}</span></span>'
    )
    features = "".join(
        [
            _feature_row(
                "Invisible when it can be",
                "Most real users pass quietly. Challenges only show when risk is high.",
            ),
            _feature_row(
                "Keys that fit your stack",
                "Create a site key and secret key, drop in one script, verify on your server.",
            ),
            _feature_row(
                "Dashboard and docs, ready now",
                "Manage domains, rotate keys, and follow a short integration path.",
            ),
        ]
    )
    html_body = _shell(
        subject,
        f"""
<tr>
  <td style="padding:0;background:{INK};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td style="padding:36px 28px 32px;">
          <div style="margin:0 0 18px;">{badge}</div>
          <h1 style="margin:0 0 20px;font-size:28px;line-height:1.25;font-weight:800;color:#ffffff;">
            Keep bots out.<br />Keep humans moving.
          </h1>
          <p style="margin:0 0 12px;font-size:15px;line-height:1.55;color:#e5e7eb;">
            Hi {_esc(greet)}, welcome aboard.
          </p>
          <p style="margin:0;font-size:15px;line-height:1.6;color:#d1d5db;">
            {mark} scores traffic in the background so your forms stay open to people —
            and closed to automated abuse. {_esc(method_line)}
          </p>
        </td>
      </tr>
    </table>
  </td>
</tr>
<tr>
  <td style="padding:32px 28px 8px;background:#ffffff;">
    <h2 style="margin:0 0 22px;font-size:22px;line-height:1.3;font-weight:800;color:#111827;">
      What you get from day one
    </h2>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      {features}
    </table>
    {_pill_cta("Open your dashboard", DASHBOARD_URL)}
    <p style="margin:0 0 8px;text-align:center;font-size:12px;color:#9ca3af;">
      Free tier available — no card required to start.
    </p>
    <p style="margin:18px 0 0;text-align:center;font-size:13px;color:{MUTED};">
      Prefer the docs first?
      <a href="{_esc(DOCS_URL)}" style="color:#111827;text-decoration:underline;">Quick start</a>
    </p>
  </td>
</tr>""",
    )
    text_body = f"""Welcome to {BRAND}

Hi {greet}, welcome aboard.

{BRAND} scores traffic in the background so your forms stay open to people — and closed to automated abuse.
{method_line}

What you get from day one
• Invisible when it can be — most real users pass quietly; challenges only when risk is high
• Keys that fit your stack — site key + secret key, one script, server verify
• Dashboard and docs — domains, keys, and a short integration path

Open your dashboard: {DASHBOARD_URL}
Docs: {DOCS_URL}

Free tier available — no card required to start.

Questions? Reach us at {SUPPORT_EMAIL}

© {YEAR} {BRAND}
"""
    return send_email(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        tags=["welcome"],
    )


def send_password_changed_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    was_set: bool = False,
) -> bool:
    first = _display_name(full_name, to)
    when = _utc_now_label()
    if was_set:
        subject = f"Password added to your {BRAND} account"
        event = "A password was added to your account."
        detail = "You can now sign in with email and password, in addition to any linked Google sign-in."
    else:
        subject = f"Your {BRAND} password was changed"
        event = "Your account password was changed."
        detail = "If you made this change, no further action is needed. Other signed-in sessions were signed out."
    html_body = _wrap_html(
        subject,
        f"""
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;font-weight:800;">Security update</h1>
<p style="margin:0 0 12px;">Hi {_esc(first)},</p>
<p style="margin:0 0 12px;">{_esc(event)}</p>
<p style="margin:0 0 12px;">{_esc(detail)}</p>
{_meta_block(when, ip, user_agent)}
{_pill_cta("Review account security", DASHBOARD_URL)}
<p style="margin:20px 0 0;font-size:13px;color:{MUTED};">
  If you did not make this change, secure your account from the dashboard and contact
  <a href="mailto:{_esc(SUPPORT_EMAIL)}" style="color:#111827;">{_esc(SUPPORT_EMAIL)}</a>.
</p>
""",
    )
    text_body = f"""Security update

Hi {first},

{event}
{detail}

When: {when}
IP address: {ip or "unknown"}
Device: {(user_agent or "unknown")[:160]}

Review account: {DASHBOARD_URL}

If you did not make this change, secure your account immediately and contact {SUPPORT_EMAIL}.

© {YEAR} {BRAND}
"""
    return send_email(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        tags=["security", "password"],
    )


def send_api_key_created_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    project_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    first = _display_name(full_name, to)
    when = _utc_now_label()
    project = (project_name or "your project").strip() or "your project"
    subject = f"New API keys created for {project}"
    html_body = _wrap_html(
        subject,
        f"""
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;font-weight:800;">New API keys created</h1>
<p style="margin:0 0 12px;">Hi {_esc(first)},</p>
<p style="margin:0 0 12px;">
  A new site key and secret key pair was created for <strong>{_esc(project)}</strong>.
</p>
<p style="margin:0 0 12px;">
  The secret key is only shown once in the dashboard. Treat it like a password and never expose it in browser code.
</p>
{_meta_block(when, ip, user_agent)}
{_pill_cta("Open dashboard", DASHBOARD_URL)}
<p style="margin:20px 0 0;font-size:13px;color:{MUTED};">
  If you did not create these keys, revoke them in the dashboard and contact
  <a href="mailto:{_esc(SUPPORT_EMAIL)}" style="color:#111827;">{_esc(SUPPORT_EMAIL)}</a>.
</p>
""",
    )
    text_body = f"""New API keys created

Hi {first},

A new site key and secret key pair was created for {project}.
The secret key is only shown once in the dashboard. Treat it like a password and never expose it in browser code.

When: {when}
IP address: {ip or "unknown"}
Device: {(user_agent or "unknown")[:160]}

Dashboard: {DASHBOARD_URL}

If you did not create these keys, revoke them immediately and contact {SUPPORT_EMAIL}.

© {YEAR} {BRAND}
"""
    return send_email(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        tags=["security", "api-keys"],
    )
