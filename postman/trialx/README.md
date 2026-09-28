# Trialx Postman collection: Portal Integration APIs

**One** Postman collection for all 34 APIs in the *Portal Integration API Specification* v0.2, set up for InsureMO tenant `trialx`.

| File | What it is |
|---|---|
| `Trialx-Portal-APIs.postman_collection.json` | All 34 APIs. Each API folder has a **Mandatory** request and, where the API has optional fields, a **Full (+ Optional)** request. |
| `Trialx.postman_environment.json` | Trialx environment: `baseUrl` is `https://portal-gw.insuremo.com`, `tenantCode` is `trialx`. Fill in `username` and `password`. |
| `STRUCTURE-CHECK.md` | Spec issues found by reading the docs, and which routes 404 on trialx before you even add a token |
| `results/` | Newman run results against trialx |
| `build_collections.py` | Generator that produces the collection and environment. Edit it and re-run `python3 build_collections.py`. |
| `summarize_run.py` | Turns a Newman JSON report into a per-request PASS / error / doc-update table |

## No example responses anywhere in this collection

**Nothing in this collection is invented.** No request carries a saved "example" response — not the spec's sample JSON, not anything I generated. Every request has only:

- the request itself (built from the spec's field tables), and
- structure tests that run against whatever trialx actually returns.

A request only shows **PASS** in Postman when trialx itself returns a 2xx response whose shape matches the spec. Anything else — 401, 403, 404, a 2xx with a different shape, a rejected field — shows as a failing test that names exactly what came back, so you can see the real trialx behaviour and tell a genuine error apart from a place where the specification document itself needs correcting.

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

The following requests create data or send messages on trialx, so leave them out of runs where that is not wanted:

- API-22 Upload Document
- API-28 FNOL (both requests)
- SMS and email sends (API-03, API-15, API-16, API-34)
