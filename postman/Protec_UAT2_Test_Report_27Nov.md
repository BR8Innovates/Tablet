# Protec UAT2 - test report (27 Nov 2026)

Environment: protecuat2 sandbox. Users: admin (`protecuat2.admin`, via PAT, user ID 10000000970439) and portal user (`ProtecPortalUser`, user ID 10000001643083). Payment links, SMS and email APIs were excluded.

## 1. Deliverables (branch `claude/serene-knuth-9acc0x`)

| File | Purpose |
|---|---|
| `postman/Protec_UAT2_EndToEnd.postman_collection.json` | 264 requests, login to float plus add-on quotes, examples saved, `payMode` and `issueViaApi` switches |
| `postman/Protec_UAT2_Sequenced_Collection.postman_collection.json` | 138-request sequenced collection (cash proposals, claims, uploads) |
| `postman/Protec_UAT2_Addon_Quotes.postman_collection.json` | 109 add-on calculations (URLs fixed) |
| `postman/Protec_UAT2_Sequenced_Test_Report.md` | first full-run report (morning run) |
| `postman/Protec_UAT2_PCAR_New_Policy_Run.md`, `postman/Protec_UAT2_getCollection_responses.json` | endpoint/response evidence |

## 2. Results by area

| Area | Result |
|---|---|
| Reference data, party, KYC, sales channel, vehicle | Pass (known gaps in section 4) |
| Quote, proposal, validate, underwriting, bind (all 4 products) | **Pass** after fixes (effective date = today, customer email aligned to party master, installment type sent) |
| Prepayment, float mode (PayMode 120) | **Fail**: 422 `UndefinedException` for admin and for portal user |
| Policy issue | **Blocked**: no new policy issued; 4 cash proposals waiting for manual issue |
| Endorsements E1-E7 | Not testable on new policies until issued (earlier run: 28 requests 422 because policies were not issued) |
| Claims (FNOL) | 3 of 4 created; P2W blocked by claim matrix |
| Documents (read APIs) | **Pass**: attachment info, query files, tree, checklist, versions, download (PDF) |
| Documents (upload) | **Pass** for policy and claims with portal user token; PAT needs extra fields for claims |
| Float account reads | **Pass**: balances and frozen amounts available |
| Add-on quotes (109) | 107 returned 200, 2 returned 422; 86 fail the premium-impact assertion |

Full sequenced run before the fixes (morning): 138 requests, 86 passed, 52 failed. Second run after the date fix: 89 passed, 49 failed. All remaining failures traced to the unissued policies, plus the items in section 4.

## 3. Records created today

**Bound proposals, cash (PayMode 100), waiting for you to issue:**

| Product | ProposalNo | PolicyId | Premium |
|---|---|---|---:|
| PCAR | PQ-1005-26-00000096 | 6000565 | 4,473 |
| P2W | PQ-1106-26-00000024 | 6000568 | 1,226 |
| PCV | PQ-1202-26-00000022 | 6000571 | 31,312 |
| GCV | PQ-1204-26-00000023 | 6000574 | 17,084 |

Other bound, unissued proposals from float tests: PQ-1005-26-00000095, PQ-1106-26-00000023, PQ-1202-26-00000021, PQ-1204-26-00000022 (admin) and PQ-1005-26-00000099 (portal user).

**Claims (on issued policies, accident 27 Nov 09:30):**

| Product | Policy | ClaimNo |
|---|---|---|
| PCAR | PP-1005-26-00000059-00 | PC-1005-26-00000006 |
| PCV | PP-1202-26-00000015-00 | PC-1202-26-00000003 |
| GCV | PP-1204-26-00000014-00 | PC-1204-26-00000004 |
| P2W | PP-1106-26-00000016-00 | not created (`MO-CLM-Validation-E0101`) |

**Uploaded documents:** policy PP-1005-26-00000059-00: 6402845, 6402849, 6402861; claim PC-1005-26-00000006: 6402826, 6402840, 6402853; claim PC-1202-26-00000003: 6402831, 6402857; claim PC-1204-26-00000004: 6402836.

**Float (IA000001, account ACCOUNT20261100000001, BcpAccountId 4688150):** collection balances 6482873: 900,000; 6319031: 199,999; 5983222: 99,999; 5983231: 45,904; others 0. Total 1,245,902. Frozen balance 0 on every collection. Account sub-account balance reads 0 and `AllowOverdraft` is N.

## 4. Open issues

| # | Issue | Impact | Next step / owner |
|---|---|---|---|
| 1 | Float prepayment returns 422 `UndefinedException` for both users; reproduced with funded collections, correct payment block, `IsIssueAfterPay` Y/N | Blocks policy issue via API | Platform team: logs for trace IDs `e54dd5f39008d7127866a5e1c3cc711a`, `0a49b2f5c2fede87808582d5306b2027`, `3daaad9b3450ceeb3618fc3b73fab12b`, `cabb35757107d877184f4ce8c50048d9`, `69cb82e4d8b0c2455c3a23209ae0462a` |
| 2 | Four cash proposals not issued | Endorsements, commission and 3.1 checks wait | You: issue in portal, then re-run from 3.1 |
| 3 | P2W (1106) claim blocked: product missing from claim matrix | No P2W claim | Claim configuration |
| 4 | IIB reference retrieve returned 500 earlier, 200 later | Intermittent | Watch; platform |
| 5 | Add-on quotes: 86 of 109 show no premium impact | Add-on rating unverified | Needs sum insured / dependency inputs per add-on |
| 6 | KYC organisation validation returns 200 where 422 expected | Validation gap | Platform |
| 7 | A03.1 and A47.1 assertions compare to unresolved or stale values | False failures | Fix assertions |
| 8 | PCAR commission 15% vs 10% in the agreement; commission zero where no policy issued | Commission unverified | After issue |
| 9 | Customer master has 0 records on UAT2 | A04.1 untestable | Data |
| 10 | Claim document upload with PAT needs BusinessId, ProductCode, ProductLine, AttachType; user token works with minimal fields | Token-specific behaviour | Documented in 6.10 |
| 11 | Package Individual APIs collection uses `{{baseUrl}}/platform/...` (404; correct is `/api/platform/...`) | Package collection broken | Not changed |
| 12 | PAT and user passwords were shared in chat | Security | Rotate after testing |

## 5. Not done

- One end-to-end pass over all 264 requests on issued policies (depends on items 1-2).
- Admin user token test (no admin password available).
- Individual examples for endorsement, commission and queries on the new policies (current examples are from earlier runs).
