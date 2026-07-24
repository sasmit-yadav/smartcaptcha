# VeilProof red-team harness (P0)

Industry-style adversarial gate for bot-detection regressions.

| Probe | Purpose | CI gate |
|---|---|---|
| Backend pytest (signing + CDP) | Strict signing + CDP inconclusive policy | **Must pass** |
| `unsigned_forge.py` | Direct `/api/predict` forge without ECDSA | **Must 401** in strict |
| `playwright_js_stealth.mjs` | Playwright + `webdriver→undefined` + human-like input | **Must BLOCK** |
| `rebrowser_probe.mjs` | CDP-minimal Chromium (optional dep) | Report; skip if missing |
| `camoufox_probe.py` | Patched Firefox + humanize (optional) | Report; skip if missing |

Advanced stacks (Camoufox / rebrowser) are **known hard** — CI records their
outcome as an artifact so false-negatives are visible, but does not fail the
pipeline unless `REDTEAM_REQUIRE_ADVANCED_BLOCK=1`.

## Local

```bash
# Always
cd sdk-backend && python -m pytest tests/test_request_signing.py tests/test_stealth_fingerprint.py tests/test_signed_predict_route.py -q

# Against production (needs site key + demo site)
set VEILPROOF_API=https://api.veilproof.tech
set VEILPROOF_SITE_KEY=vp_site_...
set REDTEAM_BASE=http://127.0.0.1:3000
python tools/redteam/unsigned_forge.py
node tools/redteam/playwright_js_stealth.mjs
```

Optional:
```bash
npm i -D rebrowser-playwright   # then
node tools/redteam/rebrowser_probe.mjs

pip install camoufox playwright
python -m camoufox fetch
python tools/redteam/camoufox_probe.py
```
