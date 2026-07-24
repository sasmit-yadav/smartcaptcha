# VeilProof red-team harness

Industry-style adversarial gate for bot-detection regressions.

**Context (2026-07-24 EOD):** P0 stealth + strict signing are production gates.
**P1** network Worker is live on `api.veilproof.tech`. **P2.1** JSONL labels
collected; Camoufox retrain skipped. Hardest demo bots **BLOCKED** on CDN
**1.1.10**. Product freeze (dashboard auth): CAPTCHA
`docs/VeilProof_Product_Through_2026-07-24.md`.

| Probe | Purpose | CI gate |
|---|---|---|
| Backend pytest (signing + CDP + network) | Strict signing + CDP soft + network fuse | **Must pass** |
| `unsigned_forge.py` | Direct `/api/predict` forge without ECDSA | **Must 401** in strict |
| `playwright_js_stealth.mjs` | Playwright + `webdriver→undefined` + human-like input | **Must BLOCK** |
| `rebrowser_probe.mjs` | CDP-minimal Chromium (optional dep) | Report + **JSONL**; skip if missing |
| `camoufox_probe.py` | Patched Firefox + humanize (optional) | Report + **JSONL**; skip if missing |

Advanced stacks (Camoufox / rebrowser) are **known hard** — CI records their
outcome as an artifact so false-negatives are visible, but does not fail the
pipeline unless `REDTEAM_REQUIRE_ADVANCED_BLOCK=1`.

## P2.1 — collect labeled bots

```bash
# Terminal A — customer demo
cd C:\customer-website-test
npm start

# Terminal B — batch (example: 10 Camoufox sessions)
cd C:\Users\91798.SASMITPC\OneDrive\Documents\PROJECTS\CAPTCHA
set REDTEAM_BASE=http://127.0.0.1:3000
set REDTEAM_RUNS=10
python tools/redteam/collect_p2.py
```

Or single stack:
```bash
set REDTEAM_RUNS=50
python tools/redteam/camoufox_probe.py
```

Labels land in `tools/redteam/out/camoufox_YYYYMMDD.jsonl` (`label: bot`).
Target before P2.2 ingest: **N≥50** Camoufox sessions.

## Local regression

```bash
cd sdk-backend && python -m pytest tests/test_request_signing.py tests/test_stealth_fingerprint.py tests/test_network_signals.py tests/test_signed_predict_route.py -q

set VEILPROOF_API=https://api.veilproof.tech
set VEILPROOF_SITE_KEY=vp_site_...
set REDTEAM_BASE=http://127.0.0.1:3000
python tools/redteam/unsigned_forge.py
node tools/redteam/playwright_js_stealth.mjs
```

Optional deps:
```bash
npm i -D rebrowser-playwright
pip install camoufox
python -m camoufox fetch
```

Worker / API proof (P1 ops):
```bash
curl.exe -sSI https://api.veilproof.tech/api/stats
# Expect: X-VP-Worker: wispy-term-8f37
```
