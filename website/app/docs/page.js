'use client';

import { useState } from 'react';
import { Shield, Rocket, Code, Server, Layers, ShieldCheck, BookOpen, ArrowLeft } from 'lucide-react';
import CodeBlock from '../../components/docs/CodeBlock';
import TabbedCode from '../../components/docs/TabbedCode';
import Callout from '../../components/docs/Callout';
import EndpointCard from '../../components/docs/EndpointCard';
import {
  scriptTagSnippet, scriptTagFormSnippet, npmInstallSnippet, npmInitSnippet,
  reactSnippet, nextjsSnippet, vueSnippet,
  siteverifyCurlSnippet, siteverifyNodeSnippet, siteverifyPythonFlaskSnippet,
  siteverifyPythonDjangoSnippet, siteverifyPhpSnippet,
  siteverifySuccessResponse, siteverifyErrorResponse, CDN_URL,
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
      <h2 className="text-3xl font-bold">{title}</h2>
      {children}
    </div>
  );
}

function H3({ children }) {
  return <h3 className="text-xl font-semibold mt-8 mb-3">{children}</h3>;
}

function P({ children }) {
  return <p className="text-textSecondary leading-relaxed">{children}</p>;
}

export default function DocsPage() {
  const [active, setActive] = useState('start');

  const content = {
    start: (
      <Section title="Getting Started">
        <P>
          VeriFlow is an invisible bot-detection layer: a browser SDK collects
          behavioral signals (mouse, keyboard, scroll), your customer's server
          decides who to trust — not the browser. Three steps to integrate:
        </P>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-surface p-6 rounded-xl border border-border">
            <div className="text-primary font-bold text-lg mb-2">1. Get keys</div>
            <p className="text-textSecondary text-sm">Create a project in the dashboard — you get a <strong className="text-text">site key</strong> (browser) and a <strong className="text-text">secret key</strong> (server), always as a pair.</p>
          </div>
          <div className="bg-surface p-6 rounded-xl border border-border">
            <div className="text-primary font-bold text-lg mb-2">2. Drop in the script</div>
            <p className="text-textSecondary text-sm">Add one script tag (or <code className="text-accent">npm install</code>) with your site key. No JS required for plain HTML forms.</p>
          </div>
          <div className="bg-surface p-6 rounded-xl border border-border">
            <div className="text-primary font-bold text-lg mb-2">3. Verify server-side</div>
            <p className="text-textSecondary text-sm">Your server redeems the token with your secret key at <code className="text-accent">/api/siteverify</code> before trusting the request.</p>
          </div>
        </div>

        <H3>Site key vs. secret key</H3>
        <Callout variant="danger">
          <strong>Never put your secret key in browser code.</strong> The site
          key (<code>vf_site_...</code>) is public — it's meant to sit in your
          HTML/JS. The secret key (<code>vf_secret_...</code>) only ever runs
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
        <P>Zero JS required. Auto-initializes from <code className="text-accent">data-site-key</code>:</P>
        <CodeBlock language="html" code={scriptTagSnippet()} />
        <p className="text-textSecondary text-sm">Add <code className="text-accent">data-debug=&quot;true&quot;</code> for console logging, or <code className="text-accent">data-endpoint</code> to override the API host.</p>

        <H3>Classic HTML form — no JS at all</H3>
        <P>Add <code className="text-accent">data-veriflow</code> to any form — the SDK injects a hidden token field before it submits:</P>
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
          the browser received with your <strong className="text-text">secret key</strong> —
          only then is the decision trustworthy.
        </P>
        <TabbedCode tabs={[
          { label: 'curl', code: siteverifyCurlSnippet() },
          { label: 'Node / Express', code: siteverifyNodeSnippet() },
          { label: 'Python (Flask)', code: siteverifyPythonFlaskSnippet() },
          { label: 'Python (Django)', code: siteverifyPythonDjangoSnippet() },
          { label: 'PHP', code: siteverifyPhpSnippet() },
        ]} />

        <H3>Interpreting the result</H3>
        <P>
          Check <code className="text-accent">action</code> (<code className="text-accent">allow</code> / <code className="text-accent">block</code>) and
          <code className="text-accent"> risk_score</code> (0-100). Most integrations trust <code className="text-accent">action</code> directly;
          if you want finer control, threshold on <code className="text-accent">risk_score</code> yourself.
        </P>
        <Callout variant="warn">
          <strong>Fail-open vs. fail-closed:</strong> if <code>/api/siteverify</code> is
          unreachable, decide deliberately whether to let the request through
          (fail-open — better UX, worse security) or block it (fail-closed —
          the SDK itself fails closed on <code>/api/predict</code> errors).
        </Callout>

        <H3>Tokens are single-use and expire in 120 seconds</H3>
        <P>A replayed or expired token returns <code className="text-accent">timeout-or-duplicate</code>. Don't cache or retry a token across requests.</P>
      </Section>
    ),

    api: (
      <Section title="API Reference">
        <EndpointCard method="POST" path="/api/siteverify" auth="Secret key (X-API-Key header or `secret` form field)">
          <div className="space-y-3">
            <p className="text-textSecondary text-sm">Accepts JSON <code className="text-accent">{'{ "token": "..." }'}</code> or classic form-encoded <code className="text-accent">secret=...&amp;response=...</code> (reCAPTCHA-compatible). Failures return HTTP 200 — check <code className="text-accent">success</code>, not the status code.</p>
            <div>
              <h4 className="font-semibold text-sm text-textSecondary mb-1">Success response</h4>
              <CodeBlock code={siteverifySuccessResponse} />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-textSecondary mb-1">Error response</h4>
              <CodeBlock code={siteverifyErrorResponse} />
              <p className="text-textSecondary text-xs mt-2">Codes: <code className="text-accent">missing-input-secret</code>, <code className="text-accent">invalid-input-secret</code>, <code className="text-accent">missing-input-response</code>, <code className="text-accent">invalid-input-response</code>, <code className="text-accent">timeout-or-duplicate</code>.</p>
            </div>
          </div>
        </EndpointCard>

        <EndpointCard method="POST" path="/api/predict" auth="Site key (SDK-internal)">
          <p className="text-textSecondary text-sm">Called automatically by the SDK — you shouldn't call this directly. Returns the risk decision plus a <code className="text-accent">verification_token</code> for <code className="text-accent">/api/siteverify</code>.</p>
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
        <P>If you set a CSP, allow the SDK's origin in <code className="text-accent">connect-src</code>:</P>
        <CodeBlock code={`Content-Security-Policy: connect-src 'self' https://next-captcha-sdk.onrender.com; script-src 'self' https://cdn.jsdelivr.net;`} />
      </Section>
    ),

    sdk: (
      <Section title="SDK Reference">
        <P>Full method list — see the <a className="text-primary underline" href="https://www.npmjs.com/package/veriflow-sdk" target="_blank" rel="noreferrer">npm README</a> for details.</P>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border border-border rounded-xl overflow-hidden">
            <thead className="bg-surface2 text-textSecondary">
              <tr><th className="text-left p-3">Method</th><th className="text-left p-3">Purpose</th></tr>
            </thead>
            <tbody className="text-textSecondary">
              {[
                ['VeriFlow.init(config)', 'Initialize with your site key (auto-called by script-tag)'],
                ['VeriFlow.getToken(callback?)', 'Get a verification token — callback or Promise'],
                ['VeriFlow.getDecision(callback)', 'Raw decision result (used internally by getToken)'],
                ['VeriFlow.getSessionId()', 'Current session ID'],
                ['VeriFlow.selfTest(callback)', 'Diagnose init/network/event-collection issues'],
                ['VeriFlow.destroy()', 'Stop tracking and flush remaining events'],
              ].map(([m, d]) => (
                <tr key={m} className="border-t border-border">
                  <td className="p-3 font-mono text-accent">{m}</td>
                  <td className="p-3">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <H3>Troubleshooting with selfTest()</H3>
        <CodeBlock code={`VeriFlow.selfTest((results) => console.log(results));\n// { tests: [...], passed, failed, overall }`} />
        <p className="text-textSecondary text-xs">CDN: <code className="text-accent">{CDN_URL}</code></p>
      </Section>
    ),
  };

  return (
    <div className="min-h-screen bg-background text-text">
      <header className="border-b border-border bg-surface sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.location.href = '/'}>
            <Shield className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold">VeriFlow Docs</span>
          </div>
          <button
            onClick={() => window.location.href = '/'}
            className="flex items-center gap-2 text-sm text-textSecondary hover:text-text transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-10 grid md:grid-cols-4 gap-8">
        <aside className="md:col-span-1 space-y-2">
          {NAV.map(({ id, title, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left text-sm font-medium transition-all ${
                active === id ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-textSecondary hover:bg-surface'
              }`}
            >
              <Icon className="w-5 h-5" />
              {title}
            </button>
          ))}
        </aside>

        <main className="md:col-span-3 bg-surface border border-border rounded-2xl p-8 shadow-xl">
          {content[active]}
        </main>
      </div>
    </div>
  );
}
