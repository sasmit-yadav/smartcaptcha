"""
Tool-config bot: AI-agent/LLM-driven browser (strategy doc Part D.1 / D.4;
STEP3_STEP8_IMPLEMENTATION_SPEC.md §8.1's `browser_use_agent.py`).

Every other real_bots/* class drives a real browser via *hand-scripted*
Selenium/Playwright calls (fixed selectors, coded mouse paths). This one
drives a real Playwright/Chromium browser via an LLM agent (the `browser-use`
library) acting on natural-language instructions only ("find the email
field and type X") — the click targets, cursor path, and pacing are
whatever browser-use's CDP-level actions produce when the model decides to
act, not anything this script codes directly. That is the open D.1
question: does an agentic browser's behavior look more or less human than
`test_stealth_bot.py`'s hand-tuned jitter? Nobody has measured it yet.

Deliberately scoped down (per the 2026-07-19 agreed plan) to just this one
persona for an initial ~20-30 session read, before committing to the full
Step 8 build (4 personas, human-baseline crowdsourcing, vendor comparison).

Session identity + labeling follow the exact same pattern as
playwright_bot.py/selenium_plain_bot.py: demo-site's own inline collector
(login.html's <script type="module">) mints its own sessionId client-side
via crypto.randomUUID()/sessionStorage — this script reads it back out of
the live page (via a CDP Runtime.evaluate call, since browser-use's
BrowserSession is CDP-native, not a raw Playwright Page) after the agent
acts, then labels that row `bot` directly in the DB (common.label_session,
bypassing the ingest-key hop, same as every other real_bots/* helper).

Deliberately does NOT ask the agent to interact with any field beyond email/
password/submit — login.html's honeypot input (`data-vp-honeypot`, off-screen,
aria-hidden) would trivially force a block if tripped, which would answer a
different question (does this bot trip the honeypot) than the one this
persona exists to measure (does the model's *behavioral* axis alone catch it).

Requires: `OPENAI_API_KEY` in ml-train/.env (already provisioned), the
`browser-use` package (installed into ml-train/.venv, kept out of the global
Python env — see docs/current_task.md), demo-site running on DEMO_SITE_URL,
and the sdk-backend instance demo-site's config.js points at reachable.
"""
import argparse
import asyncio
import os
import random
import time

try:
    from ..common import DEMO_SITE_URL, label_session, wait_for_telemetry_flush
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from common import DEMO_SITE_URL, label_session, wait_for_telemetry_flush

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PROVIDER = "openai"


class _GeminiKeyRotator:
    """Gemini's free tier is 20 requests/day *per Google Cloud project*
    (2026-07-19 finding — see docs/current_task.md). Each session costs
    ~5 LLM calls, so one project/key is good for ~4 sessions. Rather than
    stop the batch every time one key's daily quota is hit, read every
    `GEMINI_API_KEY`/`GEMINI_API_KEY_2`/`GEMINI_API_KEY_3`/... (or a single
    comma-separated `GEMINI_API_KEYS`) from ml-train/.env and round-robin,
    advancing to the next key whenever a run fails outright."""

    def __init__(self):
        keys: list[str] = []
        raw = os.getenv("GEMINI_API_KEYS")
        if raw:
            keys.extend(k.strip() for k in raw.split(",") if k.strip())
        base = os.getenv("GEMINI_API_KEY")
        if base and base not in keys:
            keys.append(base)
        i = 1
        while True:
            v = os.getenv(f"GEMINI_API_KEY_{i}")
            if not v:
                break
            if v not in keys:
                keys.append(v)
            i += 1
        self.keys = keys
        self.idx = 0

    def current(self) -> str | None:
        if not self.keys:
            return None
        return self.keys[self.idx % len(self.keys)]

    def advance(self):
        if self.keys:
            self.idx += 1

    def __len__(self):
        return len(self.keys)


_gemini_rotator = _GeminiKeyRotator()

