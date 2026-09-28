# Trialx Postman collection: Portal Integration APIs

**One** Postman collection for all 34 APIs in the *Portal Integration API Specification* v0.2, set up for InsureMO tenant `trialx`.

| File | What it is |
|---|---|
| `Trialx-Portal-APIs.postman_collection.json` | All 34 APIs. Each API folder has a **Mandatory** request and, where the API has optional fields, a **Full (+ Optional)** request. |
| `Trialx.postman_environment.json` | Trialx environment: `baseUrl` is `https://portal-gw.insuremo.com`, `tenantCode` is `trialx`. Fill in `username` and `password`. |
| `STRUCTURE-CHECK.md` | Spec issues found by reading the docs, and which routes 404 on trialx before you even add a token |
| `results/` | Newman run results against trialx |
| `build_collections.py` | Generator that produces the collection and environment from scratch (no examples). Edit it and re-run `python3 build_collections.py`. |
| `attach_live_examples.py` | Attaches real captured trialx responses (from a Newman JSON report) onto the collection `build_collections.py` just wrote, as saved Postman examples. Run it after `build_collections.py`, pointed at a run report: `python3 attach_live_examples.py run.json`. |
| `summarize_run.py` | Turns a Newman JSON report into a per-request PASS / error / doc-update table |

## Naming: working requests first, "(Pending)" at the end of the name for anything not confirmed working

A plain request name (e.g. `Search Sales Channel Pool — Mandatory`) means it returned a real 2xx response matching the spec on the 28 Sep 2026 run. Anything else has its name suffixed **`(Pending)`** — `Ratetable Lookup — Mandatory (Pending)` — so you never have to open a request to know whether it works.

**Working requests are sorted first in every folder, and folders with a lower fraction of pending requests sort before folders with more** — so the whole collection reads working-first, top to bottom, and a folder that's 96% working (e.g. Datatable and LoadTables, 4 pending of 101) sorts ahead of a 2-item folder that's 100% broken, not after it just because 4 > 2.

| State | Count (28 Sep, after fixes + new test data + sourced CustomerIds) | Meaning |
|---|---|---|
| Plain name (no suffix) | 148 | 2xx, `Status` not `BLOCK`, and the response shape matched the spec — the only state that means "works as documented" |
| `(Pending)`, REJECTED | 22 | trialx returned a 4xx/5xx other than 401/403/404 — this run included the SMS/Email sends (see below); every one of these needs either data this collection cannot fully obtain on its own (a data/rate table name only the Config team has), or a fix outside this collection (the broken trialx SNS endpoint) |
| `(Pending)`, STRUCTURE FAIL | 10 | 2xx, but the response shape differs from the spec (documented, known nuances — e.g. an array field omitted on an empty result set), **or** a well-formed `Status: "BLOCK"` (API-28 FNOL: blocked by a real, confirmed tenant permission error - see `STRUCTURE-CHECK.md` §7) |
| `(Pending)`, ROUTE MISSING | 10 | trialx returned 404 — the spec's own path is wrong; the working alternative is included as a separate, plain-named request |

`API-18`/`API-19` Load Customer are now confirmed working (real `CustomerId` sourced from an undocumented-but-real customer search endpoint, `POST /platform/custv2/v1/query` with `Module: "Customer"`) — see `STRUCTURE-CHECK.md` §9.

Every `(Pending)` request still carries a real saved example — the exact response trialx sent — but that example is evidence of what happened, not proof of success; open its Examples tab to see why it's pending. Nothing here is invented: no spec sample JSON, no placeholder data, and any `access_token` inside a body is redacted before it's saved. **This run included every SMS/Email send** (unlike earlier runs, which excluded them by convention) — none dispatched a real message: every send attempt returned HTTP 499 against trialx's own confirmed-broken SNS endpoint (`STRUCTURE-CHECK.md` §8), and the destination is still the placeholder `{{mobileNo}}`, never a real number. Exclude the SMS/Email folders from a run if you'd rather not depend on that broken endpoint responding. `results/2026-09-28-live-run-with-new-data.md` and `STRUCTURE-CHECK.md` §5-9 have the same findings written out.

