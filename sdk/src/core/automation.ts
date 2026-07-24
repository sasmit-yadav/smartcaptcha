/**
 * Automation / stealth-driver probes + environment coherence.
 *
 * navigator.webdriver alone is not enough: Playwright/Puppeteer stealth
 * kits redefine it to `undefined` via Object.defineProperty. Real Chrome
 * exposes a native boolean (false when not automated). A non-native own
 * getter or Playwright/Selenium globals are decisive.
 *
 * CDP Runtime.enable leaks are *inconclusive* soft evidence only.
 * Industry consensus (2025–2026): Chrome serialization changes and
 * CDP-minimal drivers often never trip the classic console.stack probe —
 * a miss must never be treated as proof of humanity, and a lone hit must
 * not be decisive on its own.
 *
 * Environment coherence (UA ↔ engine ↔ WebGL ↔ platform) catches patched
 * browsers (e.g. Camoufox) that pass webdriver probes but still leak
 * inconsistent fingerprints. Coherence hits are medium-weight: several
 * strong mismatches can block; a single mild mismatch stays soft.
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
/** Strong environment incoherence (enough to push fingerprint toward block). */
const COHERENCE_STRONG = 70;
/** Mild environment incoherence (soft contribution). */
const COHERENCE_SOFT = 40;

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
 * UA / engine / WebGL / platform / headless coherence.
 * Camoufox and similar C++-patched browsers often keep webdriver clean but
 * still leave cross-signal inconsistencies.
 *
 * Scoring: strong mismatches can reach block alone. Mild mismatches *stack*
 * so several soft tells can cross the server block threshold together
 * (industry practice — one weak signal is not enough; a bundle is).
 */
