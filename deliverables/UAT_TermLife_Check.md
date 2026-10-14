# UAT check - Term Life (TL001), 14 October 2026

Tenant uponlyuat, base https://uponlyuat-sandbox-in.insuremo.com/api/uponlyuat/api-orchestration/v1/flow. Collection checked: UPONLY_UAT.postman_collection_2.json.

## Why the collection fails
| # | Request | Result | Cause |
|---|---|---|---|
| 1 | Every request (12) | 401 | Each request carries its own pasted bearer token. They have expired (a token lasts about 2 hours: expire_in 7229 s). The Token request does not save the token it returns. |
| 2 | 3. Update Proposal | 500 INTERNAL_ERROR "proposal status shows it has been issued already, can not be update/issue again" | ProposalNo PTL0010000000002 was already issued (policy POTL00100000001). The platform's business message comes back as a 500 and carries a misleading iHub text ("Make sure iHubUrl provided is correct ... ihub.service.pat.token"). |
| 3 | 11. cancel-check | 409 UP-409 "status is Cancelled" | Policy POTL00100000001 was cancelled in an earlier run (status 3). |
| 4 | 12. cancel-approve | 404 UP-404 "No pending cancellation request POTL00100000001-003" | Fixed RequestNo from an earlier run. |
| 5 | 7. Proposal Reject | 200 | Rejects PPA0010000000030, a Personal Accident number, with ProductCode TL001: no product check in UAT (MC answers 400 MISMATCH). |
| 6 | 1. Get Plan | 200 | Uses ProductSubcode 2 while every other request uses 1. |
| 7 | 2. / 3. | 200 | Sends DuePremium 153 (top) and 216 (LOB); both are ignored, the platform rates 216. Dates are March 2026 (past). ApplicationNo "123" is reused. |
| 8 | Bodies of Data Table and generate-feedfile | 200 | Contain // comments inside the JSON. UAT tolerates them; MC would answer 400 invalid JSON. |

With fresh data the whole Term Life flow passes on UAT (14 of 14 requests 200): corrected collection attached.

## Tables
All 14 UP_ tables exist in UAT with the same row counts as MC and identical content, except UP_ApiConfig (114 keys): GatewayUrl and AllowedHosts point to the UAT host (correct for UAT).
- UP_UserRole holds the three MC test rows (ravi.teja@insuremo.com): replace them with real users.
- PrintUrl still points to portal-gw.insuremo.com (the MC gateway); PDFs are produced today, confirm this is intended for UAT.
- RoleEnforcement N, AllowSelfApproval Y, NotifyMode DRYRUN (same as MC).

## Rating (Term Life, UAT against MC, 10 plans)
Identical for variant 1 and variant 2, plans 1 to 5: premium (216, 328, 440, 552, 664 / 132, 244, 360, 472, 580), commission (151.2 ... 464.8 / 92.4 ... 406), commission rate 0.1, sums insured (10000 to 50000 / 7500 to 47500) and coverages (variant 1 includes Travel). A wrong premium sent in the request is ignored.
Observations: Get Plans on UAT returns only the plan sent (premium not shown per plan, none at plan level), where MC returns all 5 plans with premium. The premium is at risk level (PolicyRiskList[0].DuePremium); policy level shows 0 on both tenants.

## UAT runs a different build than MC
- Missing on UAT (HTTP 500 E9998): me, worklist, dashboard, share, cancel-detail, commission-query.
- list-master-table on UAT returns any table, including UP_ApiConfig and UP_UserRole (MC refuses with 400): restrict it.
- Errors are the older shape: platform rule violations (gender 9, plan 9) return 500 INTERNAL_ERROR instead of 400 UP-PLATFORM-VALIDATION.
- Update Proposal goes through an iHub integration service (create-update-proposal), not used in MC.
UAT was therefore not deployed from the same build as MC; redeploy iComposer from the current source.
