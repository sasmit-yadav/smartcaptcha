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
BRAND = "VeilProof"


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


def _utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def _wrap_html(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f5f7;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:24px 28px 8px;font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#2563eb;">
              {_esc(BRAND)}
            </td>
          </tr>
          <tr>
            <td style="padding:8px 28px 28px;font-size:15px;line-height:1.55;color:#111827;">
              {body_html}
            </td>
          </tr>
        </table>
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;">
          <tr>
            <td style="padding:16px 8px 0;font-size:12px;line-height:1.5;color:#6b7280;text-align:center;">
              You’re receiving this email because of activity on your {_esc(BRAND)} account.<br />
              <a href="{_esc(DASHBOARD_URL)}" style="color:#2563eb;text-decoration:none;">Dashboard</a>
              &nbsp;·&nbsp;
              <a href="{_esc(DOCS_URL)}" style="color:#2563eb;text-decoration:none;">Docs</a>
              &nbsp;·&nbsp;
              <a href="{_esc(SUPPORT_URL)}" style="color:#2563eb;text-decoration:none;">Help</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _cta(label: str, url: str) -> str:
    return f"""
<p style="margin:24px 0 8px;">
  <a href="{_esc(url)}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;padding:12px 18px;border-radius:8px;">
    {_esc(label)}
  </a>
</p>
<p style="margin:0;font-size:12px;color:#6b7280;word-break:break-all;">
  Or open: <a href="{_esc(url)}" style="color:#2563eb;">{_esc(url)}</a>
</p>"""


def _meta_block(when: str, ip: Optional[str], user_agent: Optional[str]) -> str:
    rows = [f"<tr><td style='padding:4px 0;color:#6b7280;'>When</td><td style='padding:4px 0;'>{_esc(when)}</td></tr>"]
    if ip:
        rows.append(
            f"<tr><td style='padding:4px 0;color:#6b7280;'>IP address</td><td style='padding:4px 0;'>{_esc(ip)}</td></tr>"
        )
    if user_agent:
        ua = user_agent[:160] + ("…" if len(user_agent) > 160 else "")
        rows.append(
            f"<tr><td style='padding:4px 0;color:#6b7280;vertical-align:top;'>Device</td><td style='padding:4px 0;'>{_esc(ua)}</td></tr>"
        )
    return (
        "<table role='presentation' cellspacing='0' cellpadding='0' "
        "style='width:100%;margin:16px 0;padding:12px 14px;background:#f9fafb;"
        "border:1px solid #e5e7eb;border-radius:8px;font-size:13px;'>"
        + "".join(rows)
        + "</table>"
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
    method_line = (
        "You signed up with Google."
        if signup_method == "google"
        else "Your email and password account is ready."
    )
    subject = f"Welcome to {BRAND}"
    html_body = _wrap_html(
        subject,
        f"""
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;font-weight:700;">Welcome to {_esc(BRAND)}, {_esc(first)}</h1>
<p style="margin:0 0 12px;">Your account is active. {_esc(method_line)}</p>
<p style="margin:0 0 12px;">Next steps:</p>
<ol style="margin:0 0 12px;padding-left:20px;">
  <li>Open your dashboard and create a site key + secret key pair</li>
  <li>Add your allowed domains</li>
  <li>Follow the quick start in the docs</li>
</ol>
{_cta("Open your dashboard", DASHBOARD_URL)}
<p style="margin:20px 0 0;font-size:13px;color:#6b7280;">
  Docs: <a href="{_esc(DOCS_URL)}" style="color:#2563eb;">{_esc(DOCS_URL)}</a>
</p>
""",
    )
    text_body = f"""Welcome to {BRAND}, {first}

Your account is active. {method_line}

Next steps:
1. Open your dashboard and create a site key + secret key pair
2. Add your allowed domains
3. Follow the quick start in the docs

Dashboard: {DASHBOARD_URL}
Docs: {DOCS_URL}

You’re receiving this because you created a {BRAND} account.
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
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;font-weight:700;">Security update</h1>
<p style="margin:0 0 12px;">Hi {_esc(first)},</p>
<p style="margin:0 0 12px;">{_esc(event)}</p>
<p style="margin:0 0 12px;">{_esc(detail)}</p>
{_meta_block(when, ip, user_agent)}
{_cta("Review account security", DASHBOARD_URL)}
<p style="margin:20px 0 0;font-size:13px;color:#6b7280;">
  If you did not make this change, reset your password immediately from the dashboard
  and contact support via <a href="{_esc(SUPPORT_URL)}" style="color:#2563eb;">Help</a>.
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

If you did not make this change, secure your account immediately and contact support via {SUPPORT_URL}.
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
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;font-weight:700;">New API keys created</h1>
<p style="margin:0 0 12px;">Hi {_esc(first)},</p>
<p style="margin:0 0 12px;">
  A new site key and secret key pair was created for <strong>{_esc(project)}</strong>.
</p>
<p style="margin:0 0 12px;">
  The secret key is only shown once in the dashboard. Treat it like a password and never expose it in browser code.
</p>
{_meta_block(when, ip, user_agent)}
{_cta("Open dashboard", DASHBOARD_URL)}
<p style="margin:20px 0 0;font-size:13px;color:#6b7280;">
  If you did not create these keys, revoke them in the dashboard and contact support via
  <a href="{_esc(SUPPORT_URL)}" style="color:#2563eb;">Help</a>.
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

If you did not create these keys, revoke them immediately and contact support via {SUPPORT_URL}.
"""
    return send_email(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        tags=["security", "api-keys"],
    )
