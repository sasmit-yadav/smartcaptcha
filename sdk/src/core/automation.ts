/**
 * Automation / stealth-driver probes.
 *
 * navigator.webdriver alone is not enough: Playwright/Puppeteer stealth
 * kits redefine it to `undefined` via Object.defineProperty. Real Chrome
 * exposes a native boolean (false when not automated). A non-native own
 * getter, Playwright/Selenium globals, or CDP leaks are decisive.
 */

export interface AutomationProbe {
  /** Treat as webdriver for fingerprint scoring. */
  webdriverFlag: boolean;
  /** 0-100 contribution for fingerprint_score. */
  automationScore: number;
  signals: string[];
}

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
  // Runtime.enable causes Error.stack accessors to fire when console
  // methods stringify errors. Cheap one-shot probe; false on clean browsers.
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
  let score = 0;

  if ((navigator as Navigator & { webdriver?: boolean }).webdriver === true) {
    signals.push('webdriver_true');
    score = 100;
  }

  const spoof = probeWebdriverSpoof();
  if (spoof) {
    signals.push(spoof);
    score = Math.max(score, 100);
  }

  for (const g of probeDriverGlobals()) {
    signals.push(g);
    score = Math.max(score, 100);
  }

  const cdp = probeCdpRuntimeLeak();
  if (cdp) {
    signals.push(cdp);
    score = Math.max(score, 85);
  }

  return {
    webdriverFlag: score >= 50,
    automationScore: Math.min(100, score),
    signals,
  };
}
