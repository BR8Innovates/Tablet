# Trialx Postman collections: Portal Integration APIs

Postman collections for all 34 APIs in the *Portal Integration API Specification* v0.2, set up for InsureMO tenant `trialx`.

| File | What it is |
|---|---|
| `Trialx-Portal-APIs-Mandatory.postman_collection.json` | Each API with **mandatory fields only** |
| `Trialx-Portal-APIs-Full-Optional.postman_collection.json` | Each API with **mandatory and optional fields**, plus conditional variants (for example FNOL with a manual policy) |
| `Trialx.postman_environment.json` | Trialx environment: `baseUrl` is `https://portal-gw.insuremo.com` and `tenantCode` is `trialx`. Fill in `username` and `password`. |
| `STRUCTURE-CHECK.md` | Which API structures do not work, and why |
| `results/` | Newman run results against trialx |
| `build_collections.py` | Generator that produces the collections and environment. Edit it and re-run `python3 build_collections.py`. |
| `summarize_run.py` | Turns a Newman JSON report into a per-API verdict table |

## What is in each collection

- **One folder per API (API-01 to API-34).** Each request carries:
  - Saved examples with the spec's sample responses, plus responses observed on trialx (404 and 401 gateway errors, the get-token error shapes).
  - A description with a *Fields bound to code tables / data tables* table.
  - Structure tests. A failing test names the field or envelope that differs from the spec.
- **Token handling.** A collection pre-request script calls API-02 `/cas/get-token` when no token is cached or it is about to expire.
- **ID chaining.** Search APIs store the signed IDs, comma URL-encoded as `%2C`, that the load APIs need:

  | Search API | Sets | Used by |
  |---|---|---|
  | API-01 | `channelId` | API-04, API-05 |
  | API-06 | `collectionId` | API-07, API-08 |
  | API-17 | `quotePolicyId` | API-13 |
  | API-20 | `policyId`, `PolicyNo` | API-21, API-32 |
  | API-14 | `attachFileId` | API-24, API-27 |
  | API-29 | `claimNo`, `clmPolicyId` | API-30, API-31 |

- **Datatable and LoadTables folder**:
  - **Code Tables (LoadTables):** one request per code table bound to an API field (99 tables), plus a *Load ALL* request that loads every table in one call and lists any missing on trialx in `codeTablesMissing`. The folder description maps every table to the API fields that use it.
  - **Service-backed Code Tables:** UserInfo, PubBranch, Products, SalesChannelAPI, SalesAgreementAPI and ProductElementIdAPI.
  - **Data Tables:** Load Product and Load Plan (API-10), plus the runtime data-by-name read.
  - **Rate and Config Tables:** the package table (API-11).

## Use

1. In Postman, import both collections and the environment, then select **Trialx (InsureMO)**.
2. Set `username` and `password` to a trialx Machine User.
3. Run the collection in order with the Collection Runner, or with Newman:

```bash
newman run Trialx-Portal-APIs-Mandatory.postman_collection.json -e Trialx.postman_environment.json \
  --env-var username=<user> --env-var password=<password> \
  --reporters cli,json --reporter-json-export run.json
python3 summarize_run.py run.json
```

The following requests create data or send messages on trialx, so leave them out of runs where that is not wanted:

- API-22 Upload Document
- API-28 FNOL
- SMS and email sends (API-03, API-15, API-16, API-34)
