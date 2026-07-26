'use client';

import { useEffect, useState } from 'react';
import { Rocket, Code, Server, Layers, ShieldCheck, BookOpen, LifeBuoy, Cog } from 'lucide-react';
import SiteNav from '../../components/chrome/SiteNav';
import SiteFooter from '../../components/chrome/SiteFooter';
import CodeBlock from '../../components/docs/CodeBlock';
import TabbedCode from '../../components/docs/TabbedCode';
import Callout from '../../components/docs/Callout';
import EndpointCard from '../../components/docs/EndpointCard';
import {
  scriptTagSnippet, scriptTagFormSnippet, htmlCompleteSnippet, programmaticHtmlSnippet,
  npmInstallSnippet, npmInitSnippet,
  reactSnippet, nextjsSnippet, vueSnippet,
  siteverifyCurlSnippet, siteverifyNodeSnippet, siteverifyPythonFlaskSnippet,
  siteverifyPythonDjangoSnippet, siteverifyPhpSnippet,
  siteverifyJavaSnippet, siteverifyRubySnippet, siteverifyGoSnippet, siteverifyCsharpSnippet,
  siteverifySuccessResponse, siteverifyBlockedResponse, siteverifyErrorResponse,
  predictAllowResponse, predictBlockResponse, CDN_URL, API_HOST,
} from '../../components/docs/docSnippets';

const NAV = [
  { id: 'start', title: 'Getting Started', icon: Rocket },
  { id: 'how', title: 'How It Works', icon: Cog },
  { id: 'client', title: 'Client Integration', icon: Code },
  { id: 'server', title: 'Server Verification', icon: Server },
  { id: 'api', title: 'API Reference', icon: Layers },
  { id: 'security', title: 'Security', icon: ShieldCheck },
  { id: 'sdk', title: 'SDK Reference', icon: BookOpen },
  { id: 'help', title: 'Troubleshooting', icon: LifeBuoy },
];

function Section({ title, children }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{title}</h2>
      {children}
    </div>
  );
}

function H3({ children }) {
  return <h3 className="text-lg font-bold mt-8 mb-3">{children}</h3>;
}

function P({ children }) {
  return <p className="text-mute leading-relaxed">{children}</p>;
}

function Checklist({ items }) {
  return (
    <ol className="space-y-3 list-decimal list-inside text-mute text-sm leading-relaxed">
      {items.map((item, index) => (
        <li key={index} className="pl-1">{item}</li>
      ))}
    </ol>
  );
}

function Mistake({ title, children }) {
  return (
    <div className="border border-hairline rounded-xl p-4 bg-surfaceSoft/40">
      <div className="font-semibold text-sm text-ink mb-1">{title}</div>
      <div className="text-mute text-sm leading-relaxed">{children}</div>
    </div>
  );
}

