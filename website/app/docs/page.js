'use client';

import { useEffect, useState } from 'react';
import { Rocket, Code, Server, Layers, ShieldCheck, BookOpen } from 'lucide-react';
import SiteNav from '../../components/chrome/SiteNav';
import SiteFooter from '../../components/chrome/SiteFooter';
import CodeBlock from '../../components/docs/CodeBlock';
import TabbedCode from '../../components/docs/TabbedCode';
import Callout from '../../components/docs/Callout';
import EndpointCard from '../../components/docs/EndpointCard';
import {
  scriptTagSnippet, scriptTagFormSnippet, npmInstallSnippet, npmInitSnippet,
  reactSnippet, nextjsSnippet, vueSnippet,
  siteverifyCurlSnippet, siteverifyNodeSnippet, siteverifyPythonFlaskSnippet,
  siteverifyPythonDjangoSnippet, siteverifyPhpSnippet,
  siteverifyJavaSnippet, siteverifyRubySnippet, siteverifyGoSnippet, siteverifyCsharpSnippet,
  siteverifySuccessResponse, siteverifyBlockedResponse, siteverifyErrorResponse,
  predictAllowResponse, predictBlockResponse, CDN_URL,
} from '../../components/docs/docSnippets';

const NAV = [
  { id: 'start', title: 'Getting Started', icon: Rocket },
  { id: 'client', title: 'Client Integration', icon: Code },
  { id: 'server', title: 'Server Verification', icon: Server },
  { id: 'api', title: 'API Reference', icon: Layers },
  { id: 'security', title: 'Security Best Practices', icon: ShieldCheck },
  { id: 'sdk', title: 'SDK Reference', icon: BookOpen },
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
          VeilProof is an invisible bot-detection layer: a browser SDK collects
          behavioral signals, your customer's server decides who to trust —
          not the browser. Three steps to integrate:
        </P>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="card p-5">
            <div className="text-primary font-bold text-sm uppercase tracking-wide mb-2">1. Get keys</div>
            <p className="text-mute text-sm">Create a project in the dashboard — you get a <strong className="text-ink">site key</strong> (browser) and a <strong className="text-ink">secret key</strong> (server), always as a pair.</p>
          </div>
          <div className="card p-5">
            <div className="text-primary font-bold text-sm uppercase tracking-wide mb-2">2. Drop in the script</div>
            <p className="text-mute text-sm">Add one script tag (or <code className="text-primary">npm install</code>) with your site key. No JS required for plain HTML forms.</p>
          </div>
          <div className="card p-5">
            <div className="text-primary font-bold text-sm uppercase tracking-wide mb-2">3. Verify server-side</div>
            <p className="text-mute text-sm">Your server redeems the token with your secret key at <code className="text-primary">/api/siteverify</code> before trusting the request.</p>
          </div>
        </div>

        <H3>Site key vs. secret key</H3>
        <Callout variant="danger">
          <strong>Never put your secret key in browser code.</strong> The site
          key (<code>vp_site_...</code>) is public — it's meant to sit in your
          HTML/JS. The secret key (<code>vp_secret_...</code>) only ever runs
          on your server, to call <code>/api/siteverify</code>. The SDK
          refuses to initialize with a secret key.
        </Callout>

        <H3>Quick start</H3>
        <CodeBlock language="html" code={scriptTagSnippet()} />
      </Section>
    ),

    client: (
      <Section title="Client Integration">
        <P>
          The browser's decision is not a trust boundary — a bot can ignore or
          fake it. The SDK's job is only to collect signals and hand you a
          short-lived token; verification happens on your server (next section).
        </P>

        <H3>Script tag — any HTML site (WordPress, Django templates, Rails views...)</H3>
        <P>Zero JS required. Auto-initializes from <code className="text-primary">data-site-key</code>:</P>
        <CodeBlock language="html" code={scriptTagSnippet()} />
        <p className="text-mute text-sm">Add <code className="text-primary">data-debug=&quot;true&quot;</code> for console logging, or <code className="text-primary">data-endpoint</code> to override the API host.</p>

        <H3>Classic HTML form — no JS at all</H3>
        <P>Add <code className="text-primary">data-veilproof</code> to any form — the SDK injects a hidden token field before it submits:</P>
        <CodeBlock language="html" code={scriptTagFormSnippet()} />

        <H3>npm / ESM (React, Vue, Next.js)</H3>
        <TabbedCode tabs={[
          { label: 'Install', code: npmInstallSnippet() },
          { label: 'Vanilla JS', code: npmInitSnippet() },
          { label: 'React', code: reactSnippet() },
          { label: 'Next.js (App Router)', code: nextjsSnippet() },
          { label: 'Vue 3', code: vueSnippet() },
        ]} />
      </Section>
    ),

    server: (
      <Section title="Server Verification (siteverify)">
        <P>
          This is the actual trust boundary. Your server redeems the token
          the browser received with your <strong className="text-ink">secret key</strong> —
          only then is the decision trustworthy.
        </P>
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
          The <code className="text-primary">curl</code> tab only shows the request —
          it can't check the response for you. Every other tab shows the full
          pattern, including the <code className="text-primary">action</code> check below.
          Don't wire up your own handler from the curl example alone.
        </p>

        <H3>Interpreting the result</H3>
        <Callout variant="danger">
          <strong><code>success: true</code> does not mean the visitor is human.</strong> It
          only means the token is genuine, unexpired, and hasn't been redeemed
          before — the same way a valid-but-expired coupon code is still a
          &quot;real&quot; code. A detected bot is still issued a validly-signed
          token; <code>/api/siteverify</code> will happily return
          <code> success: true</code> for it. You must check
          <code className="text-primary"> action !== &apos;block&apos;</code> yourself,
          every time, before trusting the request. Skipping this check means
          every bot VeilProof detects gets through anyway.
        </Callout>
        <P>
          Check <code className="text-primary">action</code> (<code className="text-primary">allow</code> / <code className="text-primary">block</code>) and
          <code className="text-primary"> risk_score</code> (0-100). Most integrations trust <code className="text-primary">action</code> directly;
          if you want finer control, threshold on <code className="text-primary">risk_score</code> yourself.
        </P>
        <Callout variant="warn">
          <strong>Fail-open vs. fail-closed:</strong> if <code>/api/siteverify</code> is
          unreachable, decide deliberately whether to let the request through
          (fail-open — better UX, worse security) or block it (fail-closed —
          the SDK itself fails closed on <code>/api/predict</code> errors).
        </Callout>

        <H3>Tokens are single-use and expire in 120 seconds</H3>
        <P>A replayed or expired token returns <code className="text-primary">timeout-or-duplicate</code>. Don't cache or retry a token across requests.</P>
      </Section>
    ),

    api: (
      <Section title="API Reference">
        <EndpointCard method="POST" path="/api/siteverify" auth="Secret key (X-API-Key header or `secret` form field)">
          <div className="space-y-3">
            <p className="text-mute text-sm">Accepts JSON <code className="text-primary">{'{ "token": "..." }'}</code> or classic form-encoded <code className="text-primary">secret=...&amp;response=...</code>. Failures return HTTP 200 — check <code className="text-primary">success</code>, not the status code.</p>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Success response — visitor allowed</h4>
              <CodeBlock code={siteverifySuccessResponse} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Success response — bot blocked (note: still <code className="text-primary">success: true</code>)</h4>
              <CodeBlock code={siteverifyBlockedResponse} />
              <p className="text-mute text-xs mt-2">
                This is the response for a bot VeilProof correctly detected. <code className="text-primary">success</code> is
                still <code className="text-primary">true</code> — only <code className="text-primary">action</code> tells
                you it was blocked. See the danger callout in Server Verification.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Error response — invalid or expired token</h4>
              <CodeBlock code={siteverifyErrorResponse} />
              <p className="text-mute text-xs mt-2">Codes: <code className="text-primary">missing-input-secret</code>, <code className="text-primary">invalid-input-secret</code>, <code className="text-primary">missing-input-response</code>, <code className="text-primary">invalid-input-response</code>, <code className="text-primary">timeout-or-duplicate</code>.</p>
            </div>
          </div>
        </EndpointCard>

        <EndpointCard method="POST" path="/api/predict" auth="Site key (SDK-internal)">
          <div className="space-y-3">
            <p className="text-mute text-sm">Called automatically by the SDK — you shouldn't call this directly. Returns the risk decision plus a <code className="text-primary">verification_token</code> for <code className="text-primary">/api/siteverify</code>.</p>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Response — visitor allowed</h4>
              <CodeBlock code={predictAllowResponse} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-mute mb-1">Response — bot blocked</h4>
              <CodeBlock code={predictBlockResponse} />
            </div>
            <table className="w-full text-sm mt-2">
              <thead className="bg-surfaceSoft text-mute">
                <tr><th className="text-left p-2 font-bold">Field</th><th className="text-left p-2 font-bold">Meaning</th></tr>
              </thead>
              <tbody className="text-mute">
                {[
                  ['action', '"allow" or "block" — the verdict. Binary only; there is no "challenge" state.'],
                  ['risk_score', '0–100 combined risk score. ≥ 50 blocks.'],
                  ['behavior_score', "0–100, VeilProof's behavioral risk signal."],
                  ['fingerprint_score', "0–100, VeilProof's device/environment risk signal."],
                  ['confidence', '0–1, how far risk_score sits from the 50-point decision boundary — not a statistical confidence interval.'],
                  ['verification_token', 'Short-lived (120s), single-use token to redeem at /api/siteverify.'],
                ].map(([f, m]) => (
                  <tr key={f} className="border-t border-hairline">
                    <td className="p-2"><code className="text-primary">{f}</code></td>
                    <td className="p-2">{m}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-mute text-xs">
              <code className="text-primary">risk_score</code> combines multiple independent
              signals into one number — check <code className="text-primary">action</code> for
              the verdict, or threshold on <code className="text-primary">risk_score</code>
              yourself for finer control.
            </p>
          </div>
        </EndpointCard>
      </Section>
    ),

    security: (
      <Section title="Security Best Practices">
        <Callout variant="danger">
          <strong>Secret keys never touch the browser.</strong> Store them as
          a server-side environment variable, same as a payment API key.
        </Callout>
        <Callout variant="info">
          <strong>Site keys are not secret</strong> — they ship in the
          browser bundle no matter where you read them from. The examples in
          this guide read the site key from an env var (<code>NEXT_PUBLIC_*</code>,
          <code> VITE_*</code>, etc.) purely for config hygiene — one place to
          rotate it, no accidental commits of a stale key — not because it
          hides the value from users. Don't let that convention create a
          false sense of security about the site key; the actual security
          boundary is the secret key never appearing in client code, plus
          allowed-domain restrictions below.
        </Callout>
        <H3>Restrict allowed domains</H3>
        <P>Set your project's allowed domains in the dashboard — a leaked site key only works from domains you configured.</P>
        <H3>Tokens: replay and TTL</H3>
        <P>Verification tokens are single-use and expire after 120 seconds. Don't log or store them beyond the verification call.</P>
        <H3>Content-Security-Policy</H3>
        <P>If you set a CSP, allow the SDK's origin in <code className="text-primary">connect-src</code>:</P>
        <CodeBlock code={`Content-Security-Policy: connect-src 'self' https://api.veilproof.tech; script-src 'self' https://cdn.jsdelivr.net;`} />
      </Section>
    ),

    sdk: (
      <Section title="SDK Reference">
        <P>Full method list — see the <a className="text-primary underline" href="https://www.npmjs.com/package/veilproof" target="_blank" rel="noreferrer">npm README</a> for details.</P>
        <div className="overflow-x-auto card">
          <table className="w-full text-sm">
            <thead className="bg-surfaceSoft text-mute">
              <tr><th className="text-left p-3 font-bold">Method</th><th className="text-left p-3 font-bold">Purpose</th></tr>
            </thead>
            <tbody className="text-mute">
              {[
                ['VeilProof.init(config)', 'Initialize with your site key (auto-called by script-tag)'],
                ['VeilProof.getToken(callback?)', 'Get a verification token — callback or Promise'],
                ['VeilProof.getDecision(callback)', 'Raw decision result (used internally by getToken)'],
                ['VeilProof.getSessionId()', 'Current session ID'],
                ['VeilProof.selfTest(callback)', 'Diagnose init/network/event-collection issues'],
                ['VeilProof.destroy()', 'Stop tracking and flush remaining events'],
              ].map(([m, d]) => (
                <tr key={m} className="border-t border-hairline">
                  <td className="p-3 font-mono text-primary">{m}</td>
                  <td className="p-3">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <H3>Troubleshooting with selfTest()</H3>
        <CodeBlock code={`VeilProof.selfTest((results) => console.log(results));\n// { tests: [...], passed, failed, overall }`} />
        <p className="text-mute text-xs">CDN: <code className="text-primary">{CDN_URL}</code></p>
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
