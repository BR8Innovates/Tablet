Subject: Protec UAT API test report - 28 Oct 2026 (results, Postman collection, bugs)

Hi team,

Attached are the results of the Protec API test run on UAT (https://protecuat-sandbox-protec-in.insuremo.com, tenant protecuat).

Attachments
1. Protec_UAT_API_Test_Report.xlsx - Summary, All APIs (with endpoints), Success, Failure, Not tested, Bugs
2. Protec_UAT_Test_Results.postman_collection.json - requests with saved responses, in Success / Failure / Blocked folders

Result: 83 use cases covered - 76 success, 4 partial, 1 failure, 4 not tested (get token, requote, collection-and-issue, new-customer KYC). Nothing is blocked after re-testing.

Test data created: agent PTY00000000000003 (agreement, 10% commission on PCAR/P2W/PCV/GCV, float of Rs 1,00,00,000 across collections 532527 and 532533), customer CUS26000022 (active, KYC verified), and issued policies for PCAR, P2W, PCV and GCV, plus claims on each.

Bugs raised (API wise)
- A07 GetVehicleData - UAT-BUG-05 (Medium): intermittent Vahan "wallet balance is low".
- A08 searchSCList - UAT-OBS-06 (Info): returns 0 when the ScStatus [1] filter is sent.
- A27 proposalValidate - UAT-BUG-02 (High): HTTP 500 for registered vehicles (MH12AB1234, KA01AB1234).
- A29 proposalBind - UAT-BUG-02 (High): HTTP 500 for registered vehicles; PCAR gives 422 instead.
- A31 proposalSendPrepayment - UAT-BUG-01 (High): UW-referral policies are issued with no float debit.
- A36.2 uploadMulti (claim) - UAT-BUG-03 (Medium): HTTP 500.
- A39.2 getTreeData (claim) - UAT-BUG-03 (Medium): claim document types not configured.
- A42 ECS_business_fnol - UAT-OBS-07 (Low): misleading "policy does not exist" for a loss date before policy start.
- General - UAT-BUG-04 (Low): generic E9998 error message with no cause.

Leftovers in UAT: about 25 unissued draft quotes/proposals and a sample PDF on PP-1005-26-00000052-00.

Regards
