Subject: Protec UAT API test report - 28 Oct 2026 (results, Postman collection, bugs)

Hi team,

Attached are the results of the Protec API test run on UAT (https://protecuat-sandbox-protec-in.insuremo.com, tenant protecuat).

Attachments
1. Protec_UAT_API_Test_Report.xlsx - Summary, All APIs (with endpoints), Success, Failure, Not tested, Bugs
2. Protec_UAT_Test_Results.postman_collection.json - requests with saved responses, in Success / Failure / Blocked folders

Result: 83 use cases covered - 76 success, 4 partial, 1 failure, 4 not tested (get token, requote, collection-and-issue, new-customer KYC). Nothing is blocked after re-testing.

Test data created: agent PTY00000000000003 (agreement, 10% commission on PCAR/P2W/PCV/GCV, float of Rs 1,00,00,000 across collections 532527 and 532533), customer CUS26000022 (active, KYC verified), and issued policies for PCAR, P2W, PCV and GCV, plus claims on each.

Bugs raised
- UAT-BUG-01 (High): policies with UW referral (AutoUwResultCode 2) are issued with no float debit.
- UAT-BUG-02 (High): proposalValidate/bind return HTTP 500 for registered vehicles (MH12AB1234, KA01AB1234).
- UAT-BUG-03 (Medium): claim document types not configured; claim document upload returns HTTP 500.
- UAT-BUG-04 (Low): unhandled exceptions return a generic E9998 message.
- Observations: searchSCList returns 0 with the ScStatus filter; FNOL gives a misleading "policy does not exist" message for a loss date before policy start.

Leftovers in UAT: about 25 unissued draft quotes/proposals and a sample PDF on PP-1005-26-00000052-00.

Regards