TASK_TEMPLATE = (
    "Go to {url}. Wait for the page to fully load. "
    "Find the input field labeled 'Email address' and type '{email}' into it. "
    "Find the input field labeled 'Password' and type '{password}' into it. "
    "Then click the 'Sign In' button to submit the form. "
    "Only interact with the email field, the password field, and the Sign In "
    "button. Do not click, focus, or fill any other input on the page — "
    "there may be other elements present, ignore all of them. "
    "The task is complete as soon as you have clicked Sign In."
)


async def _read_session_id(browser_session) -> str | None:
    """Read demo-site's client-generated sessionId out of the live page via
    CDP (BrowserSession is CDP-native, no raw Playwright Page.evaluate)."""
    try:
        cdp_session = await browser_session.get_or_create_cdp_session()
        result = await cdp_session.cdp_client.send.Runtime.evaluate(
            params={
                "expression": "sessionStorage.getItem('sc_session_id')",
                "returnByValue": True,
            },
            session_id=cdp_session.session_id,
        )
        return (result or {}).get("result", {}).get("value")
    except Exception as e:
        print(f"[browser_use_agent] session_id read failed: {e}")
        return None


def _build_llm(provider: str, model: str | None):
    """browser-use accepts any of its LLM wrapper classes interchangeably;
    swapping provider is just picking a different one with a sane default
    model per provider. 2026-07-19: tried OpenAI (quota-exhausted key) then
    Gemini free tier (20 req/day cap — exhausted after ~4 sessions, each
    session costs 3-5 LLM calls); added Groq as a third option since its
    free tier has a much higher daily cap and it hosts a vision-capable
    model (llama-4-scout) — see docs/current_task.md."""
    if provider == "google":
        from browser_use.llm import ChatGoogle
        return ChatGoogle(model=model or "gemini-flash-latest", api_key=_gemini_rotator.current())
    if provider == "openai":
        from browser_use.llm import ChatOpenAI
        return ChatOpenAI(model=model or DEFAULT_MODEL)
    if provider == "groq":
        # meta-llama/llama-4-scout (vision) isn't enabled on every Groq
        # account tier; llama-3.3-70b-versatile is a reliable text-only
        # fallback that's broadly available on the free tier.
        from browser_use.llm import ChatGroq
        return ChatGroq(model=model or "llama-3.3-70b-versatile")
    if provider == "openrouter":
        # OpenRouter's ":free" model variants have per-day limits well above
        # Gemini's 20/day and no per-project juggling needed — added
        # 2026-07-19 after Gemini's two keys both got blocked for the day
        # (one on quota, one on a project-level 403). See docs/current_task.md.
        from browser_use.llm import ChatOpenRouter
        return ChatOpenRouter(
            model=model or "meta-llama/llama-3.2-11b-vision-instruct:free",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    if provider == "ollama":
        # Genuinely unlimited: runs entirely locally (localhost:11434), no
        # API key, no rate limit, no per-day cap — bounded only by local
        # compute. Added 2026-07-19 after every hosted free tier (Gemini,
        # Groq, OpenRouter) hit some real capacity ceiling for a batch of
        # 20-30 sessions. llama3.2:3b is a small text-only model (no vision)
        # already pulled on this machine; `ollama pull <model>` first for
        # anything else.
        from browser_use.llm import ChatOllama
        return ChatOllama(model=model or "llama3.2:latest")
    raise ValueError(
        f"Unknown provider: {provider!r} (expected 'openai', 'google', 'groq', 'openrouter', or 'ollama')"
    )


# Only providers with a vision-capable free model confirmed available get
# use_vision=True; others fall back to DOM-only (text) actions.
_VISION_BY_PROVIDER = {"openai": True, "google": True, "groq": False, "openrouter": True, "ollama": False}

# browser-use's default llm_timeout is 75s, sized for hosted APIs. A 3B model
# on CPU (no GPU on this machine — confirmed via `ollama ps` showing
# "100% CPU") chewing through a ~9k-token DOM prompt can genuinely take
# longer than that and still be making real progress, not hung.
_LLM_TIMEOUT_BY_PROVIDER = {"ollama": 300}
_STEP_TIMEOUT_BY_PROVIDER = {"ollama": 350}


async def run_async(
    headless: bool = True,
    model: str | None = None,
    provider: str = DEFAULT_PROVIDER,
) -> str | None:
    """Run one agentic-browser login session. Returns the collector's own
    sessionId, or None on failure."""
    from browser_use import Agent, BrowserSession

    email = f"agent.user{random.randint(1000, 9999)}@example.com"
    password = f"AgentPass{random.randint(100, 999)}!"
    task = TASK_TEMPLATE.format(url=f"{DEMO_SITE_URL}/login.html", email=email, password=password)

    browser_session = BrowserSession(
        headless=headless,
        allowed_domains=["localhost"],
        window_size={"width": 1400, "height": 900},
        keep_alive=True,  # agent.run() otherwise tears down the CDP session
                          # on task completion, before we can read sessionId
    )
    llm = _build_llm(provider, model)
    use_vision = _VISION_BY_PROVIDER.get(provider, True)
    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser_session,
        use_vision=use_vision,
        llm_timeout=_LLM_TIMEOUT_BY_PROVIDER.get(provider),
        step_timeout=_STEP_TIMEOUT_BY_PROVIDER.get(provider, 180),
    )

    session_id = None
    try:
        await agent.run(max_steps=15)

        # login.html's own JS navigates to /quiz.html ~2.3s after a valid
        # submit, which fires beforeunload -> sendTelemetry() in-page.
        # sessionStorage persists across that same-tab navigation, so the ID
        # is still readable afterward regardless of exact timing.
        await asyncio.sleep(3.5)
        session_id = await _read_session_id(browser_session)

        wait_for_telemetry_flush(2.0)
    except Exception as e:
        print(f"[browser_use_agent] error: {e}")
    finally:
        try:
            await browser_session.kill()
        except Exception:
            pass

    if session_id:
        label_session(session_id, "bot")
        print(f"[browser_use_agent] labeled session {session_id[:8]}...")
    else:
        print("[browser_use_agent] no session_id captured")
    return session_id


