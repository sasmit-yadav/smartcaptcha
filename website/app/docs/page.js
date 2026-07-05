'use client';

import { useState } from 'react';
import { Shield, BookOpen, Code, Terminal, Layers, ArrowLeft, Copy, Check } from 'lucide-react';

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState('intro');
  const [copiedText, setCopiedText] = useState('');

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedText(id);
    setTimeout(() => setCopiedText(''), 2000);
  };

  const sections = {
    intro: {
      title: 'Introduction',
      icon: BookOpen,
      content: (
        <div className="space-y-6">
          <p className="text-textSecondary leading-relaxed">
            NextCaptcha is a next-generation, invisible bot detection system. Unlike legacy CAPTCHAs that force users to solve frustrating puzzles, NextCaptcha uses advanced behavioral telemetry and a multi-factor machine learning risk engine to verify traffic invisibly and in real-time.
          </p>
          
          <h3 className="text-xl font-semibold mt-8 mb-4">How it works</h3>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-surface p-6 rounded-xl border border-border">
              <div className="text-primary font-bold text-lg mb-2">1. Collect</div>
              <p className="text-textSecondary text-sm">
                The lightweight client SDK runs silently in the background, collecting micro-behavioral signals (mouse velocity, scroll acceleration, key intervals, and hardware fingerprints).
              </p>
            </div>
            <div className="bg-surface p-6 rounded-xl border border-border">
              <div className="text-primary font-bold text-lg mb-2">2. Analyze</div>
              <p className="text-textSecondary text-sm">
                Telemetry features are transmitted to our hosted ML prediction backend. Our models evaluate behavioral signatures against patterns of human vs. automated traffic.
              </p>
            </div>
            <div className="bg-surface p-6 rounded-xl border border-border">
              <div className="text-primary font-bold text-lg mb-2">3. Decide</div>
              <p className="text-textSecondary text-sm">
                The risk engine calculates an overall score (0-100) and returns an action recommendation (<code className="text-accent">allow</code>, <code className="text-yellow-500">challenge</code>, or <code className="text-red-500">block</code>).
              </p>
            </div>
          </div>
        </div>
      )
    },
    npm: {
      title: 'NPM SDK Integration',
      icon: Code,
      content: (
        <div className="space-y-6">
          <p className="text-textSecondary leading-relaxed">
            For modern single-page applications (React, Next.js, Vue, Svelte) and projects utilizing bundlers, utilize our official NPM package to aggregate telemetry and fetch decisions.
          </p>
          
          <h3 className="text-xl font-semibold mt-6 mb-2">1. Installation</h3>
          <div className="relative">
            <pre className="bg-surface p-4 rounded-xl font-mono text-sm overflow-x-auto text-accent border border-border">
              <code>npm install nextcaptcha-sdk</code>
            </pre>
            <button 
              onClick={() => copyToClipboard('npm install nextcaptcha-sdk', 'npm-install')}
              className="absolute right-4 top-4 text-textSecondary hover:text-text transition-colors"
            >
              {copiedText === 'npm-install' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <h3 className="text-xl font-semibold mt-8 mb-2">2. Client Implementation</h3>
          <p className="text-textSecondary text-sm mb-2">
            Import the SDK, initialize it with your public API Key, and fetch client verdicts during critical actions (like form registration or login submissions).
          </p>
          <div className="relative">
            <pre className="bg-surface p-4 rounded-xl font-mono text-xs overflow-x-auto text-textSecondary border border-border leading-relaxed">
              <code>{`import NextCaptcha from 'nextcaptcha-sdk';

// Initialize the SDK near your app entry point
NextCaptcha.init({
  apiKey: 'sc_live_your_public_api_key',
  endpoint: 'https://next-captcha-sdk.onrender.com', // Production API Host
  debug: false
});

// Request a decision during form submissions or actions
const handleSubmit = async () => {
  NextCaptcha.getDecision((result) => {
    if (result.error) {
      console.error('NextCaptcha failed:', result.error);
      return;
    }
    
    if (result.action === 'block') {
      alert('Access Denied: Automation detected.');
      return;
    }
    
    // Proceed with registration / auth calls
    submitFormData();
  });
};`}</code>
            </pre>
            <button 
              onClick={() => copyToClipboard(`import NextCaptcha from 'nextcaptcha-sdk';\n\nNextCaptcha.init({\n  apiKey: 'sc_live_your_public_api_key',\n  endpoint: 'https://next-captcha-sdk.onrender.com',\n  debug: false\n});\n\nconst handleSubmit = async () => {\n  NextCaptcha.getDecision((result) => {\n    if (result.error) {\n      console.error('NextCaptcha failed:', result.error);\n      return;\n    }\n    if (result.action === 'block') {\n      alert('Access Denied: Automation detected.');\n      return;\n    }\n    submitFormData();\n  });\n};`, 'npm-code')}
              className="absolute right-4 top-4 text-textSecondary hover:text-text transition-colors"
            >
              {copiedText === 'npm-code' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )
    },
    cdn: {
      title: 'CDN/HTML Integration',
      icon: Terminal,
      content: (
        <div className="space-y-6">
          <p className="text-textSecondary leading-relaxed">
            For static websites, CMS portals (WordPress, Webflow, Shopify), or simple HTML pages, load NextCaptcha using a global script tag.
          </p>

          <h3 className="text-xl font-semibold mt-6 mb-2">1. Inject the Script</h3>
          <p className="text-textSecondary text-sm mb-2">
            Add the lightweight NextCaptcha bundle before the closing <code className="text-accent">&lt;/body&gt;</code> tag of your target pages.
          </p>
          <div className="relative">
            <pre className="bg-surface p-4 rounded-xl font-mono text-xs overflow-x-auto text-textSecondary border border-border">
              <code>{`<script src="https://cdn.jsdelivr.net/npm/nextcaptcha-sdk@latest/dist/nextcaptcha.min.js" async defer></script>`}</code>
            </pre>
            <button 
              onClick={() => copyToClipboard('<script src="https://cdn.jsdelivr.net/npm/nextcaptcha-sdk@latest/dist/nextcaptcha.min.js" async defer></script>', 'cdn-script')}
              className="absolute right-4 top-4 text-textSecondary hover:text-text transition-colors"
            >
              {copiedText === 'cdn-script' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <h3 className="text-xl font-semibold mt-8 mb-2">2. Trigger Telemetry Evaluation</h3>
          <p className="text-textSecondary text-sm mb-2">
            Configure the SDK. Once page interactions are ready, call the decision engine:
          </p>
          <div className="relative">
            <pre className="bg-surface p-4 rounded-xl font-mono text-xs overflow-x-auto text-textSecondary border border-border leading-relaxed">
              <code>{`<script>
  window.addEventListener('nextcaptcha-ready', () => {
    // 1. Initialize
    window.NextCaptcha.init({
      apiKey: 'sc_live_your_public_api_key',
      endpoint: 'https://next-captcha-sdk.onrender.com'
    });
  });

  // 2. Fetch decision on action
  function performSubmit() {
    if (window.NextCaptcha) {
      window.NextCaptcha.getDecision(function(result) {
        if (result.action === 'block') {
          alert('Access Denied: Bot behavior detected.');
          return;
        }
        document.getElementById('my-form').submit();
      });
    }
  }
</script>`}</code>
            </pre>
            <button 
              onClick={() => copyToClipboard(`<script>\n  window.addEventListener('nextcaptcha-ready', () => {\n    window.NextCaptcha.init({\n      apiKey: 'sc_live_your_public_api_key',\n      endpoint: 'https://next-captcha-sdk.onrender.com'\n    });\n  });\n\n  function performSubmit() {\n    if (window.NextCaptcha) {\n      window.NextCaptcha.getDecision(function(result) {\n        if (result.action === 'block') {\n          alert('Access Denied: Bot behavior detected.');\n          return;\n        }\n        document.getElementById('my-form').submit();\n      });\n    }\n  }\n</script>`, 'cdn-code')}
              className="absolute right-4 top-4 text-textSecondary hover:text-text transition-colors"
            >
              {copiedText === 'cdn-code' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )
    },
    api: {
      title: 'REST API Reference',
      icon: Layers,
      content: (
        <div className="space-y-6">
          <p className="text-textSecondary leading-relaxed">
            For backend verification, native iOS/Android applications, or advanced server-side validation, make HTTP POST calls directly to the NextCaptcha prediction service.
          </p>

          <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <span className="bg-green-500/10 text-green-500 font-bold px-3 py-1 rounded-lg text-xs">POST</span>
              <code className="text-textSecondary font-mono text-sm">https://next-captcha-sdk.onrender.com/api/predict</code>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-semibold text-sm text-textSecondary">Request Headers:</h4>
              <pre className="bg-surface2 p-3 rounded-lg font-mono text-xs text-accent">
{`X-API-Key: sc_live_your_private_api_key
Content-Type: application/json`}
              </pre>
            </div>

            <div className="space-y-2">
              <h4 className="font-semibold text-sm text-textSecondary">Request Body Payload:</h4>
              <p className="text-xs text-textSecondary mb-2">
                Note: Client SDKs compile behavioral features automatically using <code className="text-accent">NextCaptcha.getTelemetryPayload()</code>.
              </p>
              <pre className="bg-surface2 p-3 rounded-lg font-mono text-xs text-textSecondary overflow-x-auto">
{`{
  "sdkVersion": "4.0.0",
  "webdriver_flag": false,
  "user_agent": "Mozilla/5.0...",
  "has_touch": false,
  "platform": "MacIntel",
  "avg_mouse_vel": 124.5,
  "total_distance": 520.1,
  "click_count": 3,
  "session_duration": 5.4,
  "event_count": 68,
  "avg_hover_duration": 48.0,
  "mouse_curvature_std": 0.21,
  "mouse_jerk_std": 120530.4,
  "...": "..." // Remaining 43 behavioral metrics
}`}
              </pre>
            </div>

            <div className="space-y-2">
              <h4 className="font-semibold text-sm text-textSecondary">Response Body Payload (200 OK):</h4>
              <pre className="bg-surface2 p-3 rounded-lg font-mono text-xs text-textSecondary overflow-x-auto">
{`{
  "bot_probability": 0.08,
  "model_probability": 0.08,
  "rule_boost": 0.0,
  "risk_score": 8,
  "action": "allow",
  "behavior_score": 8.0,
  "fingerprint_score": 0.0,
  "challenge_score": 0.0,
  "overall_risk": 8.0,
  "confidence": 0.92,
  "risk_engine_enabled": true
}`}
              </pre>
            </div>
          </div>
        </div>
      )
    }
  };

  return (
    <div className="min-h-screen bg-background text-text">
      {/* Top Header */}
      <header className="border-b border-border bg-surface sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => window.location.href = '/'}>
            <Shield className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold">NextCaptcha Docs</span>
          </div>
          
          <button 
            onClick={() => window.location.href = '/'}
            className="flex items-center gap-2 text-sm text-textSecondary hover:text-text transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-6 py-10 grid md:grid-cols-4 gap-8">
        
        {/* Sidebar Nav */}
        <aside className="md:col-span-1 space-y-2">
          {Object.entries(sections).map(([id, section]) => {
            const Icon = section.icon;
            const isActive = activeSection === id;
            return (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left text-sm font-medium transition-all ${
                  isActive 
                    ? 'bg-primary/10 text-primary border-l-4 border-primary' 
                    : 'text-textSecondary hover:bg-surface'
                }`}
              >
                <Icon className="w-5 h-5" />
                {section.title}
              </button>
            );
          })}
        </aside>

        {/* Content Panel */}
        <main className="md:col-span-3 bg-surface border border-border rounded-2xl p-8 shadow-xl">
          <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
            {sections[activeSection].title}
          </h2>
          {sections[activeSection].content}
        </main>

      </div>
    </div>
  );
}
