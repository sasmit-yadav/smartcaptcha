'use client';

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      {language && (
        <div className="absolute left-4 top-3 text-xs text-textSecondary font-mono uppercase tracking-wide">
          {language}
        </div>
      )}
      <pre className={`bg-surface2 border border-border rounded-xl p-4 ${language ? 'pt-9' : ''} font-mono text-xs overflow-x-auto text-textSecondary leading-relaxed`}>
        <code>{code}</code>
      </pre>
      <button
        onClick={copy}
        aria-label="Copy code"
        className="absolute right-3 top-3 text-textSecondary hover:text-text transition-colors"
      >
        {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
      </button>
    </div>
  );
}
