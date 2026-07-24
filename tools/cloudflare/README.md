# Cloudflare → VeilProof API (P1)

## Reality check (2026-07)

| Capability | Free | Enterprise Bot Management |
|---|---|---|
| Bot Fight Mode | Yes | — |
| `cf-bot-score` / `cf-ja4` to origin | **No** | Yes (managed transform) |
| Worker `request.cf.asn` / `asOrganization` / `tlsVersion` | **Yes** | Yes |

So on Free we **do not** get JA4 at the origin. We **do** get usable ASN/org via a tiny Worker.

## Deploy the forwarder

1. Cloudflare Dashboard → Workers & Pages → Create → paste
   [`forward-cf-headers.js`](./forward-cf-headers.js).
2. Add route: `api.yourdomain.tld/*` (must be orange-cloud).
3. Confirm origin FastAPI sees headers (enable debug once):
   - `CF-Connecting-IP`
   - `X-VP-CF-ASN`
   - `X-VP-CF-AS-Org`
   - `X-VP-CF-TLS-Version`
   - `X-VP-CF-HTTP-Protocol`

`sdk-backend/core/network_signals.py` already scores these.

## Optional Enterprise

Enable managed transform **Add bot protection headers**. Then
`cf-bot-score` / `cf-ja4` light up automatically — no Worker required for those.
