import html
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("veilproof.email")

RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
EMAIL_FROM = (os.getenv("EMAIL_FROM") or "VeilProof <noreply@mail.veilproof.tech>").strip()
EMAIL_REPLY_TO = (os.getenv("EMAIL_REPLY_TO") or "").strip()
DASHBOARD_URL = (os.getenv("DASHBOARD_URL") or "https://veilproof.tech/dashboard").rstrip("/")
DOCS_URL = (os.getenv("DOCS_URL") or "https://veilproof.tech/docs").rstrip("/")
SUPPORT_URL = (os.getenv("SUPPORT_URL") or "https://veilproof.tech/docs").rstrip("/")
SITE_URL = (os.getenv("SITE_URL") or "https://veilproof.tech").rstrip("/")
BRAND = "VeilProof"
BLUE = "#3578ff"
BLUE_SOFT = "#5f91ff"
NAVY = "#070c17"
NAVY_2 = "#0c1322"
SURFACE = "#0f1628"
INK = "#e8edf5"
MUTED = "#8b949e"
YEAR = datetime.now(timezone.utc).year


def email_enabled() -> bool:
    return bool((os.getenv("RESEND_API_KEY") or RESEND_API_KEY or "").strip())


def _resend_api_key() -> str:
    return (os.getenv("RESEND_API_KEY") or RESEND_API_KEY or "").strip()


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


def _brand_bar() -> str:
    return f"""
<tr>
  <td style="padding:0;background:{NAVY};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td style="padding:22px 28px 18px;">
          <a href="{_esc(SITE_URL)}"
            style="text-decoration:none;font-size:15px;font-weight:700;letter-spacing:.14em;
            color:#f5f7fb;font-family:{_font_stack()};">
            VEILPROOF
          </a>
        </td>
      </tr>
      <tr>
        <td style="padding:0;height:3px;line-height:3px;font-size:0;background:{BLUE};">&nbsp;</td>
      </tr>
    </table>
  </td>
</tr>"""


def _email_footer() -> str:
    return f"""
<tr>
  <td style="padding:24px 28px 28px;background:{NAVY};">
    <p style="margin:0;font-size:11px;line-height:1.5;color:#667083;">
      © {YEAR} {_esc(BRAND)} ·
      <a href="{_esc(DASHBOARD_URL)}" style="color:#667083;text-decoration:none;">Dashboard</a>
      ·
      <a href="{_esc(DOCS_URL)}" style="color:#667083;text-decoration:none;">Docs</a>
    </p>
  </td>
</tr>"""