function probeEnvironmentCoherence(): { signals: string[]; score: number } {
  const signals: string[] = [];
  let strong = 0;
  let softStack = 0;
  const bumpStrong = (sig: string, pts: number) => {
    signals.push(sig);
    strong = Math.max(strong, pts);
  };
  const bumpSoft = (sig: string, pts: number) => {
    signals.push(sig);
    softStack = Math.min(100, softStack + pts);
  };

  const ua = navigator.userAgent || '';
  const uaChrome = /Chrome\//.test(ua) && !/Edg\//.test(ua) && !/OPR\//.test(ua);
  const uaFirefox = /Firefox\//.test(ua);
  const w = window as unknown as Record<string, unknown>;
  const hasChromeObj = !!w.chrome;
  const hasInstallTrigger = typeof w.InstallTrigger !== 'undefined';
  const vendor = navigator.vendor || '';
  const platform = navigator.platform || '';

  // Chrome UA claiming to be Chromium but exposing Firefox-only APIs.
  if (uaChrome && hasInstallTrigger) {
    bumpStrong('coherence_chrome_ua_firefox_api', COHERENCE_STRONG);
  }
  // Firefox buildID present under Chrome UA (Gecko leak).
  try {
    const buildId = (navigator as Navigator & { buildID?: string }).buildID;
    if (uaChrome && buildId) {
      bumpStrong('coherence_chrome_ua_gecko_buildid', COHERENCE_STRONG);
    }
  } catch {
    /* ignore */
  }
  // Firefox UA with a synthetic chrome.runtime (common anti-detect leak).
  if (uaFirefox && hasChromeObj) {
    try {
      const chromeObj = w.chrome as { runtime?: unknown } | undefined;
      if (chromeObj && 'runtime' in chromeObj) {
        bumpStrong('coherence_firefox_ua_chrome_runtime', COHERENCE_STRONG);
      }
    } catch {
      /* ignore */
    }
  }
  // Desktop Chrome UA without window.chrome (often stripped by spoof layers).
  if (uaChrome && !hasChromeObj && !/Android|iPhone|iPad/i.test(ua)) {
    bumpSoft('coherence_chrome_ua_no_chrome_obj', 25);
  }
  // Vendor string fights the UA family.
  if (uaChrome && vendor && !/Google/i.test(vendor)) {
    bumpSoft('coherence_chrome_vendor_mismatch', 20);
  }
  if (uaFirefox && /Google/i.test(vendor)) {
    bumpStrong('coherence_firefox_google_vendor', 55);
  }

  // Platform vs UA OS.
  if (/Win/i.test(platform) && /Mac OS X|Macintosh/i.test(ua)) {
    bumpStrong('coherence_platform_ua_os', 60);
  }
  if (/Mac/i.test(platform) && /Windows NT/i.test(ua)) {
    bumpStrong('coherence_platform_ua_os', 60);
  }
  if (/Linux/i.test(platform) && /Windows NT|Mac OS X/i.test(ua) && !/Android/i.test(ua)) {
    bumpStrong('coherence_platform_ua_os', 55);
  }

  // Firefox should not expose userAgentData (Chromium Client Hints API).
  try {
    const uad = (navigator as Navigator & { userAgentData?: unknown }).userAgentData;
    if (uaFirefox && uad) {
      bumpStrong('coherence_firefox_has_uad', 55);
    }
  } catch {
    /* ignore */
  }

  // WebGL software renderers / missing GL on claimed desktop GPU browsers.
  try {
    const canvas = document.createElement('canvas');
    const gl =
      canvas.getContext('webgl') ||
      (canvas.getContext('experimental-webgl') as WebGLRenderingContext | null);
    if (!gl) {
      if (uaChrome || uaFirefox) bumpSoft('coherence_webgl_missing', 15);
    } else {
      const dbg = gl.getExtension('WEBGL_debug_renderer_info') as {
        UNMASKED_RENDERER_WEBGL: number;
      } | null;
      if (dbg) {
        const renderer = String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || '');
        if (/swiftshader|llvmpipe|virtualbox|microsoft basic render/i.test(renderer)) {
          bumpStrong('coherence_webgl_software', 55);
        }
      }
    }
  } catch {
    /* ignore */
  }

  // Absurd hardware claims (common in poorly configured farms).
  try {
    const hc = navigator.hardwareConcurrency;
    if (typeof hc === 'number' && (hc === 0 || hc > 128)) {
      bumpSoft('coherence_hardware_concurrency', 20);
    }
  } catch {
    /* ignore */
  }
  try {
    const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
    if (typeof mem === 'number' && (mem === 0 || mem > 128)) {
      bumpSoft('coherence_device_memory', 15);
    }
  } catch {
    /* ignore */
  }

  // Mobile UA without touch / desktop UA with mobile-only touch profile.
  try {
    const maxTouch = navigator.maxTouchPoints || 0;
    if (/Mobile|Android|iPhone/i.test(ua) && maxTouch === 0) {
      bumpSoft('coherence_mobile_ua_no_touch', 25);
    }
  } catch {
    /* ignore */
  }

  // Headless / automation viewport tells (outer dimensions zero).
  try {
    if (
      (window.outerWidth === 0 && window.outerHeight === 0) ||
      (screen.width === 0 && screen.height === 0)
    ) {
      bumpSoft('coherence_zero_outer_viewport', 30);
    }
  } catch {
    /* ignore */
  }

  // Plugins empty on desktop Chromium is increasingly common — only soft bump
  // when combined with other chrome-strip signals (already in softStack).
  try {
    if (uaChrome && navigator.plugins && navigator.plugins.length === 0 && !hasChromeObj) {
      bumpSoft('coherence_chrome_no_plugins', 10);
    }
  } catch {
    /* ignore */
  }

  const score = Math.max(strong, softStack >= 55 ? Math.min(100, softStack) : Math.min(softStack, COHERENCE_SOFT));
  return { signals, score };
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
    soft = Math.max(soft, CDP_INCONCLUSIVE_SCORE);
  }

  const coherence = probeEnvironmentCoherence();
  for (const s of coherence.signals) signals.push(s);
  if (coherence.score >= COHERENCE_STRONG) {
    // Strong incoherence is decisive enough to set webdriver-equivalent flag.
    decisive = Math.max(decisive, coherence.score);
  } else if (coherence.score > 0) {
    soft = Math.max(soft, coherence.score);
  }

  const automationScore = Math.min(100, Math.max(decisive, soft));

  return {
    webdriverFlag: decisive >= 50,
    automationScore,
    signals,
  };
}
