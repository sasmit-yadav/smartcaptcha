# P2 red-team label schema (JSONL)

Each line in `tools/redteam/out/*.jsonl` is one session probe.

## Required fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | `"veilproof.redteam.v1"` |
| `ts` | string | ISO-8601 UTC |
| `stack` | string | `camoufox` \| `rebrowser` \| `playwright_js_stealth` |
| `variant` | string | e.g. `camoufox_humanize` |
| `label` | string | always `"bot"` for these probes |
| `label_source` | string | `"redteam_probe"` |
| `result` | string | `BLOCKED` \| `ALLOWED` \| `ERROR` \| `SKIP` |
| `known_gap` | bool | true when ALLOWED (detector miss) |
| `base_url` | string | demo URL hit |
| `api_host` | string | usually `api.veilproof.tech` |
| `predict` | object\|null | `{ action, risk_score, fingerprint_score, behavior_score, network_score?, session_id? }` |
| `status_text` | string | UI status from demo |
| `run_id` | string | uuid for this process batch |
| `attempt` | int | 1-based index within batch |

## Optional

| Field | Type | Description |
|---|---|---|
| `error` | string | exception message |
| `sdk_version` | string | if observed |
| `automation_signals` | any | if present on predict body |
| `notes` | string | free text |

## Files

- `out/camoufox_YYYYMMDD.jsonl` — append-only Camoufox runs
- `out/rebrowser_YYYYMMDD.jsonl` — append-only rebrowser runs
- `out/summary_YYYYMMDD.json` — batch counts (written by `collect_p2.py`)

`out/` is gitignored. Keep N≥50 Camoufox sessions before P2.2 ingest.
