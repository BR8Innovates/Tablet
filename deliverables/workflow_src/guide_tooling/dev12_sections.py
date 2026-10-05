"""Developer guide v1.2: the content added after v1.1 (handover risks, workflow / roles / dashboard, notifications, portal, PA001 and iHub, runbook).
Each function appends blocks through the helpers of dev_content12 (passed in as g)."""
import re, os, json

B = os.environ["B"]
PORTAL = "/home/user/Tablet/uic_pages/uponly/portal/sohar-insurance-portal/index.html"


def read_first(g):
    H1, H2, P, NOTE, BUL, NUM, TBL, CODE, LBL = (g[k] for k in ("H1", "H2", "P", "NOTE", "BUL", "NUM", "TBL", "CODE", "LBL"))
    H2("1.4 Read This First: What Will Surprise You")
    P("These are the facts most likely to cost a new developer a day. Each one is explained in the section named in the last column.")
    TBL(["#", "What", "Why it matters", "Section"], [
        ["1", "The MC tenant runs with `RoleEnforcement` = Y, `AllowSelfApproval` = Y and `NotifyMode` = DRYRUN. `UP_UserRole` holds three **test** rows for one account (ravi.teja@insuremo.com holds all three roles).", "One account can run the whole flow, so maker and checker are the same person. Before UAT or go-live: AllowSelfApproval = N, replace the test rows with bank staff.", "15, 19"],
        ["2", "The maker's platform user id is stored in the proposal field **`AgentCode`**. Queues, \"My submissions\" and the maker-checker rule all depend on it.", "AgentCode is a platform field that normally means a sales agent. It is the only searchable field available. It is in the server-owned list, so callers cannot set it. Proposals created before v1.2 have no maker id.", "15.3"],
        ["3", "The work queues and dashboard counts are **read from the platform search index**, not from our tables. The index limit is 1,000 rows per query, it has no channel, no maker (except AgentCode), an empty insured name and a zero premium.", "Every queue row is enriched by loading the proposal (one call per row). Page size x page number must not exceed 1,000. A date window is always applied.", "15.4"],
        ["4", "Dashboard premium and commission are calculated by **loading policies**, capped at `DashboardMaxPolicies` (60) newest per product and flagged `Truncated`.", "Totals are exact only while a product has no more policies than the cap in the window. The dashboard takes 7 to 10 seconds. It is not a reporting database.", "15.5"],
        ["5", "The MC tenant holds a lot of **test data**: several hundred pending test proposals and over a hundred pending test cancellations created by the test suites.", "The queues and dashboard show them. There is no API to delete them.", "19"],
        ["6", "**No email or SMS is delivered.** The MC tenant has zero SNS email and SMS accounts. The SNS SMS request carries no free text, only a template code configured in the SNS account.", "`NotifyMode` = LIVE has never been exercised. The code path compiles but is unproven (field names, template codes).", "16"],
        ["7", "The portal's **sign-in screen** posts the user name and password to the platform's CAS ticket service and takes the token from the reply. Only the error path and the \"use my InsureMO session\" path were tested. A successful password sign-in was never run (no password available).", "The reply field name is assumed (`access_token` / `token` / `ticket`, as in the Postman collection). Verify with a real login first.", "17.3"],
        ["8", "The portal builds API URLs with the standard UIC helper (`/{{tenant_code}}/api-orchestration-test/v1/flow`). All automated tests ran with an override (`sohar_api_base` in sessionStorage) that points the page at the gateway through a stub. **The URL construction inside the real portal frame was not exercised by a test.**", "If the first call in the real portal fails with 404, check the route prefix. The override hook should be removed before go-live.", "17.4"],
        ["9", "The `imo` login (`imo auth login`) lasts 24 hours and cannot be refreshed from a script. Every tool in the build folder needs a valid profile token.", "When a push or script says \"token is invalid or expired\", log in again; nothing is wrong with the code.", "19"],
        ["10", "PA001 and its APIs are a **different design**: iComposer APIs in group `Policy_API` that call an adapter (`IhubCallerIntegrationAdapter`) driven by the table `AdapterServiceCfg`. The new `/up` APIs do not use that adapter or iHub.", "Do not reuse PA001 helper functions or tables for the new products. PA001 must stay untouched (`snapshot.py`).", "18"],
        ["11", "Cancellation requests that are rejected are indistinguishable from requests replaced when an approval runs: both end as endorsement status 600 (withdrawn).", "The cancellation queue can only list PENDING (120) and ISSUED (300).", "15.4"],
        ["12", "The specification (v1.1), UAT plan, policy model, OpenAPI file and Postman collection were **not updated** for v1.2. This guide is the only document that describes the new APIs.", "Section 15.7 holds request and response examples. Update the other documents before they are given to partners.", "15.7, 19"],
        ["13", "`GET /up/me` omits the `Roles` list when the caller has no roles (the platform drops empty lists).", "Treat a missing `Roles` as an empty list (the portal does).", "15.2"],
        ["14", "An inactive probe API `UPSpikeWho` (path `/up/spike-who`) remains in MC from the identity spike. The `imo` tool cannot delete an API.", "Delete it in the iComposer console before UAT. It must not be deployed.", "19"],
        ["16", "**Get Plans runs the platform's quotation validation first** (as the PA001 Get Plans does), switched by `GetPlansPlatformValidate` (MC: Y). It rejects code values outside their code table (gender, residency), an unknown risk element and non-numeric salary, but accepts a wrong ID type and marital status code (neither the platform nor our rules check them).", "A quote that was accepted before can now be refused with 400 `UP-PLATFORM-VALIDATION` or the platform's own 400. Set the key to N to return to the table-only behaviour.", "5, 9"],
        ["15", "Static type checking on push: `UPShaper.shapeResponse` returns `Object` (cast it), SMS and email builders take `requestBody(...)`, an anonymous `Comparator` may not use method variables.", "Compile errors on push usually mean one of these; the fix is a cast or a different method name.", "3.3"]], [4, 36, 46, 14])
    H2("1.5 Release History")
    TBL(["Version", "What it added"], [
        ["1.0", "13 APIs for 7 products (get plans, proposal, update, issue, load, reject, documents, cancel check and approve, master data, commission, feed file), table-driven validation, security controls, full test suite, collections."],
        ["1.1", "Insurer (`CarrierCode` / `CarrierName`, table `UP_Carrier`) in every response and an optional validated request field; developer guide and UAT plan."],
        ["1.2", "Roles (Maker, Proposal Checker, Cancellation Checker) with maker-checker rules; work queues, cancellation detail, dashboard, share by email / SMS and automatic alerts; the staff portal (UIC page) with sign-in; 5 new APIs, 3 new functions, 2 new tables, about 33 new configuration keys and 29 new field rules; analysis of PA001 and iHub. Update 5 Oct: Get Plans now runs the platform quotation validation like PA001 (key `GetPlansPlatformValidate`) and platform policy-validation errors return 400."]], [12, 88])


