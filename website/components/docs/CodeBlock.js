'use client';

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = code;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="border border-hairline rounded-xl overflow-hidden bg-surfaceElevated">
      {language && (
        <div className="flex items-center justify-between px-4 h-10 border-b border-hairline">
          <span className="text-xs text-mute font-mono uppercase tracking-wide">{language}</span>
          <button onClick={copy} aria-label="Copy code" className="text-mute hover:text-ink transition-colors">
            {copied ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      )}
      <div className="relative group">
        <pre className="p-4 font-mono text-xs overflow-x-auto text-mute leading-relaxed">
          <code>{code}</code>
        </pre>
        {!language && (
          <button
            onClick={copy}
            aria-label="Copy code"
            className="absolute right-3 top-3 text-mute hover:text-ink transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}
