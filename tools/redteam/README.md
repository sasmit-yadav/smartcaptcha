# VeilProof red-team harness

Industry-style adversarial gate for bot-detection regressions.

**Context (2026-07-24):** P0 stealth + strict signing are production gates.
**P1** network Worker is live on `api.veilproof.tech`. **Next (P2):** turn
Camoufox/rebrowser probes into labeled JSONL training data — see
`docs/VeilProof_Status_Through_2026-07-24.md`.

| Probe | Purpose | CI gate |
|---|---|---|
| Backend pytest (signing + CDP + network) | Strict signing + CDP soft + network fuse | **Must pass** |
| `unsigned_forge.py` | Direct `/api/predict` forge without ECDSA | **Must 401** in strict |
| `playwright_js_stealth.mjs` | Playwright + `webdriver→undefined` + human-like input | **Must BLOCK** |
| `rebrowser_probe.mjs` | CDP-minimal Chromium (optional dep) | Report; skip if missing → **P2 labels** |
| `camoufox_probe.py` | Patched Firefox + humanize (optional) | Report; skip if missing → **P2 labels** |

Advanced stacks (Camoufox / rebrowser) are **known hard** — CI records their
outcome as an artifact so false-negatives are visible, but does not fail the
pipeline unless `REDTEAM_REQUIRE_ADVANCED_BLOCK=1`.

## Local

```bash
# Always
cd sdk-backend && python -m pytest tests/test_request_signing.py tests/test_stealth_fingerprint.py tests/test_network_signals.py tests/test_signed_predict_route.py -q

# Against production (needs site key + demo site)
set VEILPROOF_API=https://api.veilproof.tech
set VEILPROOF_SITE_KEY=vp_site_...
set REDTEAM_BASE=http://127.0.0.1:3000
python tools/redteam/unsigned_forge.py
node tools/redteam/playwright_js_stealth.mjs
```

Optional (P2 data collection):
```bash
npm i -D rebrowser-playwright   # then
node tools/redteam/rebrowser_probe.mjs

pip install camoufox playwright
python -m camoufox fetch
python tools/redteam/camoufox_probe.py
```

Worker / API proof (P1 ops):
```bash
curl.exe -sSI https://api.veilproof.tech/api/stats
# Expect: X-VP-Worker: wispy-term-8f37
```
