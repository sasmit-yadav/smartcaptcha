/**
 * Honeypot field (strategy doc step 7 — free labels).
 *
 * Injects a form field that is invisible and unreachable for a real human
 * (off-screen, aria-hidden, tabindex=-1, autocomplete off) but that naive
 * bots — which blindly fill every input they find — will populate. A filled
 * honeypot is a near-certain bot signal, reported to /api/predict as
 * `honeypot_triggered` and used server-side both as a decisive block and as a
 * free, high-confidence training label.
 *
 * This is deliberately NOT a substitute for behavioural detection — a
 * sophisticated bot ignores hidden fields — it's a cheap high-precision layer
 * that catches the dumb majority for free. Precision over recall by design.
 */

const HONEYPOT_ATTR = 'data-vp-honeypot';
// A field name that looks worth filling to a naive bot but that no real form
// asks a human for on these flows.
const HONEYPOT_NAME = 'contact_url';

const injectedFields: HTMLInputElement[] = [];

export function injectHoneypot(form: HTMLFormElement): void {
  // Don't double-inject into the same form.
  if (form.querySelector(`[${HONEYPOT_ATTR}]`)) return;

  const input = document.createElement('input');
  input.type = 'text';
  input.name = HONEYPOT_NAME;
  input.tabIndex = -1;
  input.autocomplete = 'off';
  input.setAttribute(HONEYPOT_ATTR, '1');
  input.setAttribute('aria-hidden', 'true');
  // Visually removed from the page but still in the DOM so bots can see it.
  // Avoid display:none / visibility:hidden alone — some bots skip those; this
  // combination is off-screen AND non-interactive for real users.
  input.style.cssText =
    'position:absolute!important;left:-9999px!important;top:-9999px!important;' +
    'width:1px;height:1px;opacity:0;pointer-events:none;';

  form.appendChild(input);
  injectedFields.push(input);
}

/** True if any injected honeypot field has been filled (bot signal). */
export function isHoneypotTriggered(): boolean {
  return injectedFields.some(el => (el.value || '').trim().length > 0);
}

/** Test/teardown helper. */
export function resetHoneypot(): void {
  injectedFields.length = 0;
}
