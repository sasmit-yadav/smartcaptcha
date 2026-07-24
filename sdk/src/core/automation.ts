/**
 * Automation / stealth-driver probes.
 *
 * navigator.webdriver alone is not enough: Playwright/Puppeteer stealth
 * kits redefine it to `undefined` via Object.defineProperty. Real Chrome
 * exposes a native boolean (false when not automated). A non-native own
 * getter or Playwright/Selenium globals are decisive.
 *
 * CDP Runtime.enable leaks are kept as *inconclusive* soft evidence only.
 * Industry consensus (2025–2026): Chrome serialization changes and
 * CDP-minimal drivers (rebrowser, nodriver, patchright) often never trip
 * the classic console.stack probe — a miss must never be treated as proof
 * of humanity, and a lone hit must not be decisive on its own.
 */

export interface AutomationProbe {
  /** Treat as webdriver for fingerprint scoring. */
  webdriverFlag: boolean;
  /** 0-100 contribution for fingerprint_score. */
  automationScore: number;
  signals: string[];
}

/** Soft score for CDP-only evidence — must stay below server block@50. */
const CDP_INCONCLUSIVE_SCORE = 30;
/** Decisive automation evidence (spoof / driver globals / webdriver true). */
const DECISIVE_SCORE = 100;

function isNativeFunction(fn: unknown): boolean {
  if (typeof fn !== 'function') return false;
  try {
    return Function.prototype.toString.call(fn).includes('[native code]');
  } catch {
    return false;
  }
}

function probeWebdriverSpoof(): string | null {
  try {
    const value = (navigator as Navigator & { webdriver?: boolean }).webdriver;
    // Real Chromium always exposes a boolean. Stealth kits return undefined.
    if (value === undefined) return 'webdriver_undefined';

    const own = Object.getOwnPropertyDescriptor(navigator, 'webdriver');
    if (own && typeof own.get === 'function' && !isNativeFunction(own.get)) {
      return 'webdriver_non_native_getter';
    }
    // Own data property forced by a script is unusual; native exposure is
    // typically a prototype getter. Skip pure data-property checks to avoid
    // rare false positives on older engines.
  } catch {
    return 'webdriver_probe_threw';
  }
  return null;
}

function probeDriverGlobals(): string[] {
  const found: string[] = [];
  const w = window as unknown as Record<string, unknown>;
  const names = [
    '__playwright__binding__',
    '__pwInitScripts',
    '__PW_inspect',
    '__playwright_evaluation_script__',
    '_playwrightRestoreElementScroll',
    'callPhantom',
    '_phantom',
    '__nightmare',
    'domAutomation',
    'domAutomationController',
    '__webdriver_evaluate',
    '__selenium_evaluate',
    '__fxdriver_evaluate',
    '__driver_evaluate',
    '__webdriver_unwrapped',
    '__driver_unwrapped',
    '_Selenium_IDE_Recorder',
    '_selenium',
    'calledSelenium',
  ];
  for (const name of names) {
    try {
      if (w[name] != null) found.push(`global:${name}`);
    } catch {
      /* ignore */
    }
  }
  try {
    for (const key of Object.keys(document)) {
      if (key.match(/^\$cdc_/i) || key.match(/^\$chrome_/i) || key.includes('__selenium')) {
        found.push(`document:${key.slice(0, 32)}`);
        break;
      }
    }
  } catch {
    /* ignore */
  }
  return found;
}

function probeCdpRuntimeLeak(): string | null {
  // Classic Runtime.enable side-effect. Cheap; often silent on modern Chrome
  // and CDP-minimal drivers. Positive hit = soft signal only.
  try {
    let leaked = false;
    const err = new Error();
    Object.defineProperty(err, 'stack', {
      configurable: true,
      get() {
        leaked = true;
        return '';
      },
    });
    // eslint-disable-next-line no-console
    console.debug(err);
    if (leaked) return 'cdp_runtime_enable';
  } catch {
    /* ignore */
  }
  return null;
}

/**
 * Run all probes once per page. Safe to call repeatedly — cheap and
 * side-effect free aside from a cleared console.debug.
 */
export function detectAutomation(): AutomationProbe {
  const signals: string[] = [];
  let decisive = 0;
  let soft = 0;

  if ((navigator as Navigator & { webdriver?: boolean }).webdriver === true) {
    signals.push('webdriver_true');
    decisive = DECISIVE_SCORE;
  }

  const spoof = probeWebdriverSpoof();
  if (spoof) {
    signals.push(spoof);
    decisive = Math.max(decisive, DECISIVE_SCORE);
  }

  for (const g of probeDriverGlobals()) {
    signals.push(g);
    decisive = Math.max(decisive, DECISIVE_SCORE);
  }

  const cdp = probeCdpRuntimeLeak();
  if (cdp) {
    signals.push(cdp);
    // Inconclusive alone — never reach block threshold without decisive evidence.
    soft = Math.max(soft, CDP_INCONCLUSIVE_SCORE);
  }

  const automationScore = Math.min(100, Math.max(decisive, soft));

  return {
    // Only decisive evidence flips the webdriver-equivalent flag.
    webdriverFlag: decisive >= 50,
    automationScore,
    signals,
  };
}