def run(headless: bool = True, model: str | None = None, provider: str = DEFAULT_PROVIDER) -> str | None:
    """Sync wrapper so this matches the other real_bots/*.run() signature
    used by run_all.py."""
    return asyncio.run(run_async(headless=headless, model=model, provider=provider))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LLM-agent (browser-use) persona once")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument(
        "--provider", choices=["openai", "google", "groq", "openrouter", "ollama"], default=DEFAULT_PROVIDER
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Defaults to gpt-4o-mini (openai), gemini-2.5-flash (google), or llama-4-scout (groq)",
    )
    args = parser.parse_args()

    if args.provider == "google" and len(_gemini_rotator):
        print(f"[browser_use_agent] {len(_gemini_rotator)} Gemini key(s) loaded for rotation")

    ok = 0
    for i in range(args.runs):
        print(f"\n--- browser_use_agent run {i + 1}/{args.runs} ---")
        try:
            sid = run(headless=args.headless, model=args.model, provider=args.provider)
            if sid:
                ok += 1
            elif args.provider == "google":
                # Most likely cause of a failed run is that day's quota on
                # the current key — move to the next one for the next run.
                _gemini_rotator.advance()
                print(f"[browser_use_agent] rotating to Gemini key index {_gemini_rotator.idx % max(len(_gemini_rotator), 1)}")
        except Exception as e:
            print(f"[browser_use_agent] run {i + 1} failed: {e}")
            if args.provider == "google":
                _gemini_rotator.advance()
        time.sleep(1)
    print(f"\nbrowser_use_agent: {ok}/{args.runs} sessions labeled")
