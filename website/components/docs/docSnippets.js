// Shared snippet templates for /docs and the dashboard key-creation modal.
// Keeping the backend-shape coupling (siteverify request/response, script
// tag attributes) in one file so both surfaces stay in sync.

export const CDN_URL = 'https://cdn.jsdelivr.net/npm/veilproof@1.1.6/dist/veilproof.min.js';
export const API_HOST = 'https://api.veilproof.tech';

// Note on the pattern below: `siteKey` is only passed explicitly by the
// dashboard, right after generating a real key — showing the literal value
// there is the point (copy-paste your actual key). Every other caller (the
// generic /docs guide) gets no argument and instead sees the site key read
// from that stack's own config/env convention. The site key isn't a secret
// (it ships in the browser bundle either way), but hardcoding it as a string
// literal in source you commit to git is still sloppy — config should own it,
// not a literal in every file that calls init().

export const scriptTagSnippet = (siteKey) => `<script src="${CDN_URL}"
        data-site-key="${siteKey || '{{ VEILPROOF_SITE_KEY }}'}"
        async defer></script>
${siteKey ? '' : '\n<!-- Render data-site-key from your server-side template/config (Django, EJS, Blade, WordPress option, etc.) — don\'t hardcode it in a committed HTML file. -->'}`;

export const scriptTagFormSnippet = (siteKey) => `<script src="${CDN_URL}"
        data-site-key="${siteKey || '{{ VEILPROOF_SITE_KEY }}'}"
        async defer></script>

<form data-veilproof action="/signup" method="post">
  <input name="email" type="email" required>
  <button type="submit">Sign up</button>
</form>`;

export const npmInstallSnippet = () => `npm install veilproof`;

export const npmInitSnippet = (siteKey) => `import VeilProof from 'veilproof';

// Read from your bundler's env convention (webpack DefinePlugin, dotenv, etc.)
// — never hardcode the key as a string literal in source.
VeilProof.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'process.env.VEILPROOF_SITE_KEY'} });

const result = await VeilProof.getToken();
// send result.token to your server for /api/siteverify`;

export const reactSnippet = (siteKey) => `import { useEffect } from 'react';
import VeilProof from 'veilproof';

// Vite: import.meta.env.VITE_VEILPROOF_SITE_KEY · CRA: process.env.REACT_APP_VEILPROOF_SITE_KEY
useEffect(() => {
  VeilProof.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'import.meta.env.VITE_VEILPROOF_SITE_KEY'} });
}, []);

async function handleSubmit(formData) {
  const { token } = await VeilProof.getToken();
  await fetch('/api/signup', {
    method: 'POST',
    body: JSON.stringify({ ...formData, veilproofToken: token }),
  });
}`;

export const nextjsSnippet = (siteKey) => `'use client';
import { useEffect } from 'react';
import VeilProof from 'veilproof';

export function VeilProofInit() {
  useEffect(() => {
    // NEXT_PUBLIC_* vars are inlined at build time — set this in .env.local,
    // never commit the literal key to source.
    VeilProof.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'process.env.NEXT_PUBLIC_VEILPROOF_SITE_KEY'} }); // client component only — SDK is SSR-safe (no-ops on the server)
  }, []);
  return null;
}`;

export const vueSnippet = (siteKey) => `<script setup>
import { onMounted } from 'vue';
import VeilProof from 'veilproof';

onMounted(() => {
  // Vite exposes import.meta.env.VITE_* — set VITE_VEILPROOF_SITE_KEY in .env
  VeilProof.init({ apiKey: ${siteKey ? `'${siteKey}'` : 'import.meta.env.VITE_VEILPROOF_SITE_KEY'} });
});

async function handleSubmit() {
  const { token } = await VeilProof.getToken();
  // send token to your server
}
</script>`;

export const siteverifyCurlSnippet = (secretKey = 'vp_secret_your_secret_key') => `curl -X POST ${API_HOST}/api/siteverify \\
  -H "X-API-Key: ${secretKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"token": "<token from the browser>"}'`;

export const siteverifyNodeSnippet = (secretKey = 'vp_secret_your_secret_key') => `const response = await fetch('${API_HOST}/api/siteverify', {
  method: 'POST',
  headers: {
    'X-API-Key': '${secretKey}',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ token: req.body.veilproofToken }),
});
const result = await response.json();

if (!result.success) {
  return res.status(400).json({ error: result['error-codes'] });
}
if (result.action === 'block') {
  return res.status(403).json({ error: 'Blocked by VeilProof' });
}
// proceed — result.risk_score, result.action are trustworthy here`;

