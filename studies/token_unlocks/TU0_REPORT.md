# Token unlocks — TU-0 feasibility: **BLOCKED (no data source reachable)**

29 Oct 2026. No prices, no returns, nothing computed. No event list exists yet.

## What was tried
| Source | Result |
|---|---|
| `git clone https://github.com/DefiLlama/emissions-adapters` (read-only, outside our repo) | refused: the session's git proxy asks for credentials ("could not read Username for 'https://github.com'") |
| Attaching the repo to the session (read access) | refused: "you don't have access to defillama/emissions-adapters" (this session's GitHub credential does not cover it) |
| `defillama-datasets.llama.fi` (the files the public site uses), `api.llama.fi`, `defillama.com` | refused by the environment's network policy (proxy connect rejected) |

The session's rules also forbid reading GitHub repositories that are not attached to it, so the code was not fetched by any other route (tarball, raw files, API).

## What would unblock it (one of)
1. **Fork `DefiLlama/emissions-adapters` into the viter999 account** (or another account where the Claude GitHub App is installed), then attach the fork read-only. The fork keeps the full git history, which TU-0 step 2 (point-in-time check) needs.
2. **Allow `defillama-datasets.llama.fi`** in the environment's Network access settings (Allowed domains). This gives the built JSON the public site uses, but **no git history**, so the point-in-time check (when each schedule was written) would not be possible from it.

Option 1 is the only one that answers all four TU-0 questions.

## Not done
Steps 1–4 (schedule extraction, point-in-time history check, event list and counts, matching to Binance USDT-M perps). The Binance archive listing needed for the matching is already available from crash-absorption.

## Update — 29 Oct 2026: revised source (public DefiLlama unlock pages) — still BLOCKED
- The emissions-adapters route is dropped (the repo is no longer public).
- `defillama.com` is now allowed by the network policy (the proxy connects), but `GET https://defillama.com/unlocks` with a descriptive User-Agent returns **HTTP 403 from Cloudflare** with `cf-mitigated: challenge` — a managed "Just a moment… Enable JavaScript and cookies to continue" challenge. The `/_next/data/<buildId>/unlocks/<slug>.json` route needs the buildId from that page and is served by the same Cloudflare zone.
- Not attempted: solving or bypassing the challenge (e.g. with a headless browser). The site deliberately blocks non-browser clients; getting around that would be bot-detection evasion.
- Nothing was fetched, cached or computed; no event list exists.

### Ways forward (Shawn's choice)
1. **Shawn exports the data from his own browser** (as with the REST funding): save the `/unlocks` page's `__NEXT_DATA__` JSON and each protocol's JSON, commit them raw with their sha256 and fetch time on a separate data branch; I then verify the hashes and run the extraction offline.
2. **Allow `defillama-datasets.llama.fi`** (the static dataset host the site reads from; still refused by the proxy here) and check whether it serves the emissions files without a challenge.
3. **DefiLlama Pro API** (paid; would need an API key stored as an environment secret).
