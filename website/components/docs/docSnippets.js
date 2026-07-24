// Shared snippet templates for /docs and the dashboard key-creation modal.
// Keeping the backend-shape coupling (siteverify request/response, script
// tag attributes) in one file so both surfaces stay in sync.
//
// CRITICAL: classic HTML forms inject the token as name="veilproof-token"
// (hyphen). JSON APIs usually rename it on the way to your server — but
// when you read a normal form POST, use "veilproof-token".

export const CDN_URL = 'https://cdn.jsdelivr.net/npm/veilproof@1.1.10/dist/veilproof.min.js';
export const API_HOST = 'https://api.veilproof.tech';

/** Secret key expression for snippets: real key (dashboard) or env placeholder (docs). */
function secretExpr(secretKey, style) {
  if (secretKey) {
    if (style === 'php') return secretKey;
    if (style === 'env_php') return secretKey;
    return `'${secretKey}'`;
  }
  switch (style) {
    case 'node':
      return 'process.env.VEILPROOF_SECRET_KEY';
    case 'python':
      return 'os.environ["VEILPROOF_SECRET_KEY"]';
    case 'php':
      return 'getenv("VEILPROOF_SECRET_KEY")';
    case 'java':
      return 'System.getenv("VEILPROOF_SECRET_KEY")';
    case 'ruby':
      return 'ENV["VEILPROOF_SECRET_KEY"]';
    case 'go':
      return 'os.Getenv("VEILPROOF_SECRET_KEY")';
    case 'csharp':
      return 'Environment.GetEnvironmentVariable("VEILPROOF_SECRET_KEY")';
    case 'curl':
      return '$VEILPROOF_SECRET_KEY';
    default:
      return 'YOUR_SECRET_KEY';
  }
}

// Note: `siteKey` is only passed explicitly by the dashboard right after
// generating a real key. Generic /docs callers omit it and show a template
// placeholder so people render the key from config, not a committed literal.

export const scriptTagSnippet = (siteKey) => `<script
  src="${CDN_URL}"
  data-site-key="${siteKey || 'vp_site_YOUR_SITE_KEY'}"
  async
  defer
></script>
<!--
  Required: data-site-key = your public site key from the dashboard.
  Optional: data-endpoint="https://api.veilproof.tech" (already the SDK default)
  Optional: data-debug="true" (console logs while integrating — remove in prod)
  Optional: data-token-field="veilproof-token" (default hidden field name)
-->`;

export const scriptTagFormSnippet = (siteKey) => `<!-- 1) Load SDK once on the page -->
<script
  src="${CDN_URL}"
  data-site-key="${siteKey || 'vp_site_YOUR_SITE_KEY'}"
  async
  defer
></script>

<!-- 2) Mark the form. SDK intercepts submit, injects hidden field, then submits. -->
<form data-veilproof action="/signup" method="post">
  <input name="email" type="email" required>
  <button type="submit">Sign up</button>
  <!-- SDK adds: <input type="hidden" name="veilproof-token" value="..."> -->
</form>

<!-- 3) On your server, read POST field "veilproof-token" and call /api/siteverify -->`;

export const htmlCompleteSnippet = (siteKey) => `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Protected form</title>
  <script
    src="${CDN_URL}"
    data-site-key="${siteKey || 'vp_site_YOUR_SITE_KEY'}"
    async
    defer
  ></script>
</head>
<body>
  <form data-veilproof action="/signup" method="post">
    <input name="email" type="email" required placeholder="you@example.com" />
    <button type="submit">Sign up</button>
  </form>
</body>
</html>`;

export const programmaticHtmlSnippet = (siteKey) => `<!-- Load SDK (same as above) -->
<script
  src="${CDN_URL}"
  data-site-key="${siteKey || 'vp_site_YOUR_SITE_KEY'}"
  async
  defer
></script>

<form id="signup">
  <input id="email" name="email" type="email" required />
  <button type="submit">Sign up</button>
</form>

<script>
  document.getElementById('signup').addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!window.VeilProof) {
      alert('VeilProof SDK failed to load — check the script URL / CSP');
      return;
    }

    // getToken talks to ${API_HOST}/api/predict (signed) and returns a token
    window.VeilProof.getToken(async (result) => {
      if (!result.token) {
        console.error('VeilProof error', result.error);
        return;
      }

      // Send token to YOUR backend (never call siteverify with the secret from the browser)
      const res = await fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: document.getElementById('email').value,
          veilproofToken: result.token,
        }),
      });

      if (!res.ok) {
        alert('Blocked or verification failed');
        return;
      }
      alert('OK');
    });
  });
</script>`;

