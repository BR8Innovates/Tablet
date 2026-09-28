# Trialx API structure check

Source: *Portal Integration API Specification* v0.2 (API-01 to API-34).
Target: InsureMO tenant `trialx`. The gateway is `https://portal-gw.insuremo.com` and the tenant domain is `trialx-gimc.insuremo.com`.
Date: 28 Sep 2026.

## How it was checked

1. **Live route check on trialx (no credentials).** Every request run with Newman, without a token. 401 = route exists; 404 = path wrong or unpublished. Full output: [`results/2026-09-28-route-check-no-credentials.md`](results/2026-09-28-route-check-no-credentials.md).
2. **Live full run on trialx (real Machine User, 28 Sep 2026).** 169 of 192 requests run with a real login (`ravi.teja@insuremo.com`), skipping the 23 that create data or send messages (Upload Document, FNOL, every SMS/Email send). Full output, credentials and tokens redacted: [`results/2026-09-28-live-run.md`](results/2026-09-28-live-run.md). Result: **89 OK, 40 STRUCTURE FAIL, 37 REJECTED, 4 ROUTE MISSING.**
3. **Spec review.** I compared each API's request table, samples and response tables for internal contradictions.

Nothing in this document or in the collection is invented — every claim below cites either the spec text or an actual trialx response.

**Important correction from the credentialed run:** the no-credentials check assumes 401 = "route exists." That assumption turned out to be wrong for API-20's documented core path: it answers 401 without a token (gateway auth filter intercepts first) but **404 "No static resource core/proposal/v1/query"** once authenticated (the route genuinely does not exist once the request reaches the backend). See §5.

## Summary

| Status | APIs |
|---|---|
| **Not working on trialx: route missing (HTTP 404)** | API-05 (spec path), API-15, API-16, API-34 Option A, API-20 (documented core path — see correction above) |
| **Works differently from the spec, confirmed live** | API-02, API-09, API-17, API-20, API-30 |
| **Confirmed working as documented, real trialx data returned** | API-05 (SDK core path), API-20 (portal list path), API-29 (once a non-empty body is sent), API-30 |
| **Spec structure contradicts itself (still needs live confirmation)** | API-06, API-11 |
| **Spec structure incomplete ("to be confirmed")** | API-14, API-22, API-23, API-25, API-26, API-27, API-28, API-31, API-32, API-33, API-18, API-19 |
| Blocked in this run only by missing test data (empty customerId/attachFileId/businessType/table names, not a spec problem) | API-10, API-11, API-12, API-13, API-14, API-18, API-19, API-23, API-24, API-25, API-26, API-27, API-31 |

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
| API-17 Quotation Query | The sample request sends `PageNumber: 0`, but the sample response echoes `PageNumber: 1` — confirmed still unresolved (see §5, the live call failed for a different, unrelated reason before paging even mattered). | Full variant uses `PageNumber: 1`. |

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

## 5. Confirmed live findings (real Machine User, 28 Sep 2026)

These are not guesses — each row is what trialx actually returned. Full bodies (redacted of credentials) are in [`results/2026-09-28-live-run.md`](results/2026-09-28-live-run.md).

