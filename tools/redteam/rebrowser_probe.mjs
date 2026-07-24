/**
 * Optional P2 probe: rebrowser-playwright (CDP-minimal Chromium).
 * Appends labeled JSONL under tools/redteam/out/ (see SCHEMA.md).
 *
 * Env: REDTEAM_BASE, REDTEAM_RUNS, REDTEAM_REQUIRE_ADVANCED_BLOCK=1
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const BASE = process.env.REDTEAM_BASE || 'http://127.0.0.1:3000';
const REQUIRE_BLOCK = process.env.REDTEAM_REQUIRE_ADVANCED_BLOCK === '1';
const RUNS = Math.max(1, parseInt(process.env.REDTEAM_RUNS || '1', 10));
const OUT_DIR = path.join(__dirname, 'out');
const SCHEMA_VERSION = 'veilproof.redteam.v1';

function dayStamp() {
  return new Date().toISOString().slice(0, 10).replace(/-/g, '');
}

function appendLabel(record) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const file = path.join(OUT_DIR, `rebrowser_${dayStamp()}.jsonl`);
  fs.appendFileSync(file, JSON.stringify(record) + '\n', 'utf8');
  return file;
}

async function oneRun(chromium, attempt, runId) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  let predict = null;
  let statusText = '';
  let error = null;
  let result = 'ERROR';

  page.on('response', async (response) => {
    try {
      if (response.url().includes('/api/predict')) {
        predict = { status: response.status(), body: await response.json() };
      }
    } catch {}
  });

  try {
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForFunction(() => !!window.VeilProof, { timeout: 45000 });
    await page.fill('#name', `Rebrowser Probe ${attempt}`);
    await page.fill('#email', `rebrowser${attempt}@test.com`);
    await page.fill('#message', 'CDP-minimal red-team probe P2');
    await page.click('#submitBtn');
    await page.waitForSelector('#status.success, #status.error', { timeout: 60000 });
    statusText = await page.locator('#status').innerText();
    const body = predict?.body || {};
    const blocked =
      statusText.includes('Blocked') ||
      body.action === 'block' ||
      (body.fingerprint_score ?? 0) >= 50 ||
      (body.risk_score ?? 0) >= 50;
    result = blocked ? 'BLOCKED' : 'ALLOWED';
  } catch (err) {
    error = err.message || String(err);
    if (/unreachable|ECONNREFUSED|Timeout/i.test(error)) result = 'SKIP';
  }

  await browser.close().catch(() => {});

  const body = predict?.body || null;
  const file = appendLabel({
    schema_version: SCHEMA_VERSION,
    ts: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    stack: 'rebrowser',
    variant: 'rebrowser_cdp_minimal',
    label: 'bot',
    label_source: 'redteam_probe',
    result,
    known_gap: result === 'ALLOWED',
    base_url: BASE,
    api_host: process.env.VEILPROOF_API || 'https://api.veilproof.tech',
    predict: body
      ? {
          action: body.action,
          risk_score: body.risk_score,
          fingerprint_score: body.fingerprint_score,
          behavior_score: body.behavior_score,
          network_score: body.network_score,
          session_id: body.session_id || body.sessionId,
          automation_signals: body.automation_signals,
          sdk_version: body.sdk_version || body.sdkVersion,
        }
      : null,
    status_text: statusText,
    run_id: runId,
    attempt,
    error: error || undefined,
    notes: 'P2.1 labeled advanced stealth',
  });

  return { attempt, result, known_gap: result === 'ALLOWED', predict: body, statusText, error, jsonl: file };
}

async function main() {
  let chromium;
  try {
    ({ chromium } = require('rebrowser-playwright'));
  } catch {
    console.log('SKIP: npm i -D rebrowser-playwright to enable this probe');
    process.exit(0);
  }

  const runId = crypto.randomUUID();
  const reports = [];
  for (let i = 1; i <= RUNS; i++) {
    console.log(`[rebrowser] attempt ${i}/${RUNS} -> ${BASE}`);
    const rep = await oneRun(chromium, i, runId);
    reports.push(rep);
    console.log(JSON.stringify(rep, null, 2));
  }

  const summary = {
    run_id: runId,
    stack: 'rebrowser',
    runs: RUNS,
    blocked: reports.filter((r) => r.result === 'BLOCKED').length,
    allowed: reports.filter((r) => r.result === 'ALLOWED').length,
    skip: reports.filter((r) => r.result === 'SKIP').length,
    error: reports.filter((r) => r.result === 'ERROR').length,
  };
  console.log('SUMMARY', JSON.stringify(summary));

  const anyAllow = summary.allowed > 0;
  if (anyAllow && REQUIRE_BLOCK) {
    console.error('FAIL: rebrowser allowed and REDTEAM_REQUIRE_ADVANCED_BLOCK=1');
    process.exit(2);
  }
  if (anyAllow) {
    console.log('INFO: rebrowser ALLOWED (known advanced gap — labeled for P2 training)');
  } else if (summary.blocked) {
    console.log('PASS: rebrowser BLOCKED');
  }
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