export const npmInstallSnippet = () => `npm install veilproof@1.1.10`;

export const npmInitSnippet = (siteKey) => `import VeilProof from 'veilproof';

// Site key only (vp_site_...). Never pass vp_secret_ here — init will refuse.
VeilProof.init({
  apiKey: ${siteKey ? `'${siteKey}'` : 'process.env.VEILPROOF_SITE_KEY'},
  // endpoint: '${API_HOST}', // optional — this is already the default
});

const result = await VeilProof.getToken();
if (!result.token) {
  throw new Error(result.error || 'VeilProof getToken failed');
}
// POST result.token to your server; your server calls /api/siteverify`;

export const reactSnippet = (siteKey) => `import { useEffect } from 'react';
import VeilProof from 'veilproof';

// Vite: import.meta.env.VITE_VEILPROOF_SITE_KEY
// CRA:  process.env.REACT_APP_VEILPROOF_SITE_KEY
useEffect(() => {
  VeilProof.init({
    apiKey: ${siteKey ? `'${siteKey}'` : 'import.meta.env.VITE_VEILPROOF_SITE_KEY'},
  });
}, []);

async function handleSubmit(formData) {
  const { token, error } = await VeilProof.getToken();
  if (!token) {
    console.error('VeilProof', error);
    return;
  }
  await fetch('/api/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...formData, veilproofToken: token }),
  });
}`;

export const nextjsSnippet = (siteKey) => `'use client';
import { useEffect } from 'react';
import VeilProof from 'veilproof';

export function VeilProofInit() {
  useEffect(() => {
    // Set NEXT_PUBLIC_VEILPROOF_SITE_KEY in .env.local (client-visible on purpose)
    VeilProof.init({
      apiKey: ${siteKey ? `'${siteKey}'` : 'process.env.NEXT_PUBLIC_VEILPROOF_SITE_KEY'},
    });
  }, []);
  return null;
}

// In a Server Action / Route Handler, verify with VEILPROOF_SECRET_KEY (no NEXT_PUBLIC_)`;

export const vueSnippet = (siteKey) => `<script setup>
import { onMounted } from 'vue';
import VeilProof from 'veilproof';

onMounted(() => {
  VeilProof.init({
    apiKey: ${siteKey ? `'${siteKey}'` : 'import.meta.env.VITE_VEILPROOF_SITE_KEY'},
  });
});

async function handleSubmit() {
  const { token, error } = await VeilProof.getToken();
  if (!token) {
    console.error('VeilProof', error);
    return;
  }
  // POST { veilproofToken: token } to your server
}
</script>`;

export const siteverifyCurlSnippet = (secretKey) => `curl -X POST ${API_HOST}/api/siteverify \\
  -H "X-API-Key: ${secretKey || '$VEILPROOF_SECRET_KEY'}" \\
  -H "Content-Type: application/json" \\
  -d '{"token":"PASTE_TOKEN_FROM_BROWSER_HERE"}'

# Expect JSON with success + action. Always check action !== "block".
# HTTP status is often 200 even when success is false — read the JSON body.`;

