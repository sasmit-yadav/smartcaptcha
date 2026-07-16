import { ShieldCheck } from 'lucide-react';

const COLUMNS = [
  { title: 'Product', links: [{ label: 'Features', href: '/#features' }, { label: 'How it works', href: '/#platform' }, { label: 'Documentation', href: '/docs#start' }] },
  { title: 'Developers', links: [{ label: 'Quick start', href: '/docs#start' }, { label: 'API reference', href: '/docs#api' }, { label: 'SDK reference', href: '/docs#sdk' }] },
  { title: 'Account', links: [{ label: 'Dashboard', href: '/dashboard' }, { label: 'API keys', href: '/dashboard' }] },
];

export default function SiteFooter() {
  return (
    <footer className="bg-canvas border-t border-hairline">
      <div className="max-w-[1280px] mx-auto px-6 py-section">
        <div className="grid md:grid-cols-5 gap-12 mb-12">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4 text-ink font-brand font-semibold text-lg">
              <ShieldCheck className="w-6 h-6 text-primary" strokeWidth={2.25} />
              VeilProof
            </div>
            <p className="text-sm max-w-sm leading-relaxed text-mute">
              Invisible behavioral bot detection. A browser SDK collects
              signals; your server decides who to trust.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="text-ink font-semibold text-sm mb-4">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a href={l.href} className="text-sm text-mute hover:text-ink transition-colors">
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-col md:flex-row justify-between items-center gap-4 pt-8 border-t border-hairline text-xs text-stone uppercase tracking-wider">
          <p>&copy; 2026 VeilProof. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="/docs#security" className="hover:text-ink transition-colors">Privacy</a>
            <a href="/docs#api" className="hover:text-ink transition-colors">Terms</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
