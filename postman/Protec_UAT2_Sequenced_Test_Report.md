# Protec UAT2 - sequenced collection test report

Run: 27 Nov 2026, protecuat2 sandbox, PAT authentication. Collection: `postman/Protec_UAT2_Sequenced_Collection.postman_collection.json`. Token folder excluded (PAT passed directly).

- Requests run: **138**
- Passed (no failed assertions): **86**
- Failed (one or more failed assertions): **52** (94 assertion failures in total)
- HTTP status: 200: 98, 400: 9, 422: 30, 500: 1
- **Not run (held back):** 6.3 Proposal requote, 6.7 Submit FNOL, 6.10 Upload document. Each creates or changes a sandbox record; run only on request.

## Root cause of most failures

The quotes were persisted with effective date **2026-11-26**, one day before the system date (2026-11-27). The platform therefore sends every proposal to manual underwriting referral:

> `EA-PA-UW-B0023`: Policy effective date [2026-11-26] is before the system date; manual underwriting referral required.

Effects in this run:
- Proposal validate (2.4) returns `MO-PA-Validation-B4000` for PCAR, P2W, PCV and GCV.
- Proposal send prepayment (2.9) returns 422 for all four products, so no policy is issued.
- Issued-policy load (3.1) returns 400 for P2W, PCV and GCV. The A33.1 and A49.1 queries fail for the same reason.
- Every endorsement (E1-E7, all four products) returns 422: `Direct issue aborted: auto underwriting did not pass`. Endorsements need an issued policy.
- Commission checks (C5) for P2W, PCV and GCV show zero because no policy was issued in this run.

**Fix (test data, not applied):** set the quote effective date to the current date in the 1.1 persist bodies, then re-run. A re-run creates new quotes and policies in the sandbox, so it has not been done.

## Results by folder

| Folder | Requests | Passed | Failed |
|---|---:|---:|---:|
| 1 Reference data | 6 | 6 | 0 |
| 2 Party, customer and KYC | 11 | 9 | 2 |
| 3 Sales channel and agent | 3 | 3 | 0 |
| 4 Vehicle and IIB | 10 | 10 | 0 |
| 5.1 Issuance - PCAR (quote to float prepayment) | 10 | 8 | 2 |
| 5.2 Issuance - P2W (quote to float prepayment) | 10 | 7 | 3 |
| 5.3 Issuance - PCV (quote to float prepayment) | 10 | 7 | 3 |
| 5.4 Issuance - GCV (quote to float prepayment) | 10 | 7 | 3 |
| 5.5 Quotation and proposal (all products) | 3 | 3 | 0 |
| 6 Policy and endorsement queries | 13 | 6 | 7 |
| 7 Endorsements - PCAR  | 8 | 1 | 7 |
| 7 Endorsements - P2W  | 8 | 0 | 8 |
| 7 Endorsements - PCV  | 7 | 0 | 7 |
| 7 Endorsements - GCV  | 7 | 0 | 7 |
| 8 Claims | 3 | 3 | 0 |
| 9 Documents | 6 | 6 | 0 |
| 10 Commission | 9 | 6 | 3 |
| 11 Float account | 4 | 4 | 0 |

## Failed requests

