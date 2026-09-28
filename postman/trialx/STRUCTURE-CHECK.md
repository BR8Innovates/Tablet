# Trialx API structure check

Source: *Portal Integration API Specification* v0.2 (API-01 to API-34).
Target: InsureMO tenant `trialx`. The gateway is `https://portal-gw.insuremo.com` and the tenant domain is `trialx-gimc.insuremo.com`.
Date: 28 Sep 2026.

## How it was checked

1. **Live route check on trialx.** I ran every request in `Trialx-Portal-APIs.postman_collection.json` with Newman, without credentials. The gateway returns **401** when a route exists but needs a token, and **404** when the path is wrong or the API is not published. This checks routing only, not request bodies or response shapes. Full output: [`results/2026-09-28-route-check-no-credentials.md`](results/2026-09-28-route-check-no-credentials.md). No response shown anywhere in this repo is invented — everything logged came back from an actual call to `https://portal-gw.insuremo.com`.
2. **Spec review.** I compared each API's request table, samples and response tables for contradictions.
3. **Not done yet: body and response structure on trialx.** This needs a trialx Machine User. See [Pending](#pending-live-body--response-check).

## Summary

| Status | APIs |
|---|---|
| **Not working on trialx: route missing (HTTP 404)** | API-05 (spec path), API-15, API-16, API-34 Option A |
| **Works differently from the spec** | API-02 |
| **Spec structure contradicts itself (needs confirmation)** | API-06, API-09, API-11, API-17, API-20 |
| **Spec structure incomplete ("to be confirmed")** | API-14, API-22, API-23, API-25, API-26, API-27, API-28, API-29, API-30, API-31, API-32, API-33, API-18, API-19 |
| Route exists on trialx (401 without token); structure consistent in spec | API-01, API-03, API-04, API-07, API-08, API-10, API-12, API-13, API-21, API-24 |

## 1. Not working on trialx: route missing

| API | Spec endpoint | Result on trialx | Fix in the collection |
|---|---|---|---|
| API-05 Load Sales Agreements by Channel ID | `GET /api/platform/saleschannel/agreement/load/byChannelId` | **404** `404 page not found`. The gateway does not route the `/api` prefix. | Added the SDK path `GET /platform/saleschannel/core/agreement/load/byChannelId`, which is routed (401). The spec already lists it as the SDK equivalent. |
| API-15 Email Quote | `POST /comm/v1/notifications/send` | **404**. `/platform/comm/v1/notifications/send` also returns 404. The spec gives no request contract for it. | Kept it as a placeholder request (contract to be confirmed). Added the documented SNS alternative `POST /mo-fo/1.0/sns/email/send` (routed, 401). |
| API-16 SMS Quote | `POST /comm/v1/notifications/send` | **404**, no contract | Same approach. Added SNS `POST /mo-fo/1.0/sns/sms/send` (routed, 401). |
| API-34 Option A, OTP via Notifications Hub | `POST /comm/v1/notifications/send` | **404**, no contract | Same approach. Option B (SNS MFA send and verify) is routed (401). |

The Notifications Hub endpoint is either hosted outside the InsureMO gateway or not published for trialx. The Notifications Hub team needs to provide the host, the path and the request/response contract.

## 2. Works differently from the spec

| API | Spec | Observed on trialx |
|---|---|---|
| API-02 Get Token | Response has `access_token`, `expire_in`, `message`, `retry_times` | A failed login still returns **HTTP 200**, with `access_token: ""`. It also has four undocumented fields: `err_code` (e.g. `w_cas_password_notright`, `w_cas_parameter_empty`), `authResult`, `auth_result` and `trace_id`. An empty body returns **HTTP 400** `parameter is empty`. Callers must check that `access_token` is not empty rather than rely on the HTTP status. |
| All APIs, gateway 401 | "401 token not correct" | Body is `{"env", "env_name", "trace", "trace_id", "status":401, "flag", "message":"gateway: invalid token, ..."}`. Saved as an example in the collection. |

## 3. Spec structure contradicts itself

| API | Problem | In the collection |
|---|---|---|
| API-06 Float Statement: Search Collections | The request table documents a flat SearchCondition (`FuzzyConditions`, `OrConditionsList`, `FromRangeConditions`, `ToRangeConditions`). The sample request instead wraps the filters in `QueryCondition` with camelCase keys (`fuzzyConditions`, `orSearchConditionsList`, `gteRangeConditions`, `lteRangeConditions`). | Both forms are included as separate requests. |
| API-09 Query Commission | The request uses SearchCondition paging (`PageNo`/`PageSize`), but the response is a PagedResult (`ElementsInCurrentPage`, `PageQuery.PageNumber`). The other search APIs return a QueryResult (`Results[].EsDocs`). | Tests expect the documented PagedResult. |
| API-11 Ratetable Lookup | `conditions` is listed both as a query-string Map and as the JSON body. | Conditions are sent in the body. |
| API-17 Quotation Query | The sample request sends `PageNumber: 0`, but the sample response echoes `PageNumber: 1`, so it is unclear whether paging starts at 0 or 1. | The Full variant uses `PageNumber: 1`. |
| API-20 Proposal and Policy Query | Three different paths: the portal list uses `/platform/proposal/v1/query`, the guide uses `/proposal/core/proposal/v1/query`, and the SDK uses `/proposal/v1/queryPolicy`. | Both routed paths are included. |

## 4. Spec structure incomplete (marked "to be confirmed" in the spec)

| API | Missing detail |
|---|---|
| API-14, API-23 Fetch Document / Query Files | Field names of the file entries in `Model` (a `FileId` field is assumed) and the shape of the metadata. |
| API-22 Upload Document | Field names in `Model`. The SDK marks every form field optional, but in practice files, businessType and businessNo are needed. |
| API-25 Document Type Tree | Node field names (`Code`, `Name`, `Children` assumed) and the `Context` keys. |
| API-26 Document Checklist | Item field names and status values. |
| API-27 Load All Document Versions | Field names of the version entries. |
| API-24 / API-27 | Whether `attachFileId` is a signed field. |
| API-18 / API-19 Load Customer | Names of the address, contact and account lists. Whether `customerId` is signed. No customer search API in the list returns a `customerId`. |
| API-28 FNOL | Values for `OperationType` and `ReportChannel`, and which ClaimCase fields each tenant makes mandatory. |
| API-29 / API-33 Claim Search | Paging wrapper inside `Model`. Which field carries `ClmPolicyId`, which API-31 needs. |
| API-30 Load Claim Case Detail | Names of the object and party lists. |
| API-31 Load Claim Policy | Where `clmPolicyId` comes from. |
| API-32 Endorsement History | Whether the response is a bare list or wrapped. |
| API-10 / API-11 | Data table and rate table names (`ProductListTable`, `PlanListTable`, `PackageTable`) are not created yet. |

## Pending: live body and response check

Every route that answered 401 still needs its request body and response checked against the spec, with a real trialx Machine User. This is not something I can do without credentials, and I have not fabricated a result for it. To run that check:

```bash
newman run Trialx-Portal-APIs.postman_collection.json \
  -e Trialx.postman_environment.json \
  --env-var username=<machine user> --env-var password=<password> \
  --reporters cli,json --reporter-json-export run.json
python3 summarize_run.py run.json > results/run-$(date +%F).md
```

Each request (Mandatory and Full, both in the one collection) gets one of these verdicts, with a suggested next action:

| Verdict | Meaning | Next action |
|---|---|---|
| `OK` | 2xx and the response shape matches the spec | None |
| `STRUCTURE FAIL` | 2xx but the response shape differs from the spec | Likely a doc fix - tell me the failing check and I will update the spec doc |
| `ROUTE MISSING` | Gateway 404 | Confirm the path with the platform team; if correct, the spec's endpoint is wrong |
| `REJECTED` | Other 4xx/5xx (trialx rejected the request) | Read the response body; may be a doc fix if the spec calls a rejected field valid |
| `NO TOKEN` | 401 | Check `username`/`password` in the environment - not a doc issue |
| `NO PERMISSION` | 403 | Ask the API owner to grant the API to trialx - not a doc issue |

Send me the resulting `run.json` or the Markdown table and I will go through every `STRUCTURE FAIL`, `ROUTE MISSING` and `REJECTED` row, compare it against the spec doc, and update whichever individual API doc is wrong.

## Doc updates already made from the spec-reading pass (not yet confirmed against live data)

I added a "Doc update needed" note to the affected section of each of these docs on 28 Sep 2026, based on reading the spec text (not a live trialx call — see the "Confirmed on trialx" vs "flagged" wording in each note for which):

- [API-06 Search Collections](https://claude.ai/code/artifact/d7e0c71b-dd35-4e7e-b9dc-4854d9e004e5) — `SearchCondition` vs `QueryCondition` mismatch between the Request table and the sample
- [API-09 Query Commission](https://claude.ai/code/artifact/a2ef411d-2e14-4642-8eb4-06b7bb0e8d70) — request uses SearchCondition paging, response is PagedResult
- [API-11 Ratetable Lookup](https://claude.ai/code/artifact/2e27a287-916c-4ba8-b599-c93852cef974) — `conditions` listed as both a query param and a body field
- [API-17 Quotation Query](https://claude.ai/code/artifact/e8d78309-0ae9-4323-ab2e-34af2fff123f) — sample request `PageNumber: 0` vs sample response `PageNumber: 1`
- [API-20 Proposal and Policy Query](https://claude.ai/code/artifact/4244ed3c-29f9-407e-a912-0f6b799a48a7) — three different paths given for one API

These notes flag the issue; they do not resolve it. Once you run the collection against trialx, I will replace each note with the confirmed answer (or correct it, if the live behaviour differs from what the note assumed).