| API | Finding | Evidence |
|---|---|---|
| API-02 Get Token | Confirmed as previously noted: extra undocumented fields (`err_code`, `authResult`, `auth_result`, `trace_id`), a failed login still returns HTTP 200. A correct login returned `expire_in: 86412`–`86418` (~24h), not the ~2h in the spec's sample (`7216`) — token lifetime is tenant/account configurable, spec's number is just one example. |
| API-05 Load Sales Agreements | **Confirmed working** on the SDK core path (`GET /platform/saleschannel/core/agreement/load/byChannelId`) with real data: fields matched the spec (`AgreementCode`, `AgreementStatus`, `ChannelId`, `SalesAgreementAuthorityList[].AuthorityType`, `SalesCommissionRateList[]`). The spec's own path (`/api/platform/...`) is still 404. **Doc fix:** replace the spec path with the core path as the primary documented endpoint. |
| API-09 Query Commission | Confirmed: `ElementsInCurrentPage` is **omitted entirely** (not `[]`) when there are zero matching records — `{"NumberOfElementsInCurrentPage":0,"PageQuery":{...},"TotalElements":0}` with no `ElementsInCurrentPage` key. **Doc fix:** note this omission so client code doesn't assume the array key is always present. |
| API-17 Quotation Query | Two different real failures, neither a paging-format issue: **Mandatory** (empty body `{}`) → HTTP 500 `NumberFormatException: For input string: "Destination"` — looks like a data problem inside trialx's own quotation records (some field holds the literal text "Destination" where a number is expected), not a spec/request problem. **Full** (with `Orders: [{"FieldName": "QuotationDate", ...}]`) → HTTP 500 `Hibernate SemanticException: Could not interpret path expression 'QuotationDate'` — sorting by `QuotationDate` is rejected by the backend even though that is the field's documented name. **Doc fix:** the `Orders[].FieldName` value doesn't work for `QuotationDate` as written; the correct sortable field name needs to come from the API owner. The `PageNumber` 0-vs-1 question is still open — this run never got that far. |
| API-20 Proposal and Policy Query | **Correction to the earlier note:** the documented core path (`/proposal/core/proposal/v1/query`) returns **404 `No static resource core/proposal/v1/query`** once authenticated — it does not exist on trialx, despite answering 401 (not 404) without a token. **The portal list path (`/platform/proposal/v1/query`) works and returned real policy data** matching the spec's field names (`PolicyId`, `PolicyNo`, `ProductCode`, `ProposalStatus`, `PolicyStatus`, `DuePremium`, `SumInsured`...). **Security-relevant doc issue:** the spec says the index "masks sensitive values in results" (e.g. `IdNo`), but the live `IdNo`/`InsuredIdNo` fields came back **unmasked** in plain text; a separate `TempData.Mask-IdNo` / `TempData.MaskAfter-IdNo` pair was present instead. If the portal relies on the spec's claim that `IdNo` itself is masked, it will display unmasked IDs. **Doc fix:** drop the core path from the Request table, and correct or remove the masking claim — masking is not applied to the top-level field on trialx. |
| API-29 / API-33 Claim Search | Confirmed: an **empty JSON body `{}` is rejected** with HTTP 500 `Missing the required parameter 'claimQueryRequestCondition'`, even though every field in the spec's Request table is marked optional. Once fields were sent (Full variant), the call succeeded (HTTP 200) with the documented `ClaimResponse` envelope (`Status: "BLOCK"`, `Messages[]` with real code-table validation errors on `ProductLineCode`/`CaseStatus`). **Doc fix:** state that the body cannot be completely empty, or name the one field that must always be present. |
| API-30 Load Claim Case Detail | **Confirmed working**, returned a real claim (`CaseId`, `ClaimCase`, `ClaimObjectList`, `ClaimPartyList` all present and matching the spec's field names). On success the envelope was `{"Status":"OK","Model":{...}}` with **`Messages` omitted entirely** (not `[]`) — same omission pattern as API-09's array. **Doc fix:** note that `Messages` is only present when there is something to say, matching the BLOCK case already documented. |
| Datatable and LoadTables — code tables | Confirmed **not configured / don't exist on trialx**, by name, from a live `CodeTable is not exist` error (`MO-PLATFORM-DD-B2006`): `AuthorityType`, `Country` (`CountryCode` does exist and works — these are two different table names in the spec), `Party`, `FnolStatus`, `ClaimClosedType` (`ClaimCloseType`, the differently-named table, does exist), `RelatedType`. **Doc fix:** either these six code tables need to be confirmed with the Config team as real table names, or the spec is using the wrong name for each. Separately: several tables that do exist (`AccountNature`, `Bank`, `Department`, `Org`, ...) returned no `BusinessCodeTableValueList` at all — those tables simply have zero rows configured on trialx, not a bug. |
| API-10 / API-11 | Confirmed the placeholder table names (`{{ProductListTable}}`, `{{PlanListTable}}`, `{{PackageTable}}`) are not real trialx tables (`this argument is required; it must not be null` / HTTP 400) — as already flagged, these need the Config team to say what the real names are. Not retested with a real name. |

## Things that failed only because this run had no real business data (not spec problems)

`customerId` (API-18/19), `attachFileId` (API-24/27), and the data/rate table names (API-10/11 - `ProductListTable`, `PlanListTable`, `PackageTable`) were empty in this run, and stayed empty even after the fixes in §6, because nothing in the documented 34 APIs can produce them: there is no customer search API in the list, no file was ever uploaded on trialx under the one configured business type (confirmed - see §6), and the Config team hasn't named these tables yet. Each call correctly rejected the empty value it was given. These need real values from outside this collection, not a further request fix.

## 6. Request-parameter fixes applied and confirmed live (28 Sep 2026, second pass)

Per your instruction to try to get the right request wherever an API wasn't responding: every REJECTED/ROUTE MISSING/STRUCTURE FAIL result from §5 was retried with corrected query/body parameters, using a real OAuth login via `imo auth login --manual` (no password this time) and real data pulled live from trialx itself (product codes, claim numbers, policy numbers). Result improved from **88 OK / 40 STRUCTURE FAIL / 37 REJECTED / 4 ROUTE MISSING** to **136 OK / 5 STRUCTURE FAIL / 20 REJECTED / 4 ROUTE MISSING** (of 165 requests run). Full evidence: [`results/2026-09-28-live-run-fixed.md`](results/2026-09-28-live-run-fixed.md).

| API | What was wrong | The fix (confirmed working) |
|---|---|---|
| API-12 Product Schema | `productCode=TBTI` (the spec's own sample) doesn't exist on trialx | Changed the environment default to `FCMOTOR`, a real product on trialx. Other real codes seen: `MIE`, `TRAVEL`, `RPO01_RK`, `CI0001`. |
| API-17 Quotation Query, Mandatory | An empty body `{}`, and even `{"PageSize": 5}` alone, throws HTTP 500 `NumberFormatException: For input string: "Destination"` - bad data sitting in an existing trialx quotation record, hit whenever the query isn't filtered enough to skip it | Added `"ProductCode": "{{productCode}}"` to the Mandatory body - confirmed this alone (with `PageSize`) avoids the bad record and returns real quotations. `Orders`-based sorting is a separate, confirmed platform bug (see §5) - removed, not fixable by changing the field name. |
| API-29 / API-33 Claim Search, Mandatory | An empty body `{}` throws HTTP 500 `Missing the required parameter 'claimQueryRequestCondition'`, contradicting "every field is optional" | Changed the Mandatory body to `{"PageNo": 1, "PageSize": 5}` - confirmed working, returns real claims. Also corrected the response parsing: the real envelope is `Model.ClaimList[]`, not `Model.Results[]` as the doc's Response section assumes. |
| API-14 / API-23 Fetch Document / Query Files, API-25 Document Type Tree, API-26 Document Checklist | `businessType`/`businessNo` were empty | Queried the real `AttachBusinessType` code table: **trialx has exactly one configured value, `001` = Claim.** Set that as the environment default, with a real claim number (`CRPO01_RK202600000308`) as `businessNo`. All four now return real data (API-25 in particular: a rich node schema not in the spec - see below). |
| API-05, API-09, API-11 code table names (`AuthorityType`, `Country`, `FnolStatus`, `ClaimClosedType`) | These table names don't exist on trialx (`CodeTable is not exist`) | Pulled the full list of all 2196 code table names configured on trialx and found the real ones: `AuthorityType` → **`AgreementAuthorityType`** (values confirmed: 1 By Product Line, 2 By Product, 3 All); `Country` → **`CountryCode`** (already used elsewhere in the spec under the right name); `FnolStatus` → **`ClaimFnolStatus`**. `ClaimClosedType` has no real match - only `ClaimCloseType` exists (used for the sibling `CloseType` field); the spec's second, separately-spelled table for `ClosedType` doesn't exist and this remains unresolved, not a fix. |
| API-30/31/33 chain (`ClmPolicyId`) | Never had a real value to test with | Got one from a real, successful Claim Search (`ClmPolicyId: 905384080`, `ClaimNo: CMIE202400000186`) and confirmed both **Load Claim Policy** and **Load Claim Case Detail** return real, correctly-shaped data end to end. |
| API-13 Load Quote Details | Depended on `quotePolicyId`, which only API-17 sets | Not a request-shape bug - a run-order issue: API-13's folder runs before API-17's in a single alphabetical pass. Confirmed the request itself works once given a real `policyId` (chained manually). Documented in the collection: run API-17 first, or run the whole collection twice. |

**Two genuine platform bugs found, not fixable from the client side, reported here for the API owner:**
- **`Orders`-based sorting on Quotation Query is broken for every field name tried** (`QuotationDate`, `ProposalDate`, `EffectiveDate` all throw `Hibernate SemanticException: Could not interpret path expression`) - not a wrong field name, the sort mechanism itself doesn't work on this endpoint.
- **An unfiltered Quotation Query 500s on bad data already sitting in a trialx quotation record** (`NumberFormatException: For input string: "Destination"`) - a data-quality issue in the tenant, not a request problem.

**Confirmed, undocumented real response shape (API-25 Document Type Tree):** the spec assumes `Code`/`Name`/`Children` nodes. The real response is a **flat list** of nodes with `id`, `code`, `name`, `pId` (parent id), `path`, `sort`, `isLastLevel`, `isChecked`, `hasChecklistAuthority`, `count`, `canAddAdditional`, and more - no nesting via `Children` at all. This needs a doc rewrite, not a note.

**Ratetable Lookup and Datatable Lookup remain unfixed** - both need a real table name/code that only the Config team can provide (confirmed: no endpoint in the documented 34 APIs lists available table names). `Load Individual/Organisation Customer` remain unfixed for the same reason on the customer side - no customer search API exists in the portal list to obtain a real `customerId`, and three guessed endpoint names all 404'd.

## Doc updates made in the live spec docs

I updated the "Doc update needed" note on each of these to reflect what's now confirmed (marked *(confirmed live)*) versus what's still just a spec-reading observation:

- [API-06 Search Collections](https://claude.ai/code/artifact/d7e0c71b-dd35-4e7e-b9dc-4854d9e004e5) — `SearchCondition` vs `QueryCondition` mismatch; not yet exercised live in this run
- [API-09 Query Commission](https://claude.ai/code/artifact/a2ef411d-2e14-4642-8eb4-06b7bb0e8d70) — *(confirmed live)* `ElementsInCurrentPage` omitted on empty results
- [API-11 Ratetable Lookup](https://claude.ai/code/artifact/2e27a287-916c-4ba8-b599-c93852cef974) — `conditions` listed as both a query param and a body field; not yet exercised live with a real table code
- [API-17 Quotation Query](https://claude.ai/code/artifact/e8d78309-0ae9-4323-ab2e-34af2fff123f) — *(confirmed live)* `Orders[].FieldName: "QuotationDate"` rejected by Hibernate; `PageNumber` 0-vs-1 still open
- [API-20 Proposal and Policy Query](https://claude.ai/code/artifact/4244ed3c-29f9-407e-a912-0f6b799a48a7) — *(confirmed live, corrected)* core path is 404, not just "unconfirmed"; masking claim contradicted by live data

## Re-running

```bash
newman run Trialx-Portal-APIs.postman_collection.json \
  -e Trialx.postman_environment.json \
  --env-var username=<machine user> --env-var password=<password> \
  --reporters cli,json --reporter-json-export run.json
python3 summarize_run.py run.json > results/run-$(date +%F).md
```
