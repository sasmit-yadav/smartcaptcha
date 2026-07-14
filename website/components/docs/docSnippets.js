// Shared snippet templates for /docs and the dashboard key-creation modal.
// Keeping the backend-shape coupling (siteverify request/response, script
// tag attributes) in one file so both surfaces stay in sync.

export const CDN_URL = 'https://cdn.jsdelivr.net/npm/veriflow-sdk@0.3.0/dist/veriflow.min.js';
export const API_HOST = 'https://next-captcha-sdk.onrender.com';

// Note on the pattern below: `siteKey` is only passed explicitly by the
// dashboard, right after generating a real key — showing the literal value
// there is the point (copy-paste your actual key). Every other caller (the
// generic /docs guide) gets no argument and instead sees the site key read
// from that stack's own config/env convention. The site key isn't a secret
// (it ships in the browser bundle either way), but hardcoding it as a string
// literal in source you commit to git is still sloppy — config should own it,
// not a literal in every file that calls init().

export const scriptTagSnippet = (siteKey) => `<script src="${CDN_URL}"
        data-site-key="${siteKey || '{{ VERIFLOW_SITE_KEY }}'}"
        async defer></script>
${siteKey ? '' : '\n<!-- Render data-site-key from your server-side template/config (Django, EJS, Blade, WordPress option, etc.) — don\'t hardcode it in a committed HTML file. -->'}`;

export const scriptTagFormSnippet = (siteKey) => `<script src="${CDN_URL}"
        data-site-key="${siteKey || '{{ VERIFLOW_SITE_KEY }}'}"
        async defer></script>

<form data-veriflow action="/signup" method="post">
  <input name="email" type="email" required>
  <button type="submit">Sign up</button>
</form>`;

export const npmInstallSnippet = () => `npm install veriflow-sdk`;

export const npmInitSnippet = (siteKey) => `import VeriFlow from 'veriflow-sdk';

// Read from your bundler's env convention (webpack DefinePlugin, dotenv, etc.)
// — never hardcode the key as a string literal in source.
VeriFlow.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'process.env.VERIFLOW_SITE_KEY'} });

const result = await VeriFlow.getToken();
// send result.token to your server for /api/siteverify`;

export const reactSnippet = (siteKey) => `import { useEffect } from 'react';
import VeriFlow from 'veriflow-sdk';

// Vite: import.meta.env.VITE_VERIFLOW_SITE_KEY · CRA: process.env.REACT_APP_VERIFLOW_SITE_KEY
useEffect(() => {
  VeriFlow.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'import.meta.env.VITE_VERIFLOW_SITE_KEY'} });
}, []);

async function handleSubmit(formData) {
  const { token } = await VeriFlow.getToken();
  await fetch('/api/signup', {
    method: 'POST',
    body: JSON.stringify({ ...formData, veriflowToken: token }),
  });
}`;

export const nextjsSnippet = (siteKey) => `'use client';
import { useEffect } from 'react';
import VeriFlow from 'veriflow-sdk';

export function VeriFlowInit() {
  useEffect(() => {
    // NEXT_PUBLIC_* vars are inlined at build time — set this in .env.local,
    // never commit the literal key to source.
    VeriFlow.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'process.env.NEXT_PUBLIC_VERIFLOW_SITE_KEY'} }); // client component only — SDK is SSR-safe (no-ops on the server)
  }, []);
  return null;
}`;

export const vueSnippet = (siteKey) => `<script setup>
import { onMounted } from 'vue';
import VeriFlow from 'veriflow-sdk';

onMounted(() => {
  // Vite exposes import.meta.env.VITE_* — set VITE_VERIFLOW_SITE_KEY in .env
  VeriFlow.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'import.meta.env.VITE_VERIFLOW_SITE_KEY'} });
});

async function handleSubmit() {
  const { token } = await VeriFlow.getToken();
  // send token to your server
}
</script>`;

export const siteverifyCurlSnippet = (secretKey = 'vf_secret_your_secret_key') => `curl -X POST ${API_HOST}/api/siteverify \\
  -H "X-API-Key: ${secretKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"token": "<token from the browser>"}'`;

export const siteverifyNodeSnippet = (secretKey = 'vf_secret_your_secret_key') => `const response = await fetch('${API_HOST}/api/siteverify', {
  method: 'POST',
  headers: {
    'X-API-Key': '${secretKey}',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ token: req.body.veriflowToken }),
});
const result = await response.json();

if (!result.success) {
  return res.status(400).json({ error: result['error-codes'] });
}
if (result.action === 'block') {
  return res.status(403).json({ error: 'Blocked by VeriFlow' });
}
// proceed — result.risk_score, result.action are trustworthy here`;

export const siteverifyPythonFlaskSnippet = (secretKey = 'vf_secret_your_secret_key') => `import requests

resp = requests.post(
    "${API_HOST}/api/siteverify",
    headers={"X-API-Key": "${secretKey}"},
    json={"token": request.json["veriflowToken"]},
)
result = resp.json()

if not result["success"]:
    return jsonify(error=result["error-codes"]), 400
if result["action"] == "block":
    return jsonify(error="Blocked by VeriFlow"), 403
# proceed — result["risk_score"], result["action"] are trustworthy here`;

export const siteverifyPythonDjangoSnippet = (secretKey = 'vf_secret_your_secret_key') => `import requests
from django.http import JsonResponse

def signup(request):
    resp = requests.post(
        "${API_HOST}/api/siteverify",
        headers={"X-API-Key": "${secretKey}"},
        json={"token": request.POST.get("veriflow_token")},
    )
    result = resp.json()
    if not result["success"] or result["action"] == "block":
        return JsonResponse({"error": "verification failed"}, status=403)
    # proceed with signup`;

export const siteverifyPhpSnippet = (secretKey = 'vf_secret_your_secret_key') => `<?php
$ch = curl_init("${API_HOST}/api/siteverify");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "X-API-Key: ${secretKey}",
    "Content-Type: application/json",
]);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
    "token" => $_POST["veriflow_token"],
]));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$result = json_decode(curl_exec($ch), true);
curl_close($ch);

if (!$result["success"] || $result["action"] === "block") {
    http_response_code(403);
    exit(json_encode(["error" => "verification failed"]));
}
// proceed with signup
?>`;

export const siteverifySuccessResponse = `{
  "success": true,
  "risk_score": 12,
  "action": "allow",
  "hostname": "example.com",
  "session_id": "b1e1...",
  "challenge_ts": 1752480000
}`;

export const siteverifyErrorResponse = `{
  "success": false,
  "error-codes": ["timeout-or-duplicate"]
}`;