def _shell(title: str, inner_rows: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="dark" />
  <title>{_esc(title)}</title>
</head>
<body style="margin:0;padding:0;background:#050812;font-family:{_font_stack()};color:{INK};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">{_esc(title)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#050812;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
          style="max-width:560px;background:{NAVY_2};border:1px solid #1a2236;border-radius:12px;overflow:hidden;">
          {_brand_bar()}
          {inner_rows}
          {_email_footer()}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _cta(label: str, url: str) -> str:
    return f"""
<table role="presentation" cellspacing="0" cellpadding="0" style="margin:8px 0 4px;">
  <tr>
    <td bgcolor="{BLUE}" style="border-radius:8px;background:{BLUE};">
      <a href="{_esc(url)}"
        style="display:inline-block;padding:12px 20px;font-size:14px;font-weight:650;line-height:1.2;
        color:#ffffff;text-decoration:none;border-radius:8px;background:{BLUE};">
        {_esc(label)}
      </a>
    </td>
  </tr>
</table>"""


def _step(num: str, title: str, body: str) -> str:
    return f"""
<tr>
  <td valign="top" width="36" style="padding:0 12px 18px 0;">
    <div style="width:28px;height:28px;border-radius:6px;background:{SURFACE};border:1px solid #243049;
      text-align:center;line-height:28px;font-size:12px;font-weight:700;color:{BLUE_SOFT};">
      {_esc(num)}
    </div>
  </td>
  <td valign="top" style="padding:0 0 18px 0;">
    <div style="font-size:14px;font-weight:650;color:{INK};margin:0 0 4px;">{_esc(title)}</div>
    <div style="font-size:13px;line-height:1.55;color:{MUTED};">{_esc(body)}</div>
  </td>
</tr>"""


def _meta_block(
    when: str,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_rows: Optional[List[tuple]] = None,
) -> str:
    rows = [
        f"<tr><td style='padding:5px 0;color:{MUTED};width:110px;'>When</td>"
        f"<td style='padding:5px 0;color:{INK};'>{_esc(when)}</td></tr>"
    ]
    if ip:
        rows.append(
            f"<tr><td style='padding:5px 0;color:{MUTED};'>IP</td>"
            f"<td style='padding:5px 0;color:{INK};'>{_esc(ip)}</td></tr>"
        )
    if user_agent:
        ua = user_agent[:160] + ("…" if len(user_agent) > 160 else "")
        rows.append(
            f"<tr><td style='padding:5px 0;color:{MUTED};vertical-align:top;'>Device</td>"
            f"<td style='padding:5px 0;color:{INK};'>{_esc(ua)}</td></tr>"
        )
    for label, value in extra_rows or []:
        if value is None or value == "":
            continue
        rows.append(
            f"<tr><td style='padding:5px 0;color:{MUTED};vertical-align:top;'>{_esc(label)}</td>"
            f"<td style='padding:5px 0;color:{INK};'>{_esc(str(value))}</td></tr>"
        )
    return (
        f"<table role='presentation' cellspacing='0' cellpadding='0' "
        f"style='width:100%;margin:16px 0;padding:14px 16px;background:{SURFACE};"
        f"border:1px solid #243049;border-radius:8px;font-size:13px;'>"
        + "".join(rows)
        + "</table>"
    )


def _wrap_html(title: str, body_html: str) -> str:
    return _shell(
        title,
        f"""
<tr>
  <td style="padding:28px 28px 12px;background:{NAVY_2};font-size:15px;line-height:1.6;color:{INK};">
    {body_html}
  </td>
</tr>""",
    )


def _notice(
    *,
    to: str,
    full_name: Optional[str],
    subject: str,
    eyebrow: str,
    title: str,
    lines: List[str],
    tags: List[str],
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_rows: Optional[List[tuple]] = None,
    cta_label: str = "Open dashboard",
    caution: Optional[str] = None,
) -> bool:
    first = _display_name(full_name, to)
    when = _utc_now_label()
    paras_html = "".join(
        f'<p style="margin:0 0 12px;color:#c5cdd8;">{_esc(line)}</p>' for line in lines
    )
    caution_html = (
        f'<p style="margin:16px 0 0;font-size:13px;color:{MUTED};">{_esc(caution)} '
        f'<a href="{_esc(SUPPORT_URL)}" style="color:{BLUE_SOFT};">docs</a>.</p>'
        if caution
        else ""
    )
    html_body = _wrap_html(
        subject,
        f"""
<p style="margin:0 0 6px;font-size:12px;font-weight:650;letter-spacing:.08em;text-transform:uppercase;color:{BLUE_SOFT};">
  {_esc(eyebrow)}
</p>
<h1 style="margin:0 0 14px;font-size:22px;line-height:1.3;font-weight:700;color:#f5f7fb;">{_esc(title)}</h1>
<p style="margin:0 0 12px;color:#c5cdd8;">Hi {_esc(first)},</p>
{paras_html}
{_meta_block(when, ip, user_agent, extra_rows)}
{_cta(cta_label, DASHBOARD_URL)}
{caution_html}
""",
    )
    text_lines = "\n".join(lines)
    extra_txt = ""
    for label, value in extra_rows or []:
        if value is None or value == "":
            continue
        extra_txt += f"{label}: {value}\n"
    caution_txt = f"\n{caution} See {SUPPORT_URL}." if caution else ""
    text_body = f"""{title}

Hi {first},

{text_lines}

When: {when}
IP: {ip or "unknown"}
Device: {(user_agent or "unknown")[:160]}
{extra_txt}
Dashboard: {DASHBOARD_URL}{caution_txt}

© {YEAR} {BRAND}
"""
    return send_email(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        tags=tags,
    )


def send_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    tags: Optional[list] = None,
) -> bool:
    api_key = _resend_api_key()
    if not api_key:
        logger.warning("email skipped (no RESEND_API_KEY): to=%s subject=%s", to, subject)
        return False
    if not to:
        return False
    try:
        import resend

        resend.api_key = api_key
        from_addr = (os.getenv("EMAIL_FROM") or EMAIL_FROM or "").strip()
        payload = {
            "from": from_addr,
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }
        reply_to = (os.getenv("EMAIL_REPLY_TO") or EMAIL_REPLY_TO or "").strip()
        if reply_to:
            payload["reply_to"] = reply_to
        if tags:
            payload["tags"] = [{"name": "category", "value": tags[0][:256]}]
            if len(tags) > 1:
                payload["tags"].append({"name": "type", "value": tags[1][:256]})
        resend.Emails.send(payload)
        logger.info("email sent to=%s subject=%s", to, subject)
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
        "Signed in with Google — your workspace is ready."
        if signup_method == "google"
        else "Your email account is active."
    )
    subject = f"Your {BRAND} account is ready"
    steps = "".join(
        [
            _step("1", "Create your keys", "Generate a site key and secret key for your project."),
            _step("2", "Allow your domains", "Lock keys to the origins that will load the script."),
            _step("3", "Wire verify", "Issue tokens in the browser, confirm them with siteverify on your server."),
        ]
    )
    html_body = _shell(
        subject,
        f"""
<tr>
  <td style="padding:32px 28px 8px;background:{NAVY_2};">
    <p style="margin:0 0 6px;font-size:12px;font-weight:650;letter-spacing:.08em;text-transform:uppercase;color:{BLUE_SOFT};">
      Account ready
    </p>
    <h1 style="margin:0 0 14px;font-size:24px;line-height:1.3;font-weight:700;color:#f5f7fb;">
      Hi {_esc(first)} — you’re in.
    </h1>
    <p style="margin:0 0 12px;font-size:15px;line-height:1.65;color:#c5cdd8;">
      {_esc(BRAND)} protects forms and auth flows without forcing every visitor through a puzzle.
      {_esc(method_line)}
    </p>
    <p style="margin:0 0 8px;font-size:14px;line-height:1.6;color:{MUTED};">
      Hi {_esc(greet)}, open the dashboard when you’re ready to issue keys and ship the integration.
    </p>
  </td>
</tr>
<tr>
  <td style="padding:20px 28px 8px;background:{NAVY_2};">
    <p style="margin:0 0 16px;font-size:13px;font-weight:650;letter-spacing:.06em;text-transform:uppercase;color:#667083;">
      First steps
    </p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      {steps}
    </table>
    {_cta("Open dashboard", DASHBOARD_URL)}
    <p style="margin:14px 0 0;font-size:13px;color:{MUTED};">
      Integration guide:
      <a href="{_esc(DOCS_URL)}" style="color:{BLUE_SOFT};text-decoration:none;">{_esc(DOCS_URL)}</a>
    </p>
  </td>
</tr>""",
    )
    text_body = f"""Your {BRAND} account is ready

Hi {first} — you're in.

{BRAND} protects forms and auth flows without forcing every visitor through a puzzle.
{method_line}

First steps
1. Create your keys — site key + secret key for your project
2. Allow your domains — lock keys to the origins that load the script
3. Wire verify — tokens in the browser, siteverify on your server

Dashboard: {DASHBOARD_URL}
Docs: {DOCS_URL}

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
    if was_set:
        subject = f"Password added to your {BRAND} account"
        title = "Password added"
        lines = [
            "A password was added to your account.",
            "You can now sign in with email and password, in addition to any linked Google sign-in.",
        ]
    else:
        subject = f"Your {BRAND} password was changed"
        title = "Password changed"
        lines = [
            "Your account password was changed.",
            "If you made this change, no further action is needed. Other signed-in sessions were signed out.",
        ]
    return _notice(
        to=to,
        full_name=full_name,
        subject=subject,
        eyebrow="Security",
        title=title,
        lines=lines,
        tags=["security", "password"],
        ip=ip,
        user_agent=user_agent,
        cta_label="Review account",
        caution="If this wasn’t you, secure the account from the dashboard and review",
    )


def send_new_signin_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    method: str = "password",
) -> bool:
    method_label = "Google" if method == "google" else "email and password"
    return _notice(
        to=to,
        full_name=full_name,
        subject=f"New sign-in to your {BRAND} account",
        eyebrow="Security",
        title="New sign-in",
        lines=[
            f"Someone just signed in to your {BRAND} account with {method_label}.",
            "If this was you, you can ignore this message.",
        ],
        tags=["security", "signin"],
        ip=ip,
        user_agent=user_agent,
        extra_rows=[("Method", method_label)],
        cta_label="Review account",
        caution="If this wasn’t you, change your password from the dashboard and review",
    )


def send_api_key_created_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    project_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    key_kind: str = "pair",
) -> bool:
    project = (project_name or "your project").strip() or "your project"
    if key_kind == "pair":
        subject = f"New API keys created for {project}"
        title = "New keys issued"
        lines = [
            f"A site key and secret key pair was created for {project}.",
            "The secret is shown once in the dashboard. Keep it server-side only.",
        ]
    else:
        subject = f"New API key created for {project}"
        title = "New API key issued"
        lines = [
            f"A new API key was created for {project}.",
            "Treat secret keys like passwords and never expose them in browser code.",
        ]
    return _notice(
        to=to,
        full_name=full_name,
        subject=subject,
        eyebrow="API keys",
        title=title,
        lines=lines,
        tags=["security", "api-keys"],
        ip=ip,
        user_agent=user_agent,
        extra_rows=[("Project", project)],
        caution="If this wasn’t you, revoke the keys in the dashboard and review",
    )


def send_api_key_rotated_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    project_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    grace_hours: Optional[float] = None,
) -> bool:
    project = (project_name or "your project").strip() or "your project"
    if grace_hours and grace_hours > 0:
        grace_line = f"The previous key stays valid for about {grace_hours:g} hour(s), then stops working."
    else:
        grace_line = "The previous key was deactivated immediately."
    return _notice(
        to=to,
        full_name=full_name,
        subject=f"API key rotated for {project}",
        eyebrow="API keys",
        title="API key rotated",
        lines=[
            f"An API key was rotated for {project}.",
            grace_line,
            "Update your servers with the new secret if you haven’t already.",
        ],
        tags=["security", "api-keys"],
        ip=ip,
        user_agent=user_agent,
        extra_rows=[("Project", project)],
        caution="If this wasn’t you, revoke keys in the dashboard and review",
    )


def send_api_key_revoked_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    project_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    project = (project_name or "your project").strip() or "your project"
    return _notice(
        to=to,
        full_name=full_name,
        subject=f"API key revoked for {project}",
        eyebrow="API keys",
        title="API key revoked",
        lines=[
            f"An API key was revoked for {project}.",
            "Requests that used that key will fail immediately.",
        ],
        tags=["security", "api-keys"],
        ip=ip,
        user_agent=user_agent,
        extra_rows=[("Project", project)],
        caution="If this wasn’t you, review your account in the dashboard and",
    )


def send_domains_updated_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    project_name: Optional[str] = None,
    domains: Optional[List[str]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    project = (project_name or "your project").strip() or "your project"
    domain_list = domains or []
    if domain_list:
        domain_summary = ", ".join(domain_list[:12])
        if len(domain_list) > 12:
            domain_summary += f" (+{len(domain_list) - 12} more)"
        domains_line = f"Allowed domains are now: {domain_summary}."
    else:
        domains_line = "Allowed domains were cleared for this project."
    return _notice(
        to=to,
        full_name=full_name,
        subject=f"Allowed domains updated for {project}",
        eyebrow="Project",
        title="Domains updated",
        lines=[
            f"Allowed domains were updated for {project}.",
            domains_line,
        ],
        tags=["security", "domains"],
        ip=ip,
        user_agent=user_agent,
        extra_rows=[("Project", project)],
        caution="If this wasn’t you, restore the correct domains in the dashboard and review",
    )


def send_project_created_email(
    to: str,
    *,
    full_name: Optional[str] = None,
    project_name: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    project = (project_name or "your project").strip() or "your project"
    return _notice(
        to=to,
        full_name=full_name,
        subject=f"Project created: {project}",
        eyebrow="Project",
        title="Project created",
        lines=[
            f"A new project named {project} was created on your {BRAND} account.",
            "Next, create keys and add the domains that will load the client script.",
        ],
        tags=["project"],
        ip=ip,
        user_agent=user_agent,
        extra_rows=[("Project", project)],
        caution="If this wasn’t you, review your account in the dashboard and",
    )
