'use client';

import {
  ArrowRight,
  Bot,
  BrainCircuit,
  ChevronRight,
  Code2,
  Fingerprint,
  Gauge,
  ShieldCheck,
  Sparkles,
  Workflow,
  Zap,
} from 'lucide-react';
import SiteNav from '../components/chrome/SiteNav';
import SiteSearch from '../components/chrome/SiteSearch';

const DETECTION_ROWS = [
  { icon: Fingerprint, title: 'Behavioral Intelligence', meta: 'Silent verification', tags: ['invisible', 'real-time'], href: '/docs#security' },
  { icon: BrainCircuit, title: 'Adaptive Risk Engine', meta: 'ML-powered scoring', tags: ['AI', '+4'], href: '/docs#api' },
];

const DEVELOPER_ROWS = [
  { icon: Code2, title: 'Client SDK', meta: 'Install in minutes', count: '5 frameworks', href: '/docs#client' },
  { icon: Workflow, title: 'Server Verification', meta: 'One secure endpoint', count: '9 languages', href: '/docs#server' },
];

export default function LandingPage() {
  return (
    <main className="vp-home">
      <div className="vp-aurora" aria-hidden="true" />
      <div className="vp-network" aria-hidden="true">
        {Array.from({ length: 22 }).map((_, index) => <i key={index} />)}
      </div>

      <SiteNav />

      <section className="vp-hero">
        <div className="vp-eyebrow"><span /> INTELLIGENCE FOR THE MODERN WEB</div>
        <h1>Bot protection<br />people never notice.</h1>
        <p>
          Tired of making real people prove they're human? VeilProof does it for you — silently,
          invisibly, in the background. No puzzles. No &quot;click the traffic lights.&quot; No
          annoyed users bouncing off your signup page.
          <strong>Just clean, bot-free traffic — without anyone ever knowing it's there.</strong>
        </p>

        <SiteSearch variant="hero" placeholder="Search docs, SDKs, integrations..." />

        <div className="vp-quick-links">
          <span>Popular:</span>
          <a href="/docs#start">Quick start</a>
          <a href="/docs#client">React SDK</a>
          <a href="/docs#api">API reference</a>
        </div>
      </section>

      <section className="vp-showcase" id="features">
        <div className="vp-showcase-art">
          <div className="vp-orbit vp-orbit-one" />
          <div className="vp-orbit vp-orbit-two" />
          <div className="vp-shield-core">
            <img src="/veilproof-mark.png" alt="VeilProof" className="vp-shield-logo" />
          </div>
          <span className="vp-float-dot dot-one" />
          <span className="vp-float-dot dot-two" />
          <span className="vp-float-dot dot-three" />
        </div>
        <div className="vp-showcase-copy">
          <span className="vp-kicker"><Sparkles size={14} /> Introducing VeilProof Intelligence</span>
          <h2>Security that thinks<br />at human speed.</h2>
          <p>Analyze thousands of behavioral signals, stop sophisticated bots, and let trusted visitors pass—without a single puzzle.</p>
          <a href="/docs#security">Explore the platform <ArrowRight /></a>
        </div>
        <div className="vp-score-card">
          <div className="vp-score-head"><span>Live risk analysis</span><span className="vp-live"><i /> LIVE</span></div>
          <div className="vp-score-value">08<span>/100</span></div>
          <div className="vp-score-bar"><i /></div>
          <div className="vp-score-result"><ShieldCheck /> Human session verified</div>
          <div className="vp-signal-grid">
            <span><Gauge /> 42ms</span>
            <span><Zap /> Passive</span>
            <span><Bot /> Blocked</span>
          </div>
        </div>
      </section>

      <section className="vp-catalog" id="platform">
        <CatalogColumn
          title="Protect every interaction"
          subtitle="Real-time intelligence, zero user friction"
          icon={ShieldCheck}
          rows={DETECTION_ROWS}
        />
        <CatalogColumn
          title="Built for developers"
          subtitle="Ship production-ready protection fast"
          icon={Code2}
          rows={DEVELOPER_ROWS}
        />
      </section>
    </main>
  );
}

function CatalogColumn({ title, subtitle, icon: Icon, rows }) {
  return (
    <div className="vp-catalog-column">
      <div className="vp-section-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <Icon />
      </div>
      <div className="vp-product-list">
        {rows.map(({ icon: RowIcon, title: rowTitle, meta, tags, count, href }) => (
          <a href={href} className="vp-product-row" key={rowTitle}>
            <span className="vp-product-icon"><RowIcon /></span>
            <span className="vp-product-name"><strong>{rowTitle}</strong><small>{meta}</small></span>
            {tags && <span className="vp-tags">{tags.map((tag) => <i key={tag}>{tag}</i>)}</span>}
            {count && <span className="vp-count">{count}</span>}
            <ChevronRight className="vp-chevron" />
          </a>
        ))}
      </div>
    </div>
  );
}
