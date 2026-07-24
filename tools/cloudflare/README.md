# Cloudflare → VeilProof API (P1) — LIVE

## Reality check (2026-07)

| Capability | Free | Enterprise Bot Management |
|---|---|---|
| Bot Fight Mode | Yes | — |
| `cf-bot-score` / `cf-ja4` to origin | **No** | Yes (managed transform) |
| Worker `request.cf.asn` / `asOrganization` / `tlsVersion` | **Yes** | Yes |

So on Free we **do not** get JA4 at the origin. We **do** get usable ASN/org via a tiny Worker.

## Production deployment (verified 2026-07-24)

| Item | Value |
|---|---|
| Worker name | `wispy-term-8f37` |
| Route | `api.veilproof.tech/*` |
| Zone | `veilproof.tech` |
| DNS | `api` must stay **Proxied** (orange cloud) |
| Proof header | Response `X-VP-Worker: wispy-term-8f37` |
| Backend consumer | `sdk-backend/core/network_signals.py` |

```bash
curl.exe -sSI https://api.veilproof.tech/api/stats
# Expect: X-VP-Worker: wispy-term-8f37  and  Via: 2.0 heroku-router
```

## Deploy / recreate the forwarder

1. Cloudflare → Workers & Pages → Create → **Start with Hello World** → Deploy.
2. Edit code → paste [`forward-cf-headers.js`](./forward-cf-headers.js) (include `X-VP-Worker` proof) → **Deploy**.
3. Worker → **Domains** → **+ Add Route** (**not** Add Domain).
4. Select zone `veilproof.tech`, then route pattern **`api.veilproof.tech/*`**  
   (never `*.veilproof.tech/*` — that breaks website/dashboard).
5. Confirm with the curl above.

### Pitfalls

- UI error “No zones match…” → pick the **zone** first, then the hostname pattern.
- **Add Domain** makes the Worker own the hostname (breaks Heroku). Use **Add Route**.
- `workers.dev` preview showing “nothing here” is **expected** (no Heroku origin there).
- Dashboard “Subrequests = 0” can lag or mislead — trust **`X-VP-Worker`**.

## Headers forwarded to origin (request)

- `X-VP-CF-ASN`
- `X-VP-CF-AS-Org`
- `X-VP-CF-TLS-Version`
- `X-VP-CF-HTTP-Protocol`
- `X-VP-CF-Country`
- `X-VP-CF-Bot-Score` / `X-VP-CF-Verified-Bot` (only if Enterprise `request.cf.botManagement` present)
- Plus edge-native: `CF-Connecting-IP`, `CF-Ray`

## Optional Enterprise

Enable managed transform **Add bot protection headers**. Then
`cf-bot-score` / `cf-ja4` light up automatically — no Worker required for those.
