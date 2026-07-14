'use client';

import { useState, useEffect } from 'react';
import CodeBlock from './CodeBlock';

const STORAGE_KEY = 'veriflow_docs_lang';

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
      <div className="flex gap-1 mb-2 flex-wrap">
        {tabs.map(t => (
          <button
            key={t.label}
            onClick={() => select(t.label)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              active === t.label ? 'bg-primary/10 text-primary' : 'text-textSecondary hover:bg-surface2'
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
