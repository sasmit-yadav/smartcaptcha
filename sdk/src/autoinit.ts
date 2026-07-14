/**
 * Script-tag auto-init + classic <form> integration.
 *
 * Lets any HTML page use VeriFlow with zero JS:
 *   <script src=".../veriflow.min.js" data-site-key="vf_site_..." async defer></script>
 *   <form data-veriflow action="/submit" method="post">...</form>
 *
 * Programmatic `VeriFlow.init(...)` callers are unaffected: this only fires
 * when a `data-site-key` attribute is actually present, and `init()`'s
 * existing `initialized` guard prevents a double-init if both are used.
 */

import type { VeriFlowConfig, TokenResult } from './types.js';

interface AutoInitHost {
  init(config: VeriFlowConfig): void;
  getToken(callback: (result: TokenResult) => void): void;
}

function findAutoInitScript(): HTMLScriptElement | null {
  const current = (document as any).currentScript as HTMLScriptElement | null;
  if (current && current.dataset && current.dataset.siteKey) {
    return current;
  }
  // Fallback for browsers/bundling setups where currentScript isn't available
  // (e.g. dynamically injected scripts after the fact).
  const candidates = Array.from(document.querySelectorAll('script[data-site-key]')) as HTMLScriptElement[];
  return candidates.find(s => (s.src || '').includes('veriflow')) || candidates[0] || null;
}

function wireFormInterception(host: AutoInitHost, tokenField: string, debug: boolean): void {
  const forms = document.querySelectorAll('form[data-veriflow]');
  forms.forEach(formEl => {
    const form = formEl as HTMLFormElement;
    const fieldName = form.dataset.tokenField || tokenField;
    let submitting = false;

    form.addEventListener('submit', (event) => {
      if (submitting) return; // second, programmatic submit() call below
      event.preventDefault();

      host.getToken((result) => {
        if (debug) console.log('[VeriFlow] Form token result:', result);

        // Fail open: if token acquisition errors out, submit anyway rather
        // than blocking the user on a VeriFlow outage — documented behavior.
        let input = form.querySelector<HTMLInputElement>(`input[name="${fieldName}"]`);
        if (!input) {
          input = document.createElement('input');
          input.type = 'hidden';
          input.name = fieldName;
          form.appendChild(input);
        }
        input.value = result.token || '';

        submitting = true;
        form.submit();
      });
    });
  });
}

export function runAutoInit(host: AutoInitHost): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  const script = findAutoInitScript();
  if (!script || !script.dataset.siteKey) return; // no data-site-key: programmatic use only

  const siteKey = script.dataset.siteKey;
  const endpoint = script.dataset.endpoint || undefined;
  const debug = script.dataset.debug === 'true';
  const tokenField = script.dataset.tokenField || 'veriflow-token';

  host.init({
    apiKey: siteKey,
    endpoint,
    debug,
    source: 'script-tag',
  });

  const wireForms = () => wireFormInterception(host, tokenField, debug);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireForms);
  } else {
    wireForms();
  }
}
