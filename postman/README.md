# UPONLY TL001 Postman files

- `UPONLY_TL001.postman_collection.json`: Term Life (TL001) API collection. Uses `{{baseUrl}}`, `{{token}}`, `{{proposalNo}}`, `{{policyNo}}` and `{{requestNo}}`, so no secrets or hardcoded numbers.
- `UPONLY_MC.postman_environment.json` and `UPONLY_UAT.postman_environment.json`: fill in `username` and `password` locally. Run **Token** first.

## Get Plans for TL001

Call `{{baseUrl}}/up/get-plans`, not `{{baseUrl}}/get-plans`. The legacy `/get-plans` route returns no premium for TL001 plans. `/up/get-plans` returns `DuePremium` and `Commission` on every plan, in the same shape as PA001 (`PolicyLobList[0].PolicyRiskList[0].PlanList[]`).

Premium depends on `ProductSubcode` (data table `UP_ProductPlanRelation`). Create Proposal returns the same figure for the same subcode and plan.

| Plan | Subcode 1 premium / commission | Subcode 2 premium / commission |
|---|---|---|
| 1 | 216 / 151.2 | 132 / 92.4 |
| 2 | 328 / 229.6 | 244 / 170.8 |
| 3 | 440 / 308 | 360 / 252 |
| 4 | 552 / 386.4 | 472 / 330.4 |
| 5 | 664 / 464.8 | 580 / 406 |

Subcode 3 is rejected as unknown. Premium modes 1 and 2 are allowed (mode 3 is rejected by `/up/proposal`).

## Test status

| Environment | Result |
|---|---|
| MC | Full flow passes. `/up/get-plans` returns plan premiums and commission and matches Create Proposal. |
| UAT | `/up/*` APIs are not deployed yet (they return 500). Data tables already match MC. Deploy below, then re-run this collection. |

## Deploy to UAT (iComposer, group `UP_PRODUCTS_API`, module `PA_COMMON`)

Push from MC at these versions. Data tables (`UP_ProductPlanRelation`, `UP_ProductMaster`, `UP_ProductRule`, `UP_ApiConfig`) already match, so no data migration is needed.

1. API `UPGetPlans` (v9), path `/up/get-plans`, request method POST.
2. Functions it depends on (MC version in brackets): `UPErrorHandler` (v11), `UPSecurity` (v5), `UPDataUtil` (v9), `UPProductData` (v5), `UPShaper` (v3), `UPValidator` (v3), `UPAccess` (v4). If UAT already has older versions of any of them, replace them with MC's version and re-test `/cancel-check`.
3. Optional, to use the rest of the new route set on UAT: the other `/up/*` APIs (`UPProposal`, `UPUpdateProposal`, `UPIssue`, `UPLoadPolicy`, and so on) and the remaining `UP*` functions.

After deploying, call `/up/get-plans` on UAT with subcodes 1 and 2 and compare with the table above.

## Known issues (not changed)

- `Proposal Reject` on MC returns 500: config center variable `imo.motor.proposalreject.url` is not set. `/up/proposal-reject` (`UPProposalReject`) exists as the replacement.
- PA001 `ProductSubcode "2"` on Create Proposal fails with `BenefitCode on null object`; use subcode 1.