| HTTP | Request | First failed assertion or error |
|---:|---|---|
| 200 | A03.1 Party load customer | expected 'PI-26-00000001' to deeply equal '{{customerCode}}' |
| 200 | A05.4 KYC initiate - organisation (validation: expected 422 per API list) | expected 200 to deeply equal 422 |
| 500 | 6.5 IIB reference retrieve | HTTP error |
| 200 | PCAR 2.4 Proposal validate | expected 1 to deeply equal +0 |
| 422 | PCAR 2.9 Proposal send prepayment (float, PayMode 120) | expected response to have status code 200 but got 422 |
| 200 | P2W 2.4 Proposal validate | expected 1 to deeply equal +0 |
| 422 | P2W 2.9 Proposal send prepayment (float, PayMode 120) | expected response to have status code 200 but got 422 |
| 400 | P2W 3.1 Load proposal/policy (issued) | expected response to have status code 200 but got 400 |
| 200 | PCV 2.4 Proposal validate | expected 1 to deeply equal +0 |
| 422 | PCV 2.9 Proposal send prepayment (float, PayMode 120) | expected response to have status code 200 but got 422 |
| 400 | PCV 3.1 Load proposal/policy (issued) | expected response to have status code 200 but got 400 |
| 200 | GCV 2.4 Proposal validate | expected 1 to deeply equal +0 |
| 422 | GCV 2.9 Proposal send prepayment (float, PayMode 120) | expected response to have status code 200 but got 422 |
| 400 | GCV 3.1 Load proposal/policy (issued) | expected response to have status code 200 but got 400 |
| 200 | PCAR A49.1 Endorsement history | expected +0 to be at least 1 |
| 400 | P2W A33.1 Load proposal/policy | expected response to have status code 200 but got 400 |
| 400 | P2W A49.1 Endorsement history | expected response to have status code 200 but got 400 |
| 400 | PCV A33.1 Load proposal/policy | expected response to have status code 200 but got 400 |
| 400 | PCV A49.1 Endorsement history | expected response to have status code 200 but got 400 |
| 400 | GCV A33.1 Load proposal/policy | expected response to have status code 200 but got 400 |
| 400 | GCV A49.1 Endorsement history | expected response to have status code 200 but got 400 |
| 422 | PCAR E1 Engine number correction | expected response to have status code 200 but got 422 |
| 422 | PCAR E2 Chassis number correction | expected response to have status code 200 but got 422 |
| 422 | PCAR E3 Owner-driver DOB / gender (party master) | expected response to have status code 200 but got 422 |
| 422 | PCAR E4 Nominee change - CPA (PCAR, P2W) | expected response to have status code 200 but got 422 |
| 422 | PCAR E5 Hypothecation addition | expected response to have status code 200 but got 422 |
| 422 | PCAR E6 Change of financier (run after E5) | expected response to have status code 200 but got 422 |
| 422 | PCAR E7 Hypothecation deletion (run after E6) | expected response to have status code 200 but got 422 |
| 200 | P2W Query policy latest version (A47.1) | expected 'PP-1106-26-00000002-00' to deeply equal 'PP-1106-26-00000014-00' |
| 422 | P2W E1 Engine number correction | expected response to have status code 200 but got 422 |
| 422 | P2W E2 Chassis number correction | expected response to have status code 200 but got 422 |
| 422 | P2W E3 Owner-driver DOB / gender (party master) | expected response to have status code 200 but got 422 |
| 422 | P2W E4 Nominee change - CPA (PCAR, P2W) | expected response to have status code 200 but got 422 |
| 422 | P2W E5 Hypothecation addition | expected response to have status code 200 but got 422 |
| 422 | P2W E6 Change of financier (run after E5) | expected response to have status code 200 but got 422 |
| 422 | P2W E7 Hypothecation deletion (run after E6) | expected response to have status code 200 but got 422 |
| 200 | PCV Query policy latest version (A47.1) | expected 'PP-1202-26-00000002-00' to deeply equal 'PP-1202-26-00000013-00' |
| 422 | PCV E1 Engine number correction | expected response to have status code 200 but got 422 |
| 422 | PCV E2 Chassis number correction | expected response to have status code 200 but got 422 |
| 422 | PCV E3 Owner-driver DOB / gender (party master) | expected response to have status code 200 but got 422 |
| 422 | PCV E5 Hypothecation addition | expected response to have status code 200 but got 422 |
| 422 | PCV E6 Change of financier (run after E5) | expected response to have status code 200 but got 422 |
| 422 | PCV E7 Hypothecation deletion (run after E6) | expected response to have status code 200 but got 422 |
| 200 | GCV Query policy latest version (A47.1) | expected 'PP-1204-26-00000002-00' to deeply equal 'PP-1204-26-00000013-00' |
| 422 | GCV E1 Engine number correction | expected response to have status code 200 but got 422 |
| 422 | GCV E2 Chassis number correction | expected response to have status code 200 but got 422 |
| 422 | GCV E3 Owner-driver DOB / gender (party master) | expected response to have status code 200 but got 422 |
| 422 | GCV E5 Hypothecation addition | expected response to have status code 200 but got 422 |
| 422 | GCV E6 Change of financier (run after E5) | expected response to have status code 200 but got 422 |
| 422 | GCV E7 Hypothecation deletion (run after E6) | expected response to have status code 200 but got 422 |
| 200 | C5 P2W policy commission (from policy load) | expected +0 to not deeply equal +0 |
| 200 | C5 PCV policy commission (from policy load) | expected +0 to not deeply equal +0 |
| 200 | C5 GCV policy commission (from policy load) | expected +0 to not deeply equal +0 |

## Other observations

- **6.5 IIB reference retrieve** returns HTTP 500 (MO-PLATFORM-COMMON-E9998). Platform-side error. 6.6 IIB enquiry receive passes.
- **A03.1 Party load customer** returns PI-26-00000001, but the assertion compares against the unresolved placeholder `{{customerCode}}`. The response is correct; the assertion needs fixing.
- **A05.4 KYC organisation** returns 200 where 422 is expected. Known gap from the earlier run.
- **A49.1 PCAR endorsement history** returns no entries, because the PCAR policy was not issued in this run.
- **A47.1 policy latest version** for P2W, PCV and GCV returns the policy numbers from earlier runs (PP-1106-26-00000002-00, PP-1202-26-00000002-00, PP-1204-26-00000002-00). The assertions expect the numbers stored in the variables from the earlier run.

## Examples

Each request in the sequenced collection has its real response from this run saved as an example, named with the status code. Token responses are excluded.