export const siteverifyNodeSnippet = (secretKey) => `// Express example — secret key from env, never from the browser
import express from 'express';

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false })); // needed for classic HTML form posts

app.post('/api/signup', async (req, res) => {
  // JSON clients:     req.body.veilproofToken
  // data-veilproof forms: req.body['veilproof-token']
  const token = req.body.veilproofToken || req.body['veilproof-token'];
  if (!token) {
    return res.status(400).json({ error: 'Missing VeilProof token' });
  }

  const response = await fetch('${API_HOST}/api/siteverify', {
    method: 'POST',
    headers: {
      'X-API-Key': ${secretExpr(secretKey, 'node')},
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
  });
  const result = await response.json();

  // success = token is real/unreplayed. action = allow|block (the bot verdict).
  if (!result.success) {
    return res.status(400).json({ error: result['error-codes'] || 'invalid token' });
  }
  if (result.action === 'block') {
    return res.status(403).json({ error: 'Blocked by VeilProof' });
  }

  // Safe to run your business logic here
  return res.json({ ok: true });
});`;

export const siteverifyPythonFlaskSnippet = (secretKey) => `import os
import requests
from flask import request, jsonify

@app.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    # JSON: veilproofToken · HTML form: veilproof-token
    token = data.get("veilproofToken") or request.form.get("veilproof-token")
    if not token:
        return jsonify(error="Missing VeilProof token"), 400

    resp = requests.post(
        "${API_HOST}/api/siteverify",
        headers={"X-API-Key": ${secretKey ? `"${secretKey}"` : 'os.environ["VEILPROOF_SECRET_KEY"]'}},
        json={"token": token},
        timeout=10,
    )
    result = resp.json()

    if not result.get("success"):
        return jsonify(error=result.get("error-codes")), 400
    if result.get("action") == "block":
        return jsonify(error="Blocked by VeilProof"), 403

    # proceed with signup
    return jsonify(ok=True)`;

export const siteverifyPythonDjangoSnippet = (secretKey) => `import os
import requests
from django.http import JsonResponse

def signup(request):
    token = request.POST.get("veilproof-token") or request.POST.get("veilproofToken")
    if request.content_type == "application/json":
        import json
        body = json.loads(request.body.decode() or "{}")
        token = token or body.get("veilproofToken")

    if not token:
        return JsonResponse({"error": "Missing VeilProof token"}, status=400)

    resp = requests.post(
        "${API_HOST}/api/siteverify",
        headers={"X-API-Key": ${secretKey ? `"${secretKey}"` : 'os.environ["VEILPROOF_SECRET_KEY"]'}},
        json={"token": token},
        timeout=10,
    )
    result = resp.json()
    if not result.get("success") or result.get("action") == "block":
        return JsonResponse({"error": "verification failed"}, status=403)
    # proceed with signup
    return JsonResponse({"ok": True})`;

export const siteverifyPhpSnippet = (secretKey) => `<?php
// Read token from classic form (data-veilproof) or JSON body
$raw = file_get_contents('php://input');
$json = json_decode($raw, true) ?: [];
$token = $_POST['veilproof-token']
      ?? $json['veilproofToken']
      ?? null;

if (!$token) {
    http_response_code(400);
    exit(json_encode(['error' => 'Missing VeilProof token']));
}

$ch = curl_init('${API_HOST}/api/siteverify');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => [
        'X-API-Key: ' . ${secretKey ? `"${secretKey}"` : 'getenv("VEILPROOF_SECRET_KEY")'},
        'Content-Type: application/json',
    ],
    CURLOPT_POSTFIELDS => json_encode(['token' => $token]),
    CURLOPT_RETURNTRANSFER => true,
]);
$result = json_decode(curl_exec($ch), true);
curl_close($ch);

if (empty($result['success']) || ($result['action'] ?? '') === 'block') {
    http_response_code(403);
    exit(json_encode(['error' => 'verification failed']));
}
// proceed with signup
`;

export const siteverifyJavaSnippet = (secretKey) => `RestTemplate rest = new RestTemplate();
HttpHeaders headers = new HttpHeaders();
headers.set("X-API-Key", ${secretKey ? `"${secretKey}"` : 'System.getenv("VEILPROOF_SECRET_KEY")'});
headers.setContentType(MediaType.APPLICATION_JSON);

// HTML form field is "veilproof-token"; JSON APIs often send "veilproofToken"
String token = request.getParameter("veilproof-token");
if (token == null) token = request.getParameter("veilproofToken");

Map<String, String> body = Map.of("token", token);
ResponseEntity<Map> res = rest.postForEntity(
    "${API_HOST}/api/siteverify",
    new HttpEntity<>(body, headers),
    Map.class
);
Map result = res.getBody();

if (!(boolean) result.get("success") || "block".equals(result.get("action"))) {
    return ResponseEntity.status(403).body(Map.of("error", "Blocked by VeilProof"));
}
// proceed`;