export const siteverifyPythonFlaskSnippet = (secretKey = 'vp_secret_your_secret_key') => `import requests

resp = requests.post(
    "${API_HOST}/api/siteverify",
    headers={"X-API-Key": "${secretKey}"},
    json={"token": request.json["veilproofToken"]},
)
result = resp.json()

if not result["success"]:
    return jsonify(error=result["error-codes"]), 400
if result["action"] == "block":
    return jsonify(error="Blocked by VeilProof"), 403
# proceed — result["risk_score"], result["action"] are trustworthy here`;

export const siteverifyPythonDjangoSnippet = (secretKey = 'vp_secret_your_secret_key') => `import requests
from django.http import JsonResponse

def signup(request):
    resp = requests.post(
        "${API_HOST}/api/siteverify",
        headers={"X-API-Key": "${secretKey}"},
        json={"token": request.POST.get("veilproof_token")},
    )
    result = resp.json()
    if not result["success"] or result["action"] == "block":
        return JsonResponse({"error": "verification failed"}, status=403)
    # proceed with signup`;

export const siteverifyPhpSnippet = (secretKey = 'vp_secret_your_secret_key') => `<?php
$ch = curl_init("${API_HOST}/api/siteverify");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "X-API-Key: ${secretKey}",
    "Content-Type: application/json",
]);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
    "token" => $_POST["veilproof_token"],
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

export const siteverifyJavaSnippet = (secretKey = 'vp_secret_your_secret_key') => `RestTemplate rest = new RestTemplate();
HttpHeaders headers = new HttpHeaders();
headers.set("X-API-Key", "${secretKey}");
headers.setContentType(MediaType.APPLICATION_JSON);

Map<String, String> body = Map.of("token", request.getParameter("veilproofToken"));
ResponseEntity<Map> res = rest.postForEntity(
    "${API_HOST}/api/siteverify",
    new HttpEntity<>(body, headers),
    Map.class
);
Map result = res.getBody();

if (!(boolean) result.get("success") || "block".equals(result.get("action"))) {
    return ResponseEntity.status(403).body(Map.of("error", "Blocked by VeilProof"));
}
// proceed — result.get("risk_score"), result.get("action") are trustworthy here`;

export const siteverifyRubySnippet = (secretKey = 'vp_secret_your_secret_key') => `require 'net/http'
require 'json'

uri = URI("${API_HOST}/api/siteverify")
req = Net::HTTP::Post.new(uri, {
  'X-API-Key' => '${secretKey}',
  'Content-Type' => 'application/json'
})
req.body = { token: params[:veilproof_token] }.to_json
result = JSON.parse(Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) { |http| http.request(req) }.body)

if !result['success'] || result['action'] == 'block'
  render json: { error: 'Blocked by VeilProof' }, status: 403 and return
end
# proceed — result['risk_score'], result['action'] are trustworthy here`;

export const siteverifyGoSnippet = (secretKey = 'vp_secret_your_secret_key') => `body, _ := json.Marshal(map[string]string{"token": r.FormValue("veilproofToken")})
req, _ := http.NewRequest("POST", "${API_HOST}/api/siteverify", bytes.NewBuffer(body))
req.Header.Set("X-API-Key", "${secretKey}")
req.Header.Set("Content-Type", "application/json")

resp, _ := http.DefaultClient.Do(req)
var result map[string]interface{}
json.NewDecoder(resp.Body).Decode(&result)

if success, _ := result["success"].(bool); !success || result["action"] == "block" {
    http.Error(w, "Blocked by VeilProof", http.StatusForbidden)
    return
}
// proceed — result["risk_score"], result["action"] are trustworthy here`;

export const siteverifyCsharpSnippet = (secretKey = 'vp_secret_your_secret_key') => `using var client = new HttpClient();
client.DefaultRequestHeaders.Add("X-API-Key", "${secretKey}");

var payload = JsonSerializer.Serialize(new { token = Request.Form["veilproofToken"] });
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
// proceed — result["risk_score"], result["action"] are trustworthy here`;

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
