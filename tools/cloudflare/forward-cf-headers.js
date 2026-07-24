/**
 * Cloudflare Worker — forward Free-plan request.cf fields to origin.
 *
 * Why: Bot Management headers (cf-bot-score, cf-ja4) are Enterprise-only.
 * Free zones still expose request.cf.asn / asOrganization / tlsVersion /
 * httpProtocol to Workers. Forwarding them lets sdk-backend/network_signals
 * score hosting ASNs without MaxMind or Enterprise.
 *
 * Production (2026-07-24):
 *   Worker: wispy-term-8f37
 *   Route:  api.veilproof.tech/*
 *   Proof:  response header X-VP-Worker (ops only; not scored)
 *
 * Deploy: see tools/cloudflare/README.md
 *
 * Headers consumed by sdk-backend/core/network_signals.py:
 *   X-VP-CF-ASN, X-VP-CF-AS-Org, X-VP-CF-TLS-Version, X-VP-CF-HTTP-Protocol
 *   (+ CF-Connecting-IP / CF-Ray already set by the edge)
 */
export default {
  async fetch(request, _env, _ctx) {
    const cf = request.cf || {};
    const headers = new Headers(request.headers);

    if (cf.asn != null) headers.set("X-VP-CF-ASN", String(cf.asn));
    if (cf.asOrganization) headers.set("X-VP-CF-AS-Org", String(cf.asOrganization));
    if (cf.tlsVersion) headers.set("X-VP-CF-TLS-Version", String(cf.tlsVersion));
    if (cf.httpProtocol) headers.set("X-VP-CF-HTTP-Protocol", String(cf.httpProtocol));
    if (cf.country) headers.set("X-VP-CF-Country", String(cf.country));

    // Enterprise Bot Management — forward if the plan provides them.
    if (cf.botManagement && typeof cf.botManagement.score === "number") {
      headers.set("X-VP-CF-Bot-Score", String(cf.botManagement.score));
    }
    if (cf.botManagement && cf.botManagement.verifiedBot != null) {
      headers.set("X-VP-CF-Verified-Bot", String(cf.botManagement.verifiedBot));
    }

    const res = await fetch(new Request(request, { headers }));
    const out = new Response(res.body, res);
    // Ops proof that this Worker ran on the request path.
    out.headers.set("X-VP-Worker", "wispy-term-8f37");
    return out;
  },
};