export const siteverifyRubySnippet = (secretKey) => `require 'net/http'
require 'json'

token = params['veilproof-token'] || params[:veilproofToken]
uri = URI('${API_HOST}/api/siteverify')
req = Net::HTTP::Post.new(uri, {
  'X-API-Key' => ${secretKey ? `'${secretKey}'` : 'ENV["VEILPROOF_SECRET_KEY"]'},
  'Content-Type' => 'application/json'
})
req.body = { token: token }.to_json
result = JSON.parse(Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) { |http| http.request(req) }.body)

if !result['success'] || result['action'] == 'block'
  render json: { error: 'Blocked by VeilProof' }, status: 403 and return
end
# proceed`;

export const siteverifyGoSnippet = (secretKey) => `token := r.FormValue("veilproof-token")
if token == "" {
    token = r.FormValue("veilproofToken")
}
body, _ := json.Marshal(map[string]string{"token": token})
req, _ := http.NewRequest("POST", "${API_HOST}/api/siteverify", bytes.NewBuffer(body))
req.Header.Set("X-API-Key", ${secretKey ? `"${secretKey}"` : 'os.Getenv("VEILPROOF_SECRET_KEY")'})
req.Header.Set("Content-Type", "application/json")

resp, err := http.DefaultClient.Do(req)
if err != nil {
    http.Error(w, "verify unavailable", http.StatusServiceUnavailable)
    return
}
defer resp.Body.Close()
var result map[string]interface{}
json.NewDecoder(resp.Body).Decode(&result)

success, _ := result["success"].(bool)
if !success || result["action"] == "block" {
    http.Error(w, "Blocked by VeilProof", http.StatusForbidden)
    return
}
// proceed`;

export const siteverifyCsharpSnippet = (secretKey) => `using var client = new HttpClient();
client.DefaultRequestHeaders.Add("X-API-Key", ${secretKey ? `"${secretKey}"` : 'Environment.GetEnvironmentVariable("VEILPROOF_SECRET_KEY")'});

// HTML form: veilproof-token · JSON body: veilproofToken
var token = Request.Form["veilproof-token"].ToString();
if (string.IsNullOrEmpty(token))
{
    token = Request.Form["veilproofToken"].ToString();
}

var payload = JsonSerializer.Serialize(new { token });
var response = await client.PostAsync(
    "${API_HOST}/api/siteverify",
    new StringContent(payload, Encoding.UTF8, "application/json")
);
var result = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(
    await response.Content.ReadAsStringAsync()
);

if (!result["success"].GetBoolean() || result["action"].GetString() == "block")
{
    return StatusCode(403, new { error = "Blocked by VeilProof" });
}
// proceed`;

export const siteverifySuccessResponse = `{
  "success": true,
  "risk_score": 12,
  "action": "allow",
  "hostname": "example.com",
  "session_id": "b1e1...",
  "challenge_ts": 1752480000
}`;

export const siteverifyBlockedResponse = `{
  "success": true,
  "risk_score": 97,
  "action": "block",
  "hostname": "example.com",
  "session_id": "a92f...",
  "challenge_ts": 1752480000
}`;

export const siteverifyErrorResponse = `{
  "success": false,
  "error-codes": ["timeout-or-duplicate"]
}`;

export const predictAllowResponse = `{
  "action": "allow",
  "risk_score": 10,
  "behavior_score": 26,
  "fingerprint_score": 0,
  "confidence": 0.8,
  "verification_token": "eyJhbGciOiJIUzI1NiIs..."
}`;

export const predictBlockResponse = `{
  "action": "block",
  "risk_score": 97,
  "behavior_score": 92,
  "fingerprint_score": 100,
  "confidence": 0.94,
  "verification_token": "eyJhbGciOiJIUzI1NiIs..."
}`;