def sections(g):
    H1, H2, P, NOTE, BUL, NUM, TBL, CODE, LBL, FIG = (g[k] for k in ("H1", "H2", "P", "NOTE", "BUL", "NUM", "TBL", "CODE", "LBL", "FIG"))
    # ================================================================== 15
    H1("15. Workflow, Roles and Dashboard")
    H2("15.1 Overview")
    FIG("wf", "Figure 3: Maker-checker flow for proposals and cancellations")
    P("Bank staff use the portal in three roles. The **Maker** creates quotations and proposals and raises cancellation requests. The **Proposal Checker** approves (issues) or rejects submitted proposals. The **Cancellation Checker** approves or rejects cancellation requests. No new workflow state is stored by our code: the platform already holds it. A proposal waiting for approval is a platform proposal with ProposalStatus 2. A cancellation request is the platform's pending cancellation endorsement (status 120). The queues are searches over that state, so there is nothing to keep in step and nothing to clean up.")
    H2("15.2 Roles and Identity")
    P("The caller is taken from the platform token inside iComposer: `IComposerAppContext.getUserName()` and `IComposerAppContext.getIComposerCurrentUser()` (an `AppUser` with `userId`, `userName`, `realName`, `email`). The request body is never trusted for identity. The platform's own role list (`userRoleIds`) is empty for these users, so roles come from the table `UP_UserRole` (row per user and role; matched by user name, case-insensitive, or by platform user id). `UPAccess` offers:")
    TBL(["Method", "Behaviour"], [
        ["`me()`", "UserName, UserId, DisplayName, Email, Branch, Roles[], RoleEnforcement, AllowSelfApproval. Roles is omitted from the JSON when empty."],
        ["`require(roles)`", "Returns the caller; HTTP 403 `UP-403` unless the caller holds one of the roles. Does nothing when `RoleEnforcement` is not Y."],
        ["`requireAny()`", "Any of the three roles (read access to policy data)."],
        ["`requireNotCreator(caller, creatorId)`", "Maker-checker rule: 403 when the caller created the item, unless `AllowSelfApproval` = Y or enforcement is off."],
        ["`requireCreator(caller, creatorId)`", "A maker may change only what they created (update proposal). An empty creator id (older proposals) is allowed."],
        ["`holdersOf(role)` / `contactOf(userId)`", "Recipients for alerts: active rows of a role, or the row of one user id."]], [32, 68])
    P("Role names are fixed strings used in four places and must stay in step: the config keys `RoleMaker`, `RoleProposalChecker`, `RoleCancellationChecker` (values MAKER, PROPOSAL_CHECKER, CANCELLATION_CHECKER), the `Role` column of `UP_UserRole`, the `Recipient` column of `UP_NotifyTemplate`, and the `ROLE` constants of the portal.")
    LBL("Which API needs which role")
    TBL(["API", "Roles", "Extra rule"], [
        ["UPProposal (create)", "Maker", "Stamps the maker id on the proposal (15.3)."],
        ["UPUpdateProposal", "Maker", "Only the maker who created the proposal (`requireCreator`)."],
        ["UPIssue", "Proposal Checker", "Not the creator of the proposal."],
        ["UPProposalReject", "Proposal Checker", "Not the creator; a reason is required (field rule)."],
        ["UPCancelCheck", "Maker", "Creates the pending request; alert to the Cancellation Checkers."],
        ["UPCancelDetail", "Maker or Cancellation Checker", "Read only; `CanDecide` tells whether the caller may decide."],
        ["UPCancelApprove", "Cancellation Checker", "Not the person who raised the request (checked inside `UPCancelService.decide` against the endorsement's `DataEntryUserId`)."],
        ["UPWorklistApi", "PROPOSAL: Proposal Checker. CANCELLATION: Cancellation Checker or Maker. MINE: Maker.", "Type decides the role."],
        ["UPDashboard, UPShare, UPGetPlans, UPLoadPolicy, UPDocGeneration, UPApplicationDocGeneration, UPCommissionQuery", "any of the three roles", "A caller who is only a Maker sees only their own figures in the dashboard."],
        ["UPMe", "none", "Always answers; used by the portal to build the menu."],
        ["UPListMasterTable, UPFeedFile", "**no role check**", "Left open as before. Add `requireAny()` (or a checker role) to UPFeedFile if the feed must be restricted: it contains policy data."]], [30, 32, 38])
    H2("15.3 The Maker Stamp (AgentCode)")
    P("The platform search index cannot be filtered by the user who created a proposal. Of the indexed fields only `AgentCode` can carry the maker id. `UPProposal` therefore writes `AgentCode` = the caller's platform user id on every new proposal, and `UPUpdateProposal` keeps the stored value. `AgentCode` is in the server-owned field list of `UPSecurity` (`serverOwnedBaseline`), so a value sent by a caller is removed before the stamp is applied. The queue \"My submissions\" is a search with `AgentCode` = the caller's id; the maker-checker rule compares the same field with the checker's id. The id is mapped to a name through `UP_UserRole.UserId` (otherwise the platform's `DataEntryUserRealName` is shown).")
    NOTE("Consequences: proposals created before v1.2 have no maker id (they appear in the checker queue but never in \"My submissions\"); if the bank later needs real sales agent codes, another field and a new search condition are needed; the platform does not validate AgentCode against a code table (verified).")
    H2("15.4 Queues")
    LBL("Proposal queue (type PROPOSAL and MINE)")
    BUL(["`UPWorklist.proposalList` runs `ProposalSdkClient...newQueryPolicyRequestBuilder` once per enabled product (the index supports only one exact product code per query), with `ProposalStatus` and the date window on `ProposalDate`, then merges the hits by date, takes the requested page and loads each proposal of the page (channel check, maker name, plan, premium).",
         "Status codes from `UP_ApiConfig`: `ProposalStatusPending` 2, `ProposalStatusIssued` 3, `ProposalStatusRejected` 4. Filter names PENDING, ISSUED, REJECTED, ALL.",
         "Limit: `PageSize` x `PageNo` <= `WorklistMaxRows` (1,000) and at most 100 hits per product per query. `WorklistPageSize` (20) is the default page size; the portal asks for 15.",
         "Fields returned per row: ProposalNo, PolicyNo, ProductCode, ProductSubcode, ProductName, PlanId, PlanName, InsuredName, Premium, EffectiveDate, ProposalDate, Status, StatusCode, RejectReason (`ProposalRejectDesc`), Maker, MakerId, CarrierCode, CarrierName."])
    LBL("Cancellation queue (type CANCELLATION)")
    BUL(["`UPWorklist.endoSearch` calls the endorsement search `POST /platform/endo/v1/query` through `UPPlatformClient` (the same search service, endorsement index) with `EndoType` 3 (cancellation) and `EndoStatus`.",
         "`EndoStatusPending` 120 is a pending request, `EndoStatusIssued` 300 an approved cancellation, `EndoStatusWithdrawn` 600 a withdrawn one. A rejected request and a request replaced when an approval runs are both 600, so only PENDING and ISSUED can be listed.",
         "Rows add RequestNo (`EndoNo`), RequestStatus, RequestedOn and CancellationDate. Detail of one request is `UPCancelDetail`: it finds the pending endorsement with the signed policy id (as `pendingCancellation`) and returns reason (`OtherCancelReason`), requester (`DataEntryUserId` mapped to a name), the refund calculation and `CanDecide`."])
    H2("15.5 Dashboard")
    P("`UPDashboard` has two sections so that the portal can run them in parallel. `SUMMARY` returns proposal counts (pending, issued, rejected, submitted, pending older than a day), cancellation counts and a per-product split: per product three policy searches (one per status), one for pending older than a day and two endorsement searches. `COMMISSION` takes one `ProductCode`, searches the issued policies by `EffectiveDate`, loads up to `DashboardMaxPolicies` of them and returns premium, commission, policies in force and cancelled (a policy whose status is not `PolicyStatusInforce` counts as cancelled), a by-plan table and the flags `IssuedInWindow`, `Counted`, `Truncated`. The portal calls SUMMARY once and COMMISSION for each of the 7 products at the same time (8 calls).")
    BUL(["Window: `FromDate` / `ToDate`, default the last 30 days, at most `DashboardMaxDays` (180) wide; otherwise 400.",
         "Scope: `ALL` or `MINE`. A caller who holds only the Maker role is always restricted to their own submissions (`AgentCode` condition).",
         "Cost: roughly 7 to 10 seconds per call in MC (about 40 platform calls for SUMMARY; one load per policy for COMMISSION).",
         "All figures include test data created in MC."])
    H2("15.6 Maker-Checker Rule and the Test Switch")
    P("With `RoleEnforcement` = Y and `AllowSelfApproval` = N a user can never approve, reject or decide something they created. The live role check (`role_check.py`) proves this by switching `UP_UserRole` rows on and off for the single test account. With `AllowSelfApproval` = Y the rule is skipped, which is the state of MC so that one person can test the whole flow. The portal reads the switch from `/up/me` (`AllowSelfApproval`) and disables the approve and reject buttons only when the rule would refuse them.")
    H2("15.7 New API Contracts (examples)")
    P("All requests are `POST` with a JSON body and the bearer token unless noted; `ChannelCode` is `SOHAR`. Errors use the standard body (section 9). The examples are shortened from real MC responses.")
    LBL("GET /up/me")
    CODE('{ "UserName": "ravi.teja@insuremo.com", "UserId": "1188178494", "DisplayName": "Ravi Teja (test user - replace with bank staff)",\n  "Email": "ravi.teja@insuremo.com", "Branch": "001",\n  "Roles": ["MAKER", "PROPOSAL_CHECKER", "CANCELLATION_CHECKER"],\n  "RoleEnforcement": "Y", "AllowSelfApproval": "Y" }')
    LBL("POST /up/worklist")
    CODE('request : { "ChannelCode": "SOHAR", "Type": "PROPOSAL", "Status": "PENDING", "ProductCode": "HC001", "FromDate": "2026-09-03", "ToDate": "2026-10-03", "PageNo": 1, "PageSize": 15 }\nresponse: { "Type": "PROPOSAL", "Status": "PENDING", "PageNo": 1, "PageSize": 15, "Total": 117,\n  "Records": [ { "ProposalNo": "PHC0010000000243", "PolicyNo": "", "ProductCode": "HC001", "ProductName": "Hospital Cash Benefit",\n    "PlanId": "1", "PlanName": "Plan 1", "InsuredName": "Workflow Test", "Premium": 70, "Maker": "Ravi Teja (...)", "MakerId": "1188178494",\n    "ProposalDate": "2026-10-03", "Status": "Bound", "StatusCode": "2", "RejectReason": "", "CarrierCode": "AFIC", "CarrierName": "Afillar Insurance Company" } ] }')
    LBL("POST /up/dashboard (SUMMARY and COMMISSION)")
    CODE('request : { "ChannelCode": "SOHAR", "Section": "SUMMARY", "FromDate": "2026-09-03", "ToDate": "2026-10-03", "Scope": "ALL" }\nresponse: { "Proposals": { "Pending": 567, "PendingOlderThanOneDay": 563, "Issued": 429, "Rejected": 332, "Submitted": 1328 },\n  "Cancellations": { "Pending": 110, "Issued": 199 }, "ByProduct": { "HC001": { "Pending": 117, "Issued": 74, "Rejected": 51 } },\n  "FromDate": "2026-09-03", "ToDate": "2026-10-03", "Scope": "ALL" }\nrequest : { ..., "Section": "COMMISSION", "ProductCode": "HC001" }\nresponse: { "ProductCode": "HC001", "IssuedInWindow": 69, "Counted": 47, "Truncated": true, "InForce": 16, "Cancelled": 31,\n  "Premium": 3080, "Commission": 2156, "CancelledPremium": 6510, "CancelledCommission": 4557,\n  "ByPlan": [ { "PlanName": "Plan 1", "Policies": 8, "Premium": 560, "Commission": 392 } ] }')
    LBL("POST /up/cancel-detail")
    CODE('request : { "ChannelCode": "SOHAR", "PolicyNo": "POUPPA00100000072" }\nresponse: { "RequestNo": "POUPPA00100000072-001", "RequestStatus": "PENDING", "CancelReason": "spike", "CancellationDate": "2026-10-04",\n  "RequestedBy": "Ravi Teja (...)", "RequestedOn": "2026-10-03", "CanDecide": "Y", "CarrierCode": "AFIC", "CarrierName": "Afillar Insurance Company",\n  "PolicyInfo": { "PolicyNo": "...", "InsuredName": "...", "EffectiveDate": "...", "ExpiryDate": "..." }, "PolicyStatus": { "Code": "2", "Description": "Effective" },\n  "PremiumDetails": { "Premium": 68, "FreeLookDays": 15, "DaysSinceCommencement": 0, "ProRataPremium": 68 },\n  "RefundDetails": { "CancellationType": "FREE_LOOK", "RefundPercent": 100, "RefundPremium": 68 } }')
    LBL("POST /up/share")
    CODE('request : { "ChannelCode": "SOHAR", "DocType": "POLICY", "Channel": "BOTH", "PolicyNo": "POHC00100000068", "Mobile": "96891234567" }\n          (DocType QUOTATION needs "Details": { InsuredName, ProductName, PlanName, Premium, EffectiveDate } plus ProductCode / ProductSubcode and Email or Mobile)\nresponse: { "DocType": "POLICY", "Channel": "BOTH", "Notifications": [ { "Event": "SHARE_POLICY", "Recipient": "CUSTOMER", "Channel": "EMAIL", "To": "M***@gmail.com", "Status": "DRYRUN" },\n  { "Event": "SHARE_POLICY", "Recipient": "CUSTOMER", "Channel": "SMS", "To": "***4567", "Status": "DRYRUN" } ] }')
    NOTE("Existing responses gained one additive field, `Notifications[]`, on UPProposal (create), UPIssue, UPProposalReject, UPCancelCheck (only when a new request is created) and UPCancelApprove. A 403 body has `status` 403 and `code` `UP-403`.")

    # ================================================================== 16
    H1("16. Notifications (Email and SMS)")
    H2("16.1 Design")
    P("`UPNotify.fire(event, params, customer, makerUserId, onlyChannel)` reads every active row of `UP_NotifyTemplate` for the event, resolves the recipients and sends or records each message. It never throws: a problem becomes a result row, so a failed alert can not fail a proposal, an issue or a cancellation. The caller adds the result list to the response as `Notifications[]`. Recipients: a role (all active holders in `UP_UserRole`), `MAKER` (the creator of the item, looked up by platform user id) or `CUSTOMER` (the Email and Mobile of the customer, taken from the stored proposal, unmasked, or from the request of UPShare).")
    H2("16.2 Events and Templates")
    TBL(["Event", "Recipient (email and SMS each)", "Sent by"], [
        ["SUBMITTED", "Proposal Checkers", "UPProposal after a successful create"],
        ["PROPOSAL_ISSUED", "Maker, customer", "UPIssue"], ["PROPOSAL_REJECTED", "Maker", "UPProposalReject (placeholder `{Reason}`)"],
        ["CANCEL_REQUESTED", "Cancellation Checkers", "UPCancelCheck, only when a new request is created"],
        ["CANCEL_APPROVED", "Maker, customer", "UPCancelApprove (placeholder `{Refund}`)"], ["CANCEL_REJECTED", "Maker", "UPCancelApprove with REJECT"],
        ["SHARE_QUOTATION, SHARE_PROPOSAL, SHARE_POLICY", "Customer", "UPShare (event name from the keys `ShareDocQuotation`, `ShareDocProposal`, `ShareDocPolicy`)"]], [30, 34, 36])
    P("Placeholders (`{Name}`; a placeholder without a value becomes empty): ProposalNo, PolicyNo, Insured, Product, Plan, Premium, EffectiveDate, Link (`PortalUrl`), Insurer, Checker, Maker (both are the calling user's display name), RequestNo, Reason, Refund. `UPNotify.paramsOf(policy, extra)` builds them. A template row is identified by `TemplateKey` = Event|Recipient|Channel and has Subject, Body, `SmsTemplateCode` and IsActive.")
    H2("16.3 Modes and Result Status")
    TBL(["Status", "Meaning"], [["SENT", "The SNS call was made (NotifyMode LIVE)."], ["DRYRUN", "NotifyMode is not LIVE: nothing was sent. This is the state of MC."], ["NO_ADDRESS", "No email or mobile known for that recipient (for example the test user has no mobile)."],
        ["NO_SMS_TEMPLATE", "LIVE mode, SMS, and `SmsTemplateCode` is NONE."], ["FAILED", "The SNS call raised an exception (logged as `notification failed`)."]], [22, 78])
    P("The `To` value in a result is masked (`r***@insuremo.com`, `***4567`).")
    H2("16.4 SNS Integration Details")
    BUL(["Email: `SnsSdkClient.emailApi().newSendEmailRequestBuilder().requestBody(SendEmailRequest)`. Model fields (found by reflection in MC): accountName, alias, attachments, bcc, cc, content, contentAlternative, contentType, customHeaders, replyTo, senderParams, subject, templateCode, templateParams, to. The code fills `to`, `subject`, `content` and `accountName` (when `EmailAccountName` is not NONE).",
         "SMS: `smsApi().newSendSmsRequestBuilder().requestBody(SendSMSRequest)`. Model fields: accountName, autoAddSign, senderParams, signName, templateCode, templateParams, to, useZhBracket. **There is no free-text field**: the SMS is the SNS template named by `templateCode` filled with `templateParams`. The text in `UP_NotifyTemplate.Body` for SMS is therefore documentation and dry-run preview only; the real text lives in the SNS SMS template.",
         "The request model is built with `IComposerJsonUtils.mapToObject(map, Class)` from the Java field names. Whether the SNS service accepts exactly these names at runtime is unproven.",
         "MC findings: 0 email accounts and 0 SMS accounts. Email senders offered by the tenant: SENDGRID, SMTP, AWS PINPOINT, AWS SES, Microsoft Graph. SMS senders include AWS SNS, AWS End User Messaging, ALI, OneWay, EngageLab, worldSMS and several country specific ones."])
    H2("16.5 Switching to Live Delivery")
    NUM(["A tenant administrator creates an email account and an SMS account in the SNS service and, for SMS, one SMS template per message (the template parameters are the placeholder names above).",
         "Put the account names in `EmailAccountName` / `SmsAccountName` (NONE means the default account) and each SMS template code in the `SmsTemplateCode` column of the SMS rows of `UP_NotifyTemplate` (`record-save`).",
         "Check that every staff row in `UP_UserRole` has a real Email and Mobile.", "Set `NotifyMode` = LIVE (`python3 setcfg.py NotifyMode LIVE`).",
         "Exercise each event once (`role_check.py` produces all of them) and read the platform log for `notification failed` lines. Expect to adjust field names or template parameters on the first run."])

    # ================================================================== 17
    H1("17. The Portal (UIC Page)")
    H2("17.1 What and Where")
    TBL(["Item", "Value"], [
        ["Page", "Sohar Insurance Portal, path `sohar-insurance-portal`, page id 894239494239121408, tenant `uponly`, environment `portal`"],
        ["URL", "https://portal.insuremo.com/uic-web/#/p/sohar-insurance-portal (a one-time login-free link comes from `imo uic page exchange-code --path sohar-insurance-portal`)"],
        ["Source", "`uic_pages/uponly/portal/sohar-insurance-portal/index.html` (one self-contained HTML file with inline CSS and JavaScript; copy in `deliverables/Sohar_Insurance_Portal_index.html`; also `metadata.json`, `prompt.md`)"],
        ["Template", "`standard` UIC template (vanilla HTML and JavaScript, no build step, no external libraries; the charts are inline SVG)"],
        ["Size", "about 750 lines; section 17.2 lists the functions"]], [18, 82])
    TBL(["View (role)", "Screen", "APIs called"], [
        ["Dashboard (all)", "Tiles, three charts, tables by product and plan; period and scope filter", "`/up/dashboard` (SUMMARY + 7 x COMMISSION)"],
        ["New quotation (Maker)", "Step 1 quotation (basic details, plan cards, share), step 2 proposal details, step 3 submitted", "`/up/get-plans`, `/up/share`, `/up/proposal`, `/up/doc_generation`"],
        ["My submissions (Maker)", "Queue MINE with filters; detail with reject reason and PDF / share", "`/up/worklist` (MINE), `/up/load-policy`"],
        ["Proposal approvals (Proposal Checker)", "Queue PROPOSAL; detail with approve / reject (reason in a dialog), PDF, share", "`/up/worklist`, `/up/load-policy`, `/up/issue`, `/up/proposal-reject`, `/up/share`"],
        ["Cancellations (Maker, Cancellation Checker)", "Tab Requests (queue and detail with refund calculation and approve / reject), tab Raise a request (Maker)", "`/up/worklist` (CANCELLATION), `/up/cancel-detail`, `/up/cancel-check`, `/up/cancel-approve`, `/up/load-policy`"],
        ["Policies (all)", "Search by policy or proposal number; certificate / application PDF, commission, share", "`/up/load-policy`, `/up/doc_generation`, `/up/commission-query`, `/up/share`"]], [24, 44, 32])
    H2("17.2 Structure of the File")
    P("The script is organised in blocks, in this order: UIC helpers (token, tenant, URL), configuration (`CFG`, `ROLE`), utilities (`api()`, error rendering, modal, alerts), state and master data (`loadMaster`: ProductMaster, ProductRule, PremiumMode, code tables, UP_Carrier through `/up/list-master-table`), navigation by role (`NAV`, `buildNav`, `go`), shared renderers (`policySummary`, `getDoc`, `shareDialog`), the generic `Queue` class used by three views, proposal and cancellation detail, policies, the quotation wizard, the dashboard (inline SVG helpers `barSvg`, `hbarSvg`, `donutSvg`) and the wire-up (`bind`, `startApp`, sign-in / sign-out, `init`).")
    if os.path.exists(PORTAL):
        src = open(PORTAL, encoding="utf-8").read().split("\n"); rows = []
        for i, ln in enumerate(src):
            m = re.match(r"^(?:async )?function (\w+)\(([^)]*)\)", ln) or re.match(r"^class (\w+)", ln)
            if m:
                doc = ""
                prev = src[i - 1].strip() if i > 0 else ""
                if prev.startswith("/**") and prev.endswith("*/"): doc = re.sub(r"^/\*\*\s*|\s*\*/$", "", prev).strip()
                elif prev.startswith("//") and "====" not in prev: doc = prev.lstrip("/ ").strip()
                rows.append([m.group(1), m.group(2) if m.lastindex and m.lastindex > 1 else "", str(i + 1), doc[:110]])
        LBL("Function index of index.html (generated)")
        TBL(["Function", "Parameters", "Line", "Comment"], rows, [24, 22, 7, 47])
    H2("17.3 Sign-In and Session")
    BUL(["On load the page shows the sign-in screen. It offers a user name and password form and, when the browser already holds an InsureMO portal session (`sessionStorage.Authorization`), a second button \"Continue as the user signed in to InsureMO\".",
         "Sign-in: `POST {CFG.casUrl}/cas/ebao/v2/json/tickets` (same call as step 0 of the Postman collection) with headers `x-mo-user-source-id: platform`, `x-mo-tenant-id: {CFG.tenant}` and body `{username, password}`. The token is taken from the reply (`access_token`, `token`, `ticket`, `Token` or the same under `data`), as the collection's test script does. A failure shows one plain message (\"Sign-in failed. Check your user name and password.\" or \"not available\") and no server text.",
         "Storage: the token is kept in `AUTH.token` and, for a reload, in `sessionStorage.sohar_token` (this tab only). The password is never stored or logged. Two modes: `login` (own sign-in) and `session` (the portal session token).",
         "Sign-out button and idle timeout (`CFG.idleMinutes` = 30) remove the stored token and reload the page. A 401 in `login` mode signs the user out with a message; in `session` mode it redirects to the InsureMO login as the UIC template does.",
         "After sign-in `/up/me` supplies the roles; no role gives an \"Access denied\" screen. The menu is only a convenience: every API enforces the role again."])
    NOTE("Not verified: a successful sign-in with a real password (no password was available), and whether the CAS ticket service always accepts a browser cross-origin call from the portal host (preflight returned `access-control-allow-origin: *`). Test with a real user first.")
    H2("17.4 API Access")
    P("`apiUrl(path)` = `buildApiUrl(CFG.routeBase)` + path, where `buildApiUrl` is the standard UIC helper: on a gateway host it uses the path as is, otherwise it prefixes `/api`; `{{tenant_code}}` is replaced (`platform` on the portal host). `CFG.routeBase` is `/{{tenant_code}}/api-orchestration-test/v1/flow`, the same route the collections use as `baseUrl`. All tests replaced the base with a stub through `sessionStorage.sohar_api_base`. That hook is still in the code (`API_OVERRIDE`): remove it before go-live, and confirm the real in-portal URL with a first manual call.")
    H2("17.5 Configuration and Branding")
    BUL(["`CFG` (top of the script): `casUrl`, `tenant`, `idleMinutes`, `routeBase`, `channel` (SOHAR), `branch` (001), `userName` (SoharPortal, sent as UserName in quotations), `payLG` / `payLC` (payment info codes used by the reference flows), `riskCode` (R00001), `pageSize` (15).",
         "Products, variants, premium modes, age and term limits, free look and refund percent are read at start from the master data API (`UP_ProductMaster`, `UP_ProductRule`); nothing about a product is hard coded except `FEMALE_ONLY` = [FP001] (Female Protection is sold to women only).",
         "Marital status shows only the codes 1 and 2 of `InsMaritalStatus` because that code table also holds salutation values.",
         "Brand colours, font and chart colours are CSS variables in one `:root` block at the top (approximate Sohar International Bank public colours; the official guideline was not available). The logo is a text badge."])
    H2("17.6 Deploy and Test the Portal")
    TBL(["Task", "Command / script"], [
        ["Deploy a change", "`imo uic page push --file uic_pages/uponly/portal/sohar-insurance-portal/index.html --memo \"...\" --profile portal:uponly` (pull first if someone else may have changed the page: `imo uic page pull --id 894239494239121408`)"],
        ["Get a login-free link", "`imo uic page exchange-code --path sohar-insurance-portal --profile portal:uponly --json` (single use)"],
        ["Version history / rollback", "`imo uic page history list --id 894239494239121408`, `imo uic page history rollback --page-id ... --version ...`"],
        ["Browser tests (headless Chromium, stub gateway)", "`flow2.js` (23 checks: dashboard, quote, share, submit, queue, approve, reject, cancellation, policy view), `login.js` (11 checks: sign-in screen), `run.js` (12-step flow per product); run with `node <script> <outputDir> <ProductCode>`; screenshots in `deliverables/ui_test_workflow`, `ui_test_login`, `ui_test`"],
        ["Role / notification API checks", "`python3 role_check.py` (35 checks; toggles `UP_UserRole` rows and `AllowSelfApproval`, restores them at the end)"]], [32, 68])
    P("The browser tests need a valid `imo` token (they read it with `imo auth prepare`) and Playwright with Chromium. They talk to the real MC APIs and therefore create test proposals, policies and cancellations each time.")
    H2("17.7 Portal Limitations")
    BUL(["A submitted proposal cannot be edited in the portal (the API supports it for the creating maker); a rejected proposal is resubmitted as a new quotation.",
         "The proposal detail shows what the platform returns: the mobile is masked by the platform; the ID number is masked by the page (last four characters).",
         "Queues show up to 15 rows per page; all totals include test data.", "The dashboard needs 7 to 10 seconds and is capped as described in 15.5.", "No audit trail beyond the platform's own records; no export."])

    # ================================================================== 18
    H1("18. PA001, iHub and the Other Assets in the Tenant")
    P("This section records what was found about the existing PA001 solution so that nobody assumes the new products work the same way. It is based on a read-only copy of the tenant's iComposer code and tables taken earlier in this project. A second, live check was not possible when this guide was written because the `imo` login had expired, so verify anything critical in the tenant.")
    H2("18.1 What Exists")
    TBL(["Group (iComposer)", "Content", "Notes"], [
        ["`Policy_API` (group 572066178)", "13 APIs: GetPlans, Quote, Proposal, UpdateProposal, IssuePolicyAPI, ProposalReject, LoadPolicyData, DocGeneration, ApplicationDocGeneration, FeedFile, QuickProposal, CreateUpdateProposal, CreateProposalReject. 8 functions: ProposalService, UpdateProposalService, IssueService, ProposalRejectService, QuoteService, ImoAPICallerService, APICallerUtils, CreateUpdateProposalBusinessFunction.", "The PA001 flow of the reference collection (routes `/get-plans`, `/proposal`, ...)."],
        ["`POLICY_API` (group 764483681)", "17 APIs (quote, policy, claims, document and master-table APIs) and 33 functions, including the adapter functions `IhubCallerIntegrationAdapter`, `IhubTransformerCallerIntegrationAdapter`, `IhubCallerService`, `RestClientService`, `DataTableUtil`, `ExceptionHandler`, `ErrorCodeEnum`.", "Shared building blocks of the PA001 design."],
        ["`UP_PRODUCTS_API` (group 1188491119)", "Everything described in this guide.", "Created for the new products."],
        ["Platform AI group (706710450)", "About 45 `AI_*` APIs supplied by the platform.", "Not ours; do not change."]], [24, 54, 22])
    H2("18.2 How the PA001 APIs Work")
    FIG("pa001", "Figure 5: PA001 call pattern (top) compared with the new products (bottom)")
    NUM(["The API validates the request with the platform SDK (`proposalApi().newValidateRequestBuilder()` or the quotation equivalent).",
         "A service function (for example `ProposalService.getCarrierProposal`) takes the provider code (`CarrierCode`, default AFIC), the country (OM) and the transaction type code (GETPLANS, PROPOSAL, ISSUEPOLICY, UPDATEPROPOSAL, PROPOSALREJECT) and looks the numeric transaction type up in the iTable `AdapterServiceCfg` (5 rows for PA001: 10001 to 10005).",
         "`IhubCallerIntegrationAdapter.callIntegrationAdapter` builds an `IComposerIntegrationAdapterRequest` and calls the platform's integration adapter service. The adapter row names an implementation (`iComposer.IhubCallerIntegrationAdapter`) and a URL setting (`imo.motor.quote.url`, `imo.motor.proposal.url`, `imo.motor.issuepolicy.url`, `imo.motor.updateproposal.url`, `imo.motor.proposalreject.url`) that is stored in the platform's config centre.",
         "`sendRequest` then branches on `ProductMaster.IsResident` of the product: **Y** posts to the URL through `ImoAPICallerService` (an InsureMO API, no iHub); otherwise `IhubCallerService.executeIntegration` posts to an iHub integration and turns an iHub error into `IHUB_SERVICE_CALL_ERROR` / `IHUB_SERVICE_INTERNAL_ERROR`. For non-resident products the answer is also run through `CreateUpdateQuoteBusinessFunction`.",
         "Both PA001 variants have `IsResident` = Y in the product table, so PA001 should take the direct branch."])
    H2("18.3 Comparison")
    TBL(["Topic", "PA001 APIs", "New `/up` APIs"], [
        ["iComposer group", "`Policy_API` and `POLICY_API`", "`UP_PRODUCTS_API`"], ["Routes", "`/get-plans`, `/proposal`, `/issue` ...", "`/up/get-plans`, `/up/proposal`, `/up/issue` ..."],
        ["Product data tables", "`ProductMaster`, `ProductPlanRelation`, `DocTemplate`, `AdapterServiceCfg`", "`UP_ProductMaster`, `UP_ProductPlanRelation`, `UP_DocTemplate`, ... (UPDataUtil maps the logical names)"],
        ["Validation", "Platform SDK validate", "`UPValidator` with `UP_FieldRule` rows (plus the platform's own checks on save and issue)"],
        ["Backend call", "Integration adapter, URL from the config centre, direct IMO call for resident products, iHub for others", "Platform SDK and endorsement REST called directly with the caller's token"],
        ["iHub", "Available through the adapter (not used for resident products)", "Not used"], ["Settings", "Config centre keys and `AdapterServiceCfg`", "`UP_ApiConfig` (a missing key is `UP-CONFIG`)"],
        ["Errors", "`ExceptionHandler`, `ErrorCodeEnum`", "`UPErrorHandler` (400 / 403 / 404 / 409 / 500 contract)"]], [20, 42, 38])
    H2("18.4 What Is Not Known")
    BUL(["Where the config-centre URLs `imo.motor.*.url` point (they are not readable with the tools used), and therefore what the PA001 \"IMO API\" branch calls.",
         "Whether any iHub integration, validator, transformer or Rego rule exists for PA001 or any other product in the tenant (the `imo ihub integration search` command was not run successfully).",
         "Whether the code copy used for this analysis still matches the tenant (taken earlier in the project).",
         "How PA001 behaves in UAT; the UAT plan lists its dependencies."])
    P("To close these points: log in again (`imo auth login --profile portal:uponly`), run `imo ihub integration search --scope own --profile portal:uponly --json`, reload the `Policy_API` and `POLICY_API` groups into a scratch workspace (`imo icomposer init --group-id <id>`) and read the config centre values with a platform administrator. Do not change PA001: run `snapshot.py before` and `after` around any work in the same tenant.")
    H2("18.5 If iHub Is Wanted Later")
    P("A bank or carrier integration for the new products would be a new function beside `UPPlatformClient` that posts the request to an iHub integration URL held in `UP_ApiConfig` (with the allowed host list applied as `requireAllowedHost` already does), a new key per transaction type, and a switch per product in `UP_ProductRule`. The PA001 adapter (`IhubCallerIntegrationAdapter` / `AdapterServiceCfg`) can be studied but should not be shared: it is wired to PA001's rows and to `ProductMaster`.")

    # ================================================================== 19
    H1("19. Operations Runbook and Handover Checklist")
    H2("19.1 Switches and How to Change Them")
    TBL(["Key (UP_ApiConfig)", "MC now", "Meaning", "Go-live value"], [
        ["RoleEnforcement", "Y", "Role checks active. N = every API open as before v1.2.", "Y"],
        ["AllowSelfApproval", "Y", "Creator may approve own item (single test account).", "**N**"],
        ["NotifyMode", "DRYRUN", "LIVE sends through SNS, anything else records only.", "LIVE after accounts exist"],
        ["EmailAccountName / SmsAccountName", "NONE", "SNS account names (NONE = default account).", "per tenant"],
        ["PortalUrl", "https://portal.insuremo.com/uic-web/#/p/sohar-insurance-portal", "Link placed in messages.", "per environment"],
        ["DashboardMaxDays, DashboardMaxPolicies", "180, 60", "Window and per-product policy cap.", "tune"],
        ["WorklistPageSize, WorklistMaxRows", "20, 1000", "Default page size; index limit.", "keep"],
        ["EndoSearchPath, SearchPath, EndoSearchModule", "set", "Platform search routes used by the queues.", "check per tenant"]], [28, 22, 34, 16])
    P("Change a key: `python3 setcfg.py Key Value [Key Value ...]` (it reads `UP_ApiConfig` with `record-list`, saves the row with `record-save` and prints the old value). Changes apply from the next request; no deployment is needed.")
    H2("19.2 Users and Roles")
    NUM(["A platform administrator creates the person's InsureMO user in the tenant (this solution cannot create users or passwords).",
         "Add one row per role to `UP_UserRole` (`record-batch-save`; `UserRoleKey` = `user|ROLE` must be unique, `Id` unique): UserName (as the platform reports it, usually the email), UserId (platform user id, needed for alerts to the maker), Role, DisplayName, Branch, Email, Mobile, IsActive Y.",
         "To remove access set IsActive to N (`record-save`) rather than deleting the row.",
         "Check with the user's own login: the portal header shows name and roles; `GET /up/me` returns the same."])
    NOTE("`workflow_setup.py` shows the row format. Re-running the setup scripts is not idempotent for rows: the platform refuses a duplicate `Id`.")
    H2("19.3 Troubleshooting the v1.2 Features")
    TBL(["Symptom", "Likely cause", "Check"], [
        ["403 `UP-403` for everything", "User not in `UP_UserRole` or the row is inactive", "`GET /up/me`; the table rows"],
        ["403 on approve / reject", "Maker-checker rule (creator = caller) with `AllowSelfApproval` = N", "`cancel-detail` shows `CanDecide`; use another checker"],
        ["Queue is empty but proposals exist", "Date window, product filter, or search index delay of a few seconds after a change", "Retry; check `ProposalStatus` of the proposal"],
        ["\"My submissions\" misses old proposals", "Created before v1.2 (no AgentCode)", "Expected"],
        ["Dashboard slow or truncated", "Cap `DashboardMaxPolicies`; many policies", "Narrow the window; raise the cap carefully"],
        ["`Notifications` show DRYRUN", "`NotifyMode` is not LIVE", "Section 16.5"],
        ["`NO_ADDRESS` for the maker", "The maker has no row (UserId) or no Email in `UP_UserRole`", "Add the user row"],
        ["Portal: \"Access denied\"", "User has no role", "Add roles (19.2)"],
        ["Portal: first call returns 404", "Route prefix of the real portal frame", "Section 17.4; browser network tab"],
        ["Sign-in always fails", "Wrong credentials, user in another tenant, or reply field name different", "Browser network tab for the ticket call; compare with Postman step 0"],
        ["Push fails with `token is invalid or expired`", "`imo` login expired (24 hours)", "`imo auth login --profile portal:uponly`"]], [30, 40, 30])
    H2("19.4 Go-Live Checklist for the v1.2 Additions")
    NUM(["Replace the test rows of `UP_UserRole` with bank staff; set `AllowSelfApproval` = N; run `role_check.py` (it flips the switch temporarily: run it in a test tenant, or accept the brief change).",
         "Create SNS email and SMS accounts and templates; fill the account keys and `SmsTemplateCode`; set `NotifyMode` = LIVE; send one test of every event.",
         "Delete the probe API `UPSpikeWho`; remove the `sohar_api_base` hook (`API_OVERRIDE`) from the portal; confirm the in-portal route with a manual call.",
         "Verify a real password sign-in (field name of the CAS reply).",
         "Decide about role checks on `UPFeedFile` and `UPListMasterTable`; decide about masking the ID number and the platform `TempData` block.",
         "Update the specification, UAT plan and checklist, policy model, OpenAPI and Postman collection for the new APIs, tables and keys.",
         "Re-run the full suites: `run_tests.py`, `carrier_check.py`, `role_check.py`, the three browser scripts, `security_probe.py`, `snapshot.py` before / after.",
         "Decide what to do with the test data in the tenant (it cannot be deleted through the APIs)."])
    H2("19.5 What a New Developer Needs")
    TBL(["Need", "Detail"], [
        ["Access", "An InsureMO user in the MC tenant with iComposer, iTables, product configuration and UIC rights; the `imo` CLI logged in (`imo auth login --profile portal:uponly`). No passwords or tokens are stored in the repository or in this guide."],
        ["Repository", "Branch `claude/wizardly-newton-ivfnle` of br8innovates/Tablet. Portal: `uic_pages/`. Delivered copies and tests: `deliverables/` (`workflow_src/ic_src` holds the iComposer source of v1.2 and the set-up and test scripts; `ui_test*` hold the screenshots). The full build folder (document generators, test suites, samples) is in the package zip."],
        ["Order of reading", "Section 1.4, then 2, 15, 17, 18; then 4 (code reference) next to the source; then 6 (configuration) and 19."],
        ["First actions", "`GET /up/me`; run `role_check.py` (several minutes); open the portal and walk the flow in all three views; read `UPAccess`, `UPWorklist`, `UPNotify` (about 450 lines together)."]], [20, 80])
    H2("19.6 Backlog (Consolidated)")
    TBL(["#", "Item", "Suggested action"], [
        ["1", "Notifications never exercised LIVE", "Section 16.5"], ["2", "Real password sign-in untested; portal URL in the real frame untested", "Manual verification, then remove `sohar_api_base`"],
        ["3", "No role check on UPFeedFile / UPListMasterTable", "Add `requireAny()` or a checker role"], ["4", "Maker id in AgentCode", "Dedicated field or index field when the platform allows"],
        ["5", "Dashboard accuracy and speed (cap 60, 7 to 10 s)", "Pre-aggregation (batch) or a reporting table if figures must be exact"], ["6", "Rejected cancellation requests not listable", "Record the decision outside the platform or read endorsement history"],
        ["7", "No audit table (who approved what, when)", "Audit table or the platform audit module"], ["8", "ID number and `TempData` in responses", "Mask / strip in `UPShaper`"],
        ["9", "Edit of a submitted proposal in the portal", "Add an edit view (fields are masked in the load response: ask for them again)"], ["10", "Documents lag behind the code", "Update specification, plan, model, OpenAPI, collection"],
        ["11", "PA001 / iHub open questions (18.4)", "Live check after login"], ["12", "Unit tests for pure functions", "Data-driven tests"],
        ["13", "Wrong ID type and marital status codes are accepted by Get Plans (neither the platform validation nor `UP_FieldRule` checks them)", "Add `UP_FieldRule` rows with `CodeTable` IdType / InsMaritalStatus (note the odd values in InsMaritalStatus)"]], [5, 50, 45])