**Upload Document (API-22) now runs by default and creates a new, clearly-labeled test attachment on trialx every time.** That's intentional — it's what unlocked Download Document and Load All Document Versions — but it means running the full collection repeatedly keeps adding small test files under claim `CRPO01_RK202600000308`. Exclude it from a run if that's not wanted. **Submit FNOL (API-28) is included too but never creates anything**: the Machine User this collection is configured for has no permission to create a claim, confirmed on every attempt, so it always comes back `(Pending)` with a real, well-formed `BLOCK` response - safe to leave in a run.

**Query and body parameters are real, literal values, not `{{placeholders}}`** — e.g. `productCode=FCMOTOR`, `"BusinessType": "001"` — everywhere a confirmed real value exists, so a request is ready to run as soon as you add a token, with no environment variables to fill in first. The only things still templated are auth/connection plumbing (`{{baseUrl}}`, `{{access_token}}`, `{{username}}`, `{{password}}`) and the IDs a prior request's test script sets live from its own real response (`{{channelId}}`, `{{policyId}}`, `{{claimNo}}`, ...) — those have to stay templated, or the automatic chaining described below stops working. A parameter with no confirmed real value (a data/rate table name the Config team hasn't provided) is left as `{{placeholder}}` on purpose, rather than silently blanked to an empty string.

`build_collections.py` on its own still writes a clean, unordered collection with **no** examples and **no `(Pending)` tags**, only structure tests and inlined values — that's the base you get from the spec alone. Run `attach_live_examples.py <run.json>` any time you want the tags, ordering, and saved examples to reflect a newer trialx run (it overwrites the previous tag, position, and example for every request in the new run).

## Data used at runtime is real trialx data, not invented data

Search requests (API-01, API-06, API-17, API-20, API-14, API-29, ...) store the signed IDs and other values **from their own live trialx response** into collection variables, and the load requests that follow (API-04, API-05, API-07, API-08, API-13, API-21, API-24, API-27, API-30, API-31, ...) reuse them. Nothing is hard-coded from the spec's sample data — the chain only works once trialx actually returns matching records for your test data (a real channel, a real policy, a real collection, and so on).

| Search request | Sets | Used by |
|---|---|---|
| API-01 | `channelId` | API-04, API-05 |
| API-06 | `collectionId` | API-07, API-08 |
| API-17 | `quotePolicyId` | API-13 |
| API-20 | `policyId`, `PolicyNo` | API-21, API-32 |
| API-14 | `attachFileId` | API-24, API-27 |
| API-29 | `claimNo`, `clmPolicyId` | API-30, API-31 |

## Datatable and LoadTables folder

- **Code Tables (LoadTables):** one request per code table bound to an API field (99 tables), plus a *Load ALL* request that loads every table in one call and lists any missing on trialx in `codeTablesMissing`. The folder description maps every table to the API fields that use it. No values are pre-filled — the request reads whatever trialx has configured.
- **Service-backed Code Tables:** UserInfo, PubBranch, Products, SalesChannelAPI, SalesAgreementAPI and ProductElementIdAPI.
- **Data Tables:** Load Product and Load Plan (API-10), plus the runtime data-by-name read.
- **Rate and Config Tables:** the package table (API-11).

## Use

1. In Postman, import the collection and the environment, then select **Trialx (InsureMO)**.
2. Set `username` and `password` to a trialx Machine User.
3. Run the collection in order with the Collection Runner, or with Newman:

```bash
newman run Trialx-Portal-APIs.postman_collection.json -e Trialx.postman_environment.json \
  --env-var username=<user> --env-var password=<password> \
  --reporters cli,json --reporter-json-export run.json
python3 summarize_run.py run.json > results/run-$(date +%F).md
```

`summarize_run.py` gives one row per request: HTTP code, verdict (`OK`, `STRUCTURE FAIL`, `ROUTE MISSING`, `NO TOKEN`, `NO PERMISSION`, `REJECTED`), the exact next action, which checks failed, and the response body trialx sent back. Send me that file (or the raw `run.json`) and I will tell you, per request, whether it's a real problem on trialx or something the spec document needs to be corrected for.

**API-22 Upload Document creates a new, clearly-labeled test file attachment on trialx every time it runs** (see the note above) - leave it out of a run if that's not wanted. **API-28 FNOL never creates anything** (permission-blocked, confirmed - see `STRUCTURE-CHECK.md` §7), so it's safe to leave in. **SMS and email sends (API-03, API-15, API-16, API-34) are excluded by default** and not in this collection's default run at all - those dispatch real messages, a different risk category from a test record.
