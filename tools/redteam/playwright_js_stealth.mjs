/**
 * P0 red-team: Playwright JS stealth (webdriver → undefined + human-like input).
 * Must be BLOCKED by veilproof@1.1.4+ webdriver_undefined probe.
 *
 * Env:
 *   REDTEAM_BASE   demo site (default http://127.0.0.1:3000)
 *   REDTEAM_HEADLESS=0 for headed
 */
const BASE = process.env.REDTEAM_BASE || 'http://127.0.0.1:3000';
const HEADLESS = process.env.REDTEAM_HEADLESS !== '0';

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function rand(min, max) {
  return min + Math.random() * (max - min);
}
function bezier(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return {
    x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
    y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
  };
}

async function humanMouseMove(page, toX, toY) {
  const pos = await page.evaluate(() => ({
    x: window.__vpMouseX || 20,
    y: window.__vpMouseY || 20,
  }));
  const from = { x: pos.x, y: pos.y };
  const to = { x: toX, y: toY };
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const c1 = { x: from.x + dx * rand(0.2, 0.4) + rand(-40, 40), y: from.y + dy * rand(0.1, 0.3) + rand(-30, 30) };
  const c2 = { x: from.x + dx * rand(0.6, 0.8) + rand(-40, 40), y: from.y + dy * rand(0.7, 0.9) + rand(-30, 30) };
  const steps = Math.floor(rand(24, 40));
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const p = bezier(from, c1, c2, to, eased);
    await page.mouse.move(p.x + rand(-1, 1), p.y + rand(-1, 1));
    await page.evaluate(({ x, y }) => { window.__vpMouseX = x; window.__vpMouseY = y; }, { x: p.x, y: p.y });
    await sleep(rand(6, 16));
  }
}

async function humanClick(page, selector) {
  const box = await page.locator(selector).boundingBox();
  if (!box) throw new Error(`missing ${selector}`);
  const x = box.x + box.width * rand(0.35, 0.65);
  const y = box.y + box.height * rand(0.35, 0.65);
  await humanMouseMove(page, x, y);
  await sleep(rand(40, 120));
  await page.mouse.down();
  await sleep(rand(30, 90));
  await page.mouse.up();
}

async function humanType(page, selector, text) {
  await humanClick(page, selector);
  for (const ch of text) {
    await page.keyboard.type(ch, { delay: rand(45, 140) });
    if (Math.random() < 0.08) await sleep(rand(120, 400));
  }
}

async function main() {
  let chromium;
  try {
    ({ chromium } = require('playwright'));
  } catch {
    console.log('SKIP: install playwright (npm i playwright) to run JS stealth probe');
    process.exit(0);
  }

  const browser = await chromium.launch({
    headless: HEADLESS,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = window.chrome || { runtime: {} };
  });

  const page = await context.newPage();
  let predict = null;
  page.on('response', async (response) => {
    try {
      if (response.url().includes('/api/predict')) {
        predict = { status: response.status(), body: await response.json() };
      }
    } catch {}
  });

  console.log(`JS stealth → ${BASE}`);
  try {
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  } catch (err) {
    console.log(`SKIP: demo site unreachable (${err.message})`);
    await browser.close();
    process.exit(0);
  }
  await page.waitForFunction(() => !!window.VeilProof, { timeout: 30000 });

  await humanType(page, '#name', 'Jordan Lee');
  await humanType(page, '#email', 'jordan.redteam@test.com');
  await humanType(page, '#message', 'Red-team JS stealth probe');
  await humanClick(page, '#submitBtn');
  await page.waitForSelector('#status.success, #status.error', { timeout: 45000 });

  const statusText = await page.locator('#status').innerText();
  const blocked =
    statusText.includes('Blocked') ||
    predict?.body?.action === 'block' ||
    (predict?.body?.fingerprint_score ?? 0) >= 50;

  const report = {
    variant: 'playwright_js_stealth',
    result: blocked ? 'BLOCKED' : 'ALLOWED',
    predict: predict?.body
      ? {
          action: predict.body.action,
          risk_score: predict.body.risk_score,
          fingerprint_score: predict.body.fingerprint_score,
          behavior_score: predict.body.behavior_score,
        }
      : null,
    statusText,
  };
  console.log(JSON.stringify(report, null, 2));
  await browser.close();

  if (!blocked) {
    console.error('FAIL: JS stealth bot was ALLOWED (regression)');
    process.exit(2);
  }
  console.log('PASS: JS stealth bot BLOCKED');
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