export default function DocsPage() {
  const [active, setActive] = useState('start');

  useEffect(() => {
    const syncFromUrl = () => {
      const hash = window.location.hash.replace('#', '');
      if (NAV.some((item) => item.id === hash)) setActive(hash);
    };
    syncFromUrl();
    window.addEventListener('hashchange', syncFromUrl);
    return () => window.removeEventListener('hashchange', syncFromUrl);
  }, []);

  const selectSection = (id) => {
    setActive(id);
    window.history.replaceState(null, '', `#${id}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const content = {
    start: (
      <Section title="Getting Started">
        <P>
          VeilProof is invisible bot detection. The <strong className="text-ink">browser SDK</strong> collects
          signals and returns a short-lived token. Your <strong className="text-ink">server</strong> redeems
          that token with a secret key and decides allow vs block. The browser alone is never trusted.
        </P>

        <H3>Step 0 — create your account and get your keys</H3>
        <P>
          Never used VeilProof before? Start here, before any code.
        </P>
        <Checklist
          items={[
            <>
              Go to the <a className="text-primary underline" href="/dashboard">dashboard</a> and sign up with
              an email + password, or continue with Google.
            </>,
            <>
              If you signed up with email, check your inbox for a verification email and click the link.
              Keys stay locked until the account is verified (Google sign-in counts as verified automatically).
            </>,
            <>
              Click <strong className="text-ink">Create Project</strong>, give it any name (usually your site's
              name), and save.
            </>,
            <>
              Open the project and click <strong className="text-ink">Generate API Key Pair</strong>. The dashboard
              creates both keys for you, a <code className="text-primary">vp_site_…</code> key and a{' '}
              <code className="text-primary">vp_secret_…</code> key. You never type or invent these yourself.
            </>,
            <>
              Copy both somewhere safe now. The secret key is only shown in full once, right after you
              generate it.
            </>,
          ]}
        />

        <div className="grid md:grid-cols-3 gap-4">
          <div className="card p-5">
            <div className="text-primary font-bold text-sm uppercase tracking-wide mb-2">1. Get keys</div>
            <p className="text-mute text-sm">
              In the <a className="text-primary underline" href="/dashboard">dashboard</a>, create a project.
              You receive a pair: <code className="text-primary">vp_site_…</code> (public) and{' '}
              <code className="text-primary">vp_secret_…</code> (private).
            </p>
          </div>
          <div className="card p-5">
            <div className="text-primary font-bold text-sm uppercase tracking-wide mb-2">2. Add the SDK</div>
            <p className="text-mute text-sm">
              One script tag (or <code className="text-primary">npm install veilproof</code>) with your{' '}
              <strong className="text-ink">site key</strong>. Prefer the classic form pattern if you want zero custom JS.
            </p>
          </div>
          <div className="card p-5">
            <div className="text-primary font-bold text-sm uppercase tracking-wide mb-2">3. Verify on server</div>
            <p className="text-mute text-sm">
              On every protected request, call <code className="text-primary">POST {API_HOST}/api/siteverify</code>{' '}
              with your <strong className="text-ink">secret key</strong>, then check{' '}
              <code className="text-primary">action !== &quot;block&quot;</code>.
            </p>
          </div>
        </div>

        <H3>5-minute checklist</H3>
        <Checklist
          items={[
            'Create keys in the dashboard and store the secret in a server env var (never in HTML/JS).',
            'Add the CDN script with data-site-key set to your real vp_site_… value (not the placeholder).',
            'Either mark the form with data-veilproof, or call VeilProof.getToken() and send the token to your API.',
            'On your server, read the token and POST it to /api/siteverify with X-API-Key: vp_secret_…',
            'Reject the request when success is false OR action is "block".',
            'In the dashboard, allowlist your real domain(s) before going live.',
          ]}
        />

        <H3>Site key vs secret key</H3>
        <Callout variant="danger">
          <strong>Never put <code>vp_secret_…</code> in browser code.</strong> The site key
          (<code> vp_site_…</code>) is public and belongs in HTML/JS. The secret key only runs on
          your server for <code>/api/siteverify</code>. If you pass a secret into the SDK, init fails on purpose.
        </Callout>

        <H3>Fastest path — copy this HTML</H3>
        <P>
          Paste into a page, replace the site key, point <code className="text-primary">action</code> at your
          backend, then verify <code className="text-primary">veilproof-token</code> server-side (next section).
        </P>
        <CodeBlock language="html" code={htmlCompleteSnippet()} />
        <p className="text-mute text-sm">
          Full CDN URL: <code className="text-primary">{CDN_URL}</code>
        </p>
      </Section>
    ),

    how: (
      <Section title="How It Works">
        <P>
          VeilProof is invisible bot protection: the browser SDK scores a visit, your server
          verifies the result, and you decide whether to allow the action. No CAPTCHA puzzles,
          no challenge widgets.
        </P>

        <H3>End-to-end flow</H3>
        <div className="card p-5 space-y-3 text-sm text-mute leading-relaxed">
          <p><strong className="text-ink">1. Page load</strong> — The SDK starts with your site key and quietly watches the session.</p>
          <p><strong className="text-ink">2. Token</strong> — On submit / <code className="text-primary">getToken()</code>, the SDK returns a short-lived <code className="text-primary">verification_token</code> plus an allow or block hint.</p>
          <p><strong className="text-ink">3. Your server</strong> — POST that token to <code className="text-primary">/api/siteverify</code> with your secret key. Only trust the decision after this step.</p>
          <p><strong className="text-ink">4. Your app</strong> — If <code className="text-primary">success</code> and <code className="text-primary">action !== &quot;block&quot;</code>, continue with signup / checkout / etc.</p>
        </div>

        <H3>What protection covers</H3>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="card p-5">
            <div className="font-semibold text-ink text-sm mb-2">Behavioral protection</div>
            <p className="text-mute text-sm">
              Scores how the visitor interacts with the page — timing, motion, and related
              session patterns that separate humans from scripted traffic.
            </p>
          </div>
          <div className="card p-5">
            <div className="font-semibold text-ink text-sm mb-2">Environment protection</div>
            <p className="text-mute text-sm">
              Checks for automation and inconsistent browser environments so headless or
              spoofed clients raise risk.
            </p>
          </div>
          <div className="card p-5">
            <div className="font-semibold text-ink text-sm mb-2">Request integrity</div>
            <p className="text-mute text-sm">
              Tokens are bound to a real SDK session. Hand-built or replayed predict calls
              are rejected — use the official SDK, not raw API crafting.
            </p>
          </div>
          <div className="card p-5">
            <div className="font-semibold text-ink text-sm mb-2">Network protection</div>
            <p className="text-mute text-sm">
              Server-side network context is included in risk so datacenter and suspicious
              exits can raise risk beyond what the browser alone reports.
            </p>
          </div>
        </div>

        <H3>What you get back</H3>
        <P>
          Every scored visit ends in a clear verdict. Component fields may appear in responses
          for debugging; enforce only <code className="text-primary">action</code> after siteverify.
        </P>
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead className="bg-surfaceSoft text-mute">
              <tr>
                <th className="text-left p-3 font-bold">Field</th>
                <th className="text-left p-3 font-bold">Meaning</th>
              </tr>
            </thead>
            <tbody className="text-mute">
              {[
                ['action', '"allow" or "block" — the decision your app should enforce.'],
                ['risk_score', 'Overall risk for the visit (0–100). Higher means higher risk.'],
                ['confidence', 'How decisive the verdict is for this visit.'],
                ['verification_token', 'Short-lived, single-use token for /api/siteverify.'],
              ].map(([f, m]) => (
                <tr key={f} className="border-t border-hairline">
                  <td className="p-3"><code className="text-primary">{f}</code></td>
                  <td className="p-3">{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <H3>Why siteverify exists</H3>
        <Callout variant="info">
          Anything returned only to the browser can be ignored by a bot. Use
          <code className="text-primary"> /api/siteverify</code> with your secret key so your
          backend confirms the token is real, unexpired, and not replayed before you trust allow vs block.
        </Callout>
        <P>
          <code className="text-primary">success: true</code> means the token is authentic.
          <code className="text-primary"> action</code> is the human vs bot verdict. Check both.
        </P>

        <H3>What VeilProof is not</H3>
        <ul className="list-disc list-inside text-mute text-sm space-y-2">
          <li>Not a visible CAPTCHA / image challenge / Turnstile-style widget.</li>
          <li>Not “backend config only” — the SDK must run in the browser to issue a token.</li>
          <li>Not something you integrate by hand-posting JSON to predict — use the SDK.</li>
        </ul>

        <H3>Privacy</H3>
        <P>
          The SDK sends signals needed for bot risk scoring — not your form field contents
          (email, message text, passwords). Your app still posts business fields to your own
          server separately from VeilProof.
        </P>
      </Section>
    ),

    client: (
      <Section title="Client Integration">
        <P>
          Pick <strong className="text-ink">one</strong> pattern. Mixing{' '}
          <code className="text-primary">data-veilproof</code> auto-submit with your own{' '}
          <code className="text-primary">getToken()</code> + <code className="text-primary">fetch</code> on the
          same form causes double-submit bugs.
        </P>

        <Callout variant="info">
          The browser decision is <strong>not</strong> a trust boundary. Bots can ignore it.
          Always redeem the token on your server (Server Verification).
        </Callout>

        <H3>Pattern A — classic HTML form (recommended for simple sites)</H3>
        <P>
          Zero app JS. The SDK intercepts submit, injects a hidden field named{' '}
          <code className="text-primary">veilproof-token</code>, then submits the form normally.
        </P>
        <CodeBlock language="html" code={scriptTagFormSnippet()} />
        <Callout variant="warn">
          Your server must read <code>veilproof-token</code> (with a hyphen). Looking for{' '}
          <code>veilproof_token</code> or <code>veilproofToken</code> on a classic form POST is the
          #1 &quot;Missing token&quot; mistake.
        </Callout>

        <H3>Pattern B — programmatic getToken() (SPAs / custom fetch)</H3>
        <P>
          Use this when you submit with <code className="text-primary">fetch</code> / XHR and do{' '}
          <strong className="text-ink">not</strong> put <code className="text-primary">data-veilproof</code> on the form.
        </P>
        <CodeBlock language="html" code={programmaticHtmlSnippet()} />

        <H3>Script tag attributes</H3>
        <CodeBlock language="html" code={scriptTagSnippet()} />
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead className="bg-surfaceSoft text-mute">
              <tr>
                <th className="text-left p-3 font-bold">Attribute</th>
                <th className="text-left p-3 font-bold">Required?</th>
                <th className="text-left p-3 font-bold">Meaning</th>
              </tr>
            </thead>
            <tbody className="text-mute">
              {[
                ['data-site-key', 'Yes', 'Your public vp_site_… key'],
                ['data-endpoint', 'No', `API host. Default is already ${API_HOST}`],
                ['data-debug', 'No', 'Set "true" while integrating; remove in production'],
                ['data-token-field', 'No', 'Hidden form field name. Default: veilproof-token'],
                ['async / defer', 'Recommended', 'Load without blocking page render'],
              ].map(([a, r, m]) => (
                <tr key={a} className="border-t border-hairline">
                  <td className="p-3"><code className="text-primary">{a}</code></td>
                  <td className="p-3">{r}</td>
                  <td className="p-3">{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <H3>Pattern C — npm / React / Next / Vue</H3>
        <TabbedCode tabs={[
          { label: 'Install', code: npmInstallSnippet() },
          { label: 'Vanilla JS', code: npmInitSnippet() },
          { label: 'React', code: reactSnippet() },
          { label: 'Next.js', code: nextjsSnippet() },
          { label: 'Vue 3', code: vueSnippet() },
        ]} />
        <Callout variant="info">
          In Next.js, init the SDK only in a <code>&apos;use client&apos;</code> component.
          Keep <code>VEILPROOF_SECRET_KEY</code> on the server (no <code>NEXT_PUBLIC_</code> prefix).
        </Callout>
      </Section>
    ),

    server: (
      <Section title="Server Verification (siteverify)">
        <P>
          This is the trust boundary. After the browser gets a token, your server redeems it with
          the <strong className="text-ink">secret key</strong>. Until that happens, do not create
          accounts, process payments, or accept the form.
        </P>

        <H3>Exact server checklist</H3>
        <Checklist
          items={[
            'Read the token from the request (veilproof-token for HTML forms, or the JSON field you chose).',
            `POST JSON { "token": "..." } to ${API_HOST}/api/siteverify`,
            'Send header X-API-Key: your vp_secret_… (or use the secret form field).',
            'Parse JSON even when HTTP status is 200.',
            'If success is false → reject (bad/expired/replayed token).',
            'If action === "block" → reject (bot).',
            'Only then run business logic.',
          ]}
        />

        <Callout variant="danger">
          <strong><code>success: true</code> does not mean human.</strong> It only means the token
          is genuine, unexpired, and not already redeemed. Detected bots still get{' '}
          <code>success: true</code> with <code>action: &quot;block&quot;</code>. Skipping the{' '}
          <code>action</code> check lets every detected bot through.
        </Callout>

        <H3>Copy-paste by language</H3>
        <TabbedCode tabs={[
          { label: 'curl', code: siteverifyCurlSnippet() },
          { label: 'Node / Express', code: siteverifyNodeSnippet() },
          { label: 'Python (Flask)', code: siteverifyPythonFlaskSnippet() },
          { label: 'Python (Django)', code: siteverifyPythonDjangoSnippet() },
          { label: 'PHP', code: siteverifyPhpSnippet() },
          { label: 'Java (Spring)', code: siteverifyJavaSnippet() },
          { label: 'Ruby (Rails)', code: siteverifyRubySnippet() },
          { label: 'Go', code: siteverifyGoSnippet() },
          { label: 'C# (.NET)', code: siteverifyCsharpSnippet() },
        ]} />
        <p className="text-mute text-sm">
          Prefer the language tabs over curl for production wiring — they include the{' '}
          <code className="text-primary">action === &quot;block&quot;</code> check.
        </p>

        <H3>How to read the response</H3>
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead className="bg-surfaceSoft text-mute">
              <tr>
                <th className="text-left p-3 font-bold">Field</th>
                <th className="text-left p-3 font-bold">What to do</th>
              </tr>
            </thead>
            <tbody className="text-mute">
              {[
                ['success', 'Must be true. False → missing/invalid/expired/replayed token.'],
                ['action', '"allow" or "block". Reject on "block".'],
                ['risk_score', '0–100. Optional finer control; ≥ 50 usually means block.'],
                ['hostname', 'Host the SDK reported — useful for domain audits.'],
                ['session_id', 'Debug / support correlation id.'],
                ['error-codes', 'Present when success is false (see Troubleshooting).'],
              ].map(([f, m]) => (
                <tr key={f} className="border-t border-hairline">
                  <td className="p-3"><code className="text-primary">{f}</code></td>
                  <td className="p-3">{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <H3>Token lifetime</H3>
        <P>
          Tokens are <strong className="text-ink">single-use</strong> and expire in{' '}
          <strong className="text-ink">120 seconds</strong>. Do not cache, log long-term, or retry
          the same token. A second redeem returns <code className="text-primary">timeout-or-duplicate</code>.
        </P>

        <Callout variant="warn">
          <strong>Fail-open vs fail-closed:</strong> if <code>/api/siteverify</code> is unreachable,
          choose deliberately — fail-open (better UX) or fail-closed (safer). Document the choice
          for your team.
        </Callout>
      </Section>
    ),

    api: (
      <Section title="API Reference">
        <EndpointCard method="POST" path="/api/siteverify" auth="Secret key (X-API-Key header or `secret` form field)">
          <div className="space-y-3">
            <p className="text-mute text-sm">
              Body: JSON <code className="text-primary">{'{ "token": "..." }'}</code> or form fields{' '}
              <code className="text-primary">secret</code> + <code className="text-primary">response</code>.
              Failures often still return HTTP 200 — always inspect <code className="text-primary">success</code>.
            </p>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Allowed visitor</h4>
              <CodeBlock code={siteverifySuccessResponse} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">
                Detected bot (still <code className="text-primary">success: true</code>)
              </h4>
              <CodeBlock code={siteverifyBlockedResponse} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Invalid / expired / replayed token</h4>
              <CodeBlock code={siteverifyErrorResponse} />
            </div>
          </div>
        </EndpointCard>

        <EndpointCard method="POST" path="/api/predict" auth="Site key (SDK-internal — do not call yourself)">
          <div className="space-y-3">
            <p className="text-mute text-sm">
              The SDK calls this automatically (with request signing). You only need the resulting{' '}
              <code className="text-primary">verification_token</code> for siteverify.
            </p>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Allow</h4>
              <CodeBlock code={predictAllowResponse} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Block</h4>
              <CodeBlock code={predictBlockResponse} />
            </div>
            <table className="w-full text-sm mt-2">
              <thead className="bg-surfaceSoft text-mute">
                <tr><th className="text-left p-2 font-bold">Field</th><th className="text-left p-2 font-bold">Meaning</th></tr>
              </thead>
              <tbody className="text-mute">
                {[
                  ['action', '"allow" or "block" — enforce this after siteverify.'],
                  ['risk_score', 'Overall risk 0–100. Higher means higher risk.'],
                  ['behavior_score', 'Behavioral risk component (0–100).'],
                  ['fingerprint_score', 'Environment / automation risk component (0–100).'],
                  ['confidence', 'How decisive the verdict is for this visit.'],
                  ['verification_token', 'Short-lived, single-use token for /api/siteverify.'],
                ].map(([f, m]) => (
                  <tr key={f} className="border-t border-hairline">
                    <td className="p-2"><code className="text-primary">{f}</code></td>
                    <td className="p-2">{m}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </EndpointCard>
      </Section>
    ),

    security: (
      <Section title="Security">
        <Callout variant="danger">
          <strong>Secret keys never touch the browser.</strong> Store{' '}
          <code>VEILPROOF_SECRET_KEY</code> like a payment API key.
        </Callout>
        <Callout variant="info">
          Site keys are public by design. Env vars like <code>NEXT_PUBLIC_*</code> /{' '}
          <code>VITE_*</code> are for config hygiene, not secrecy.
        </Callout>
        <H3>Allowlist domains</H3>
        <P>
          In the dashboard, open your project and use the <strong className="text-ink">Allowed domains</strong> box.
          Enter hostnames separated by commas, for example{' '}
          <code className="text-primary">example.com, www.example.com, localhost</code>.
          Leave empty to allow any domain while testing. Subdomains of a listed host are included automatically.
        </P>
        <H3>Tokens</H3>
        <P>Single-use, 120s TTL. Do not store beyond the verify call.</P>
        <H3>Content-Security-Policy</H3>
        <P>If you use CSP, allow the CDN script and API host:</P>
        <CodeBlock code={`Content-Security-Policy: script-src 'self' https://cdn.jsdelivr.net; connect-src 'self' https://api.veilproof.tech;`} />
      </Section>
    ),

    sdk: (
      <Section title="SDK Reference">
        <P>
          Package: <a className="text-primary underline" href="https://www.npmjs.com/package/veilproof" target="_blank" rel="noreferrer">veilproof on npm</a>.
          Pin <code className="text-primary">1.1.10</code> (or newer) in production.
        </P>
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead className="bg-surfaceSoft text-mute">
              <tr><th className="text-left p-3 font-bold">Method</th><th className="text-left p-3 font-bold">Purpose</th></tr>
            </thead>
            <tbody className="text-mute">
              {[
                ['VeilProof.init(config)', 'Initialize with site key (auto from script-tag data-site-key)'],
                ['VeilProof.getToken(cb?)', 'Get verification token — callback or Promise'],
                ['VeilProof.getDecision(cb)', 'Raw predict result (used inside getToken)'],
                ['VeilProof.getSessionId()', 'Current session id'],
                ['VeilProof.selfTest(cb)', 'Diagnose init / network / event collection'],
                ['VeilProof.destroy()', 'Stop tracking and flush'],
              ].map(([m, d]) => (
                <tr key={m} className="border-t border-hairline">
                  <td className="p-3 font-mono text-primary">{m}</td>
                  <td className="p-3">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <H3>selfTest()</H3>
        <CodeBlock code={`VeilProof.selfTest((results) => console.log(results));\n// { tests: [...], passed, failed, overall }`} />
        <p className="text-mute text-xs">CDN: <code className="text-primary">{CDN_URL}</code></p>
      </Section>
    ),

    help: (
      <Section title="Troubleshooting">
        <P>Most integration failures are one of the issues below. Fix in order.</P>

        <Mistake title="Missing token / 400 on my server">
          Classic <code className="text-primary">data-veilproof</code> forms post{' '}
          <code className="text-primary">veilproof-token</code> (hyphen). If you read{' '}
          <code className="text-primary">veilproofToken</code> or <code className="text-primary">veilproof_token</code>{' '}
          from a normal form POST, it will be empty. JSON <code className="text-primary">fetch</code> bodies
          use whatever field name you chose in your client code.
        </Mistake>

        <Mistake title="success: true but bots still get in">
          You verified the token but did not check <code className="text-primary">action === &quot;block&quot;</code>.
          Add that check before business logic.
        </Mistake>

        <Mistake title="window.VeilProof is undefined">
          Script blocked by CSP, wrong CDN URL, or your submit handler ran before the script loaded.
          Wait for load, allow <code className="text-primary">cdn.jsdelivr.net</code> in{' '}
          <code className="text-primary">script-src</code>, and confirm Network shows HTTP 200 for the SDK.
        </Mistake>

        <Mistake title="SDK init error / refuses key">
          You passed a <code className="text-primary">vp_secret_…</code> into the browser. Use{' '}
          <code className="text-primary">vp_site_…</code> only in the client.
        </Mistake>

        <Mistake title="401 request signing / signing_required">
          Predict requires the official SDK (it signs requests). Do not POST handmade JSON to{' '}
          <code className="text-primary">/api/predict</code> from your own code. Always use{' '}
          <code className="text-primary">getToken()</code> or <code className="text-primary">data-veilproof</code>.
        </Mistake>

        <Mistake title="timeout-or-duplicate">
          Token already redeemed or older than 120 seconds. Call <code className="text-primary">getToken()</code>{' '}
          again for a fresh token; never reuse one.
        </Mistake>

        <Mistake title="invalid-input-secret">
          Wrong or truncated secret key, or you sent the site key instead of the secret to siteverify.
          Confirm <code className="text-primary">X-API-Key</code> starts with <code className="text-primary">vp_secret_</code>.
        </Mistake>

        <Mistake title="Works on localhost, fails in production">
          Add your production domain in the dashboard allowlist. Also update CSP{' '}
          <code className="text-primary">connect-src</code> to include{' '}
          <code className="text-primary">{API_HOST}</code>.
        </Mistake>

        <Mistake title="Form submits twice / races">
          Do not combine <code className="text-primary">data-veilproof</code> with a custom{' '}
          <code className="text-primary">getToken()</code> + <code className="text-primary">fetch</code> handler
          on the same form. Pick Pattern A or Pattern B.
        </Mistake>

        <H3>Quick diagnosis</H3>
        <CodeBlock code={`// In the browser console after the SDK loads:\nVeilProof.selfTest((r) => console.log(r));`} />
        <Callout variant="info">
          Still stuck? Open the dashboard, confirm keys + allowed domains, and compare your flow
          to Getting Started → Fastest path HTML + Server Verification → Node example.
        </Callout>
      </Section>
    ),
  };

  return (
    <div className="interior-shell min-h-screen bg-canvas text-ink">
      <SiteNav active="Docs" />

      <div className="docs-layout max-w-[1280px] mx-auto px-6 py-10 grid md:grid-cols-4 gap-8">
        <aside className="docs-sidebar md:col-span-1 space-y-1">
          {NAV.map(({ id, title, icon: Icon }) => (
            <button
              key={id}
              onClick={() => selectSection(id)}
              aria-current={active === id ? 'page' : undefined}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-sm text-left text-sm font-semibold transition-colors ${
                active === id ? 'bg-white/10 text-ink' : 'text-mute hover:bg-surface'
              }`}
            >
              <Icon className="w-4 h-4" />
              {title}
            </button>
          ))}
        </aside>

        <main id={active} className="md:col-span-3 card p-8 docs-content">
          {content[active]}
        </main>
      </div>

      <SiteFooter />
    </div>
  );
}
