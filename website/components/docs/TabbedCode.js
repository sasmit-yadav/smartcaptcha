'use client';

import { useState, useEffect } from 'react';
import CodeBlock from './CodeBlock';

const STORAGE_KEY = 'veilproof_docs_lang';

export default function TabbedCode({ tabs }) {
  // tabs: [{ label, code }]
  const [active, setActive] = useState(tabs[0]?.label);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (saved && tabs.some(t => t.label === saved)) setActive(saved);
  }, [tabs]);

  const select = (label) => {
    setActive(label);
    if (typeof window !== 'undefined') localStorage.setItem(STORAGE_KEY, label);
  };

  const current = tabs.find(t => t.label === active) || tabs[0];

  return (
    <div>
      <div className="inline-flex gap-1 mb-2 flex-wrap bg-surface border border-hairline rounded-lg p-1" role="tablist">
        {tabs.map(t => (
          <button
            key={t.label}
            onClick={() => select(t.label)}
            role="tab"
            aria-selected={active === t.label}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              active === t.label ? 'bg-white/10 text-ink' : 'text-mute hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <CodeBlock code={current.code} />
    </div>
  );
}
