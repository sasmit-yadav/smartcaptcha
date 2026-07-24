/**
 * Optional P0 probe: rebrowser-playwright (CDP-minimal Chromium).
 * Skips cleanly when the package is not installed.
 *
 * Env: REDTEAM_BASE, REDTEAM_REQUIRE_ADVANCED_BLOCK=1 to fail on ALLOW.
 */
const BASE = process.env.REDTEAM_BASE || 'http://127.0.0.1:3000';
const REQUIRE_BLOCK = process.env.REDTEAM_REQUIRE_ADVANCED_BLOCK === '1';

async function main() {
  let chromium;
  try {
    ({ chromium } = require('rebrowser-playwright'));
  } catch {
    console.log('SKIP: npm i -D rebrowser-playwright to enable this probe');
    process.exit(0);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  let predict = null;
  page.on('response', async (response) => {
    try {
      if (response.url().includes('/api/predict')) {
        predict = { status: response.status(), body: await response.json() };
      }
    } catch {}
  });

  try {
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  } catch (err) {
    console.log(`SKIP: demo site unreachable (${err.message})`);
    await browser.close();
    process.exit(0);
  }
  await page.waitForFunction(() => !!window.VeilProof, { timeout: 30000 });
  await page.fill('#name', 'Rebrowser Probe');
  await page.fill('#email', 'rebrowser@test.com');
  await page.fill('#message', 'CDP-minimal red-team probe');
  await page.click('#submitBtn');
  await page.waitForSelector('#status.success, #status.error', { timeout: 45000 });

  const statusText = await page.locator('#status').innerText();
  const blocked =
    statusText.includes('Blocked') || predict?.body?.action === 'block';
  const report = {
    variant: 'rebrowser_cdp_minimal',
    result: blocked ? 'BLOCKED' : 'ALLOWED',
    known_gap: !blocked,
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

  if (!blocked && REQUIRE_BLOCK) {
    console.error('FAIL: rebrowser allowed and REDTEAM_REQUIRE_ADVANCED_BLOCK=1');
    process.exit(2);
  }
  if (!blocked) {
    console.log('INFO: rebrowser ALLOWED (known advanced gap — recorded, not failing CI)');
  } else {
    console.log('PASS: rebrowser BLOCKED');
  }
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
