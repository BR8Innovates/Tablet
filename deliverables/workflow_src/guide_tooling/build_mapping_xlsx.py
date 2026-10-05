#!/usr/bin/env python3
"""Workbook 'our APIs vs platform APIs': per our API the platform calls (SDK operation or REST) and the platform request. Built from the Groovy source, UP_ApiConfig values and recorded samples."""
import json, os, re, glob, copy
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
B = os.environ["B"]; SRC = B + "/ic/src/dev/Tenant/UP_PRODUCTS_API"
CFG = {r["Key"]: r["Value"] for r in json.load(open(B + "/devdata/tables.json"))["UP_ApiConfig"]["records"]}
assets = {a["name"]: a for a in json.load(open(B + "/devdata/assets.json")) if a["kind"] == "api"}
J = lambda o: re.sub(r"\{\{(\w+)\}\}", r"<\1>", json.dumps(o, indent=2, ensure_ascii=False))

# ------------------------------------------------------------------ platform requests (distinct)
base = json.load(open(B + "/samples/ref/HC001_1_P1/02_proposal.json"))["request"]["body"]
app = copy.deepcopy(base)
risk = app["PolicyLobList"][0]["PolicyRiskList"][0]; risk.pop("PlanList", None); app.pop("DuePremium", None)
for k in ("PolicyNo", "PolicyId", "PolicyElementId", "ProposalStatus", "PolicyStatus"): app.pop(k, None)
pay = app.pop("PolicyPaymentInfoList")[0]
app.update({"PaymentLGCode": pay["LGCode"], "PaymentLCCode": str(pay["LCCode"]), "PaymentDebitAccountNo": pay["DebitAccountNo"], "PaymentDebitRefNo": pay["DebitRefNo"], "PaymentIsInstallment": pay["IsInstallment"], "PaymentTransactionDate": pay["TransactionDate"]})
app["OrgCode"] = "1 (default when the caller sends none)"; app["AgentCode"] = "<platform user id of the maker>"
app["ChannelCode"] = "SOHAR"
endo = {"EndoEffectiveDate": "<policy start (free look) or the cancellation date>", "EndoType": CFG["EndoTypeCancel"], "CancelType": CFG["CancelTypeFreeLook"] + " (free look) or " + CFG["CancelTypeProRata"] + " (pro-rata)", "CancelReasonCode": CFG["CancelReasonCode"], "OtherCancelReason": "<reason sent by the maker>",
        "PolicyNo": "<PolicyNo>", "ProductId": "<policy.ProductId>", "ProductCode": "<policy.ProductCode>", "EndorsementPaymentInfoList": [{"PayModeCode": CFG["CancelPayMode"], "IsInstallment": CFG["CancelInstallmentFlag"], "InstallmentType": CFG["CancelInstallmentType"]}]}
search = {"Conditions": {"ProductCode": "<one product per query>", "ProposalStatus": 2, "AgentCode": "<maker id, MINE and dashboard only>"}, "FromRangeConditions": {"ProposalDate": "<FromDate>T00:00:00"}, "ToRangeConditions": {"ProposalDate": "<ToDate>T23:59:59"},
          "PageNo": 1, "PageSize": "min(PageSize x PageNo, 100)", "SortField": CFG["SearchSortField"], "SortType": CFG["SearchSortType"], "Module": CFG["SearchModule"]}
endosearch = {"Conditions": {"ProductCode": "<product>", "EndoType": CFG["EndoTypeCancelFilter"], "EndoStatus": CFG["EndoStatusPending"] + " pending / " + CFG["EndoStatusIssued"] + " issued"}, "FromRangeConditions": {}, "ToRangeConditions": {}, "PageNo": 1, "PageSize": "min(PageSize x PageNo, 100)", "SortField": CFG["SearchSortField"], "SortType": CFG["SearchSortType"], "Module": CFG["EndoSearchModule"]}
printreq = {"template_name": "<UP_DocTemplate.TemplateName>", "template_version": CFG["TemplateVersion"], "print_data": "<built by UPDocBuilder.buildPrintData from the loaded policy>", "export_file_type": CFG["PrintExportType"], "storage_config": CFG["PrintStorage"], "async_or_sync": CFG["PrintMode"]}
R = [  # id, service, operation, method, path / SDK call, parameters, body, config keys, where in code, response used
 ("R01", "Proposal", "application (create proposal)", "POST", "SDK ProposalSdkClient.proposalApi().newApplicationRequestBuilder().requestBody(payload)", "-", app, "OrgCode (default), ServerOwnedFields baseline, RiskElementCode", "UPProposal.groovy; UPProductData.prepareProposal; UPSecurity.stripServerOwned / defaultOrgCode", "Created proposal (ProposalNo, PolicyId, premium after platform rating)"),
 ("R02", "Proposal", "load", "GET", "SDK proposalApi().newLoadRequestBuilder().proposalNo(x) | .policyNo(x) .withCodeDesc(Y)", "proposalNo or policyNo; withCodeDesc = TrueValue (Y)", None, "TrueValue", "UPLoadPolicy, UPUpdateProposal, UPIssue, UPProposalReject, UPCancelService, UPDocService, UPWorklist, UPCommissionQuery, UPFeedFile", "Full stored proposal / policy (including masked and encrypted TempData)"),
 ("R03", "Proposal", "save (update proposal)", "POST", "SDK proposalApi().newSaveRequestBuilder().requestBody(payload)", "-", dict(app, ProposalNo="<ProposalNo>", PolicyId="<stored.PolicyId>", PolicyElementId="<stored.PolicyElementId>", VersionSeq="<stored.VersionSeq>", AgentCode="<stored.AgentCode>"), "-", "UPUpdateProposal.groovy", "Saved proposal (calculated plan row dropped by the platform)"),
 ("R04", "Proposal", "persistCalculate", "POST", "SDK proposalApi().newPersistCalculateRequestBuilder().requestBody(policy)", "-", "<the save response (update-proposal) or the stored proposal (issue with Recalculate = Y)>", "-", "UPUpdateProposal, UPIssue", "Proposal with premium factors recalculated and persisted"),
 ("R05", "Proposal", "issuePolicy", "POST", "SDK proposalApi().newIssuePolicyRequestBuilder().requestBody(map)", "-", {"ProposalNo": "<ProposalNo>"}, "-", "UPIssue.groovy", "Policy with PolicyNo"),
 ("R06", "Proposal", "reject", "POST", "SDK proposalApi().newRejectRequestBuilder().rejectVo(RejectVo)", "-", {"ProposalNo": "<ProposalNo>", "ProposalRejectDesc": "<reason, 3 to 200 characters>"}, "SuccessStatusText (our reply)", "UPProposalReject.groovy", "none used (our reply is {status, message})"),
 ("R07", "Search", "queryPolicy (policy index)", "POST", "SDK proposalApi().newQueryPolicyRequestBuilder().searchCondition(sc) ; REST path " + CFG["SearchPath"], "-", search, "SearchSortField, SearchSortType, SearchModule, DayStartTime, DayEndTime, ProposalStatusPending / Issued / Rejected, WorklistMaxRows", "UPWorklist.policySearch; UPCommissionQuery; UPFeedFile", "Total and EsDocs (PolicyNo, ProposalNo, ProposalStatus, PolicyStatus, ProductCode, dates; premium is 0 in the index)"),
 ("R08", "Search", "endorsement query", "POST", "REST " + CFG["EndoSearchPath"] + " (via UPPlatformClient.call)", "-", endosearch, "EndoSearchPath, EndoSearchModule, EndoTypeCancelFilter, EndoStatusPending (120), EndoStatusIssued (300)", "UPWorklist.endoSearch", "QueryResult.Results[].EsDocs (EndoNo, PolicyNo, EndoStatus, EndoEffectiveDate, FirstDataEntryDate)"),
 ("R09", "Proposal (REST)", "load with signed policy id", "GET", "REST " + CFG["ProposalLoadPath"] + "?policyNo=<PolicyNo>", "policyNo", None, "ProposalLoadPath, GatewayUrl, AllowedHosts", "UPCancelService.pendingCancellation", "PolicyId in the form <id>,<signature>"),
 ("R10", "Endorsement", "queryPendingEndo", "GET", "REST " + CFG["EndoBasePath"] + "/queryPendingEndo?policyId=<signed id>", "policyId (signed, sent once-encoded)", None, "EndoBasePath", "UPCancelService.pendingCancellation", "Pending endorsement (EndoNo, EndoId, EndoType, CancelType, OtherCancelReason, EndoEffectiveDate, DataEntryUserId, InsertTime) or empty"),
 ("R11", "Endorsement", "createEx", "POST", "REST " + CFG["EndoBasePath"] + "/createEx", "-", endo, "EndoTypeCancel, CancelTypeFreeLook, CancelTypeProRata, CancelReasonCode, CancelPayMode, CancelInstallmentFlag, CancelInstallmentType", "UPCancelService.createRequest", "The endorsement (EndoNo, EndoId, NewPolicy); on approval it is the body of calculateEx"),
 ("R12", "Endorsement", "calculateEx", "POST", "REST " + CFG["EndoBasePath"] + "/calculateEx", "-", "<the createEx response of the fresh endorsement>", "EndoBasePath", "UPCancelService.decide", "Calculated endorsement (body of validate and issueEndorsement)"),
 ("R13", "Endorsement", "validate", "POST", "REST " + CFG["EndoBasePath"] + "/validate", "-", "<the calculateEx response>", "EndoBasePath", "UPCancelService.decide", "HTTP 200 / 204 = valid; OrgCode is checked against code table PubBranch"),
 ("R14", "Endorsement", "issueEndorsement", "POST", "REST " + CFG["EndoBasePath"] + "/issueEndorsement", "-", "<the calculateEx response>", "EndoBasePath", "UPCancelService.decide", "HTTP 200; the policy becomes Cancelled"),
 ("R15", "Endorsement", "suspendEndorsement", "POST", "REST " + CFG["EndoBasePath"] + "/suspendEndorsement?endoId=<EndoId>", "endoId", None, "EndoBasePath", "UPCancelService.suspend", "HTTP 200 / 204"),
 ("R16", "Print", "printtask generate", "POST", "REST " + CFG["PrintUrl"] + " (headers: Authorization Bearer <caller token>, x-mo-tenant-id)", "-", printreq, "PrintUrl, TemplateVersion, PrintExportType, PrintStorage, PrintMode, AllowedHosts", "UPDocService.generate", "data.target_file_content (base64 PDF)"),
 ("R17", "SNS", "send email", "POST", "SDK SnsSdkClient.emailApi().newSendEmailRequestBuilder().requestBody(SendEmailRequest)", "-", {"to": ["<recipient email>"], "subject": "<rendered subject>", "content": "<rendered body>", "accountName": "<EmailAccountName, omitted when NONE>"}, "NotifyMode (LIVE only), EmailAccountName", "UPNotify.sendOne", "none used (result row SENT / FAILED)"),
 ("R18", "SNS", "send SMS", "POST", "SDK smsApi().newSendSmsRequestBuilder().requestBody(SendSMSRequest)", "-", {"to": "<mobile>", "templateCode": "<UP_NotifyTemplate.SmsTemplateCode>", "templateParams": "<placeholder map>", "accountName": "<SmsAccountName, omitted when NONE>"}, "NotifyMode (LIVE only), SmsAccountName", "UPNotify.sendOne", "none used"),
 ("R19", "Tables", "getDataTableByName", "GET", "SDK TablesSdkClient.dataTableApi().newGetDataTableByNameRequestBuilder().dataTableConditionVo(vo)", "dataTableName = UP_ table name", None, "-", "UPDataUtil.readRecords (read once per request and cached)", "All rows of the table"),
]
RID = {r[0]: r for r in R}
# ------------------------------------------------------------------ call map  (api, step, purpose, request id, condition, what we add)
CM = [
 ("UPGetPlans", "/up/get-plans", "POST", "any role", [("1", "Read plan, benefit, rule and insurer rows", "R19", "always", "Builds the plan list from the tables; no proposal or rating call. Age, term, premium mode and insurer checks.")]),
 ("UPProposal", "/up/proposal", "POST", "Maker", [("1", "Create the proposal", "R01", "always", "Field-rule validation, drops PlanList and DuePremium (platform rating decides them), strips server-owned fields, defaults OrgCode, flattens payment info, stamps AgentCode (maker id)."), ("2", "Alert the Proposal Checkers (SUBMITTED)", "R17", "NotifyMode = LIVE; recorded as DRYRUN otherwise"), ("2", "Alert the Proposal Checkers (SUBMITTED)", "R18", "NotifyMode = LIVE; recorded as DRYRUN otherwise")]),
 ("UPUpdateProposal", "/up/update-proposal", "POST", "Maker (creator only)", [("1", "Load the stored proposal", "R02", "always", "404 when missing, channel / product / open-state checks, creator check."), ("2", "Save", "R03", "always", "Copies PolicyId, PolicyElementId, VersionSeq and the stored AgentCode into the payload."), ("3", "Recalculate", "R04", "always", "The platform save drops the calculated plan row, so premium is recalculated and persisted.")]),
 ("UPIssue", "/up/issue", "POST", "Proposal Checker (not the creator)", [("1", "Load the proposal", "R02", "always", "404, channel, product match, open-state and maker-checker checks."), ("2", "Recalculate", "R04", "only when Recalculate = Y is sent", "Optional, not part of the public contract."), ("3", "Issue", "R05", "always", "Shapes the policy (commission switch, insurer)."), ("4", "Alert maker and customer", "R17", "LIVE only (DRYRUN otherwise)"), ("4", "Alert maker and customer", "R18", "LIVE only (DRYRUN otherwise)")]),
 ("UPLoadPolicy", "/up/load-policy", "GET", "any role", [("1", "Load by policyNo or proposalNo", "R02", "always", "Channel check, commission removed, payment info rebuilt, insurer added.")]),
 ("UPProposalReject", "/up/proposal-reject", "POST", "Proposal Checker (not the creator)", [("1", "Load the proposal", "R02", "always", "404, channel, product match, open state."), ("2", "Reject", "R06", "always", "Reason required (field rule)."), ("3", "Alert the maker", "R17", "LIVE only (DRYRUN otherwise)"), ("3", "Alert the maker", "R18", "LIVE only (DRYRUN otherwise)")]),
 ("UPDocGeneration", "/up/doc_generation", "POST", "any role", [("1", "Load the policy or proposal", "R02", "always", "Channel check."), ("2", "Generate the PDF", "R16", "unless PreviewData = Y", "Template from UP_DocTemplate, bilingual print data from UPDocBuilder, print host must be in AllowedHosts.")]),
 ("UPApplicationDocGeneration", "/up/application_doc_generation", "POST", "any role", [("1", "Load the proposal", "R02", "always", "Channel check."), ("2", "Generate the PDF", "R16", "unless PreviewData = Y", "Same as UPDocGeneration with DocType Application.")]),
 ("UPCancelCheck", "/up/cancel-check", "POST", "Maker", [("1", "Load the policy (by policyNo, or by proposalNo then policyNo)", "R02", "always", "Must be issued, in force and enabled for the API."), ("2", "Get the signed policy id", "R09", "always", "The endorsement service needs the id with its signature."), ("3", "Find an open request", "R10", "always", "Another kind of pending endorsement blocks the request (409); an existing cancellation is shown again."), ("4", "Create the pending request", "R11", "no pending request exists", "The refund is calculated in our code (free look 100%, then pro-rata x 80%); the platform calculates none."), ("5", "Alert the Cancellation Checkers", "R17", "new request; LIVE only"), ("5", "Alert the Cancellation Checkers", "R18", "new request; LIVE only")]),
 ("UPCancelApprove", "/up/cancel-approve", "POST", "Cancellation Checker (not the requester)", [("1", "Load the policy", "R02", "always", "Channel and product checks."), ("2", "Get the signed policy id", "R09", "always", ""), ("3", "Find the pending request", "R10", "always", "RequestNo must match (404 otherwise); requester must not be the caller."), ("4", "Withdraw the saved request", "R15", "always (reject, and first step of approve)", ""), ("5", "Create a fresh endorsement", "R11", "Decision = APPROVE", "Saved request is thin: calculateEx needs the full new policy that only createEx returns."), ("6", "Calculate", "R12", "Decision = APPROVE", ""), ("7", "Validate", "R13", "Decision = APPROVE", "A platform refusal becomes HTTP 409 with the new request left pending."), ("8", "Issue the endorsement", "R14", "Decision = APPROVE", "The policy becomes Cancelled."), ("9", "Load the policy again", "R02", "Decision = APPROVE", "Returns the new status."), ("10", "Alert maker and customer", "R17", "LIVE only"), ("10", "Alert maker and customer", "R18", "LIVE only")]),
 ("UPCancelDetail", "/up/cancel-detail", "POST", "Maker or Cancellation Checker", [("1", "Load the policy", "R02", "always", ""), ("2", "Get the signed policy id", "R09", "always", ""), ("3", "Read the pending request", "R10", "always", "Shows requester, reason, refund calculation and CanDecide; creates nothing.")]),
 ("UPListMasterTable", "/up/list-master-table", "POST", "no role check", [("1", "Read the table", "R19", "always", "Only tables listed in MasterTables; commission column removed.")]),
 ("UPCommissionQuery", "/up/commission-query", "POST", "any role", [("1", "By policy: load", "R02", "PolicyNo sent", "Commission shown only by this API."), ("2", "By period: search issued policies", "R07", "FromDate / ToDate sent", "Page totals; the index holds no premium."), ("3", "By period: load every hit", "R02", "FromDate / ToDate sent", "Channel filter; premium and commission read from the policy."), ("4", "By configuration: read plan rows", "R19", "ProductCode without dates", "No platform call except the tables.")]),
 ("UPFeedFile", "/up/generate-feedfile", "POST", "no role check", [("1", "Search policies", "R07", "always", "Capped by FeedMaxRecords / FeedMaxPages."), ("2", "Load every hit", "R02", "always", "Columns from UP_FeedColumn; Excel or JSON output.")]),
 ("UPWorklistApi", "/up/worklist", "POST", "by Type: Proposal Checker / Maker / Cancellation Checker", [("1", "Proposal queue: search per product", "R07", "Type PROPOSAL or MINE", "Status, dates; MINE adds AgentCode = caller. Merged and paged in our code."), ("2", "Proposal queue: load each row shown", "R02", "Type PROPOSAL or MINE", "Maker name, plan, premium, reject reason."), ("3", "Cancellation queue: endorsement search per product", "R08", "Type CANCELLATION", "Only PENDING and ISSUED can be listed."), ("4", "Cancellation queue: load each row shown", "R02", "Type CANCELLATION", "")]),
 ("UPDashboard", "/up/dashboard", "POST", "any role (maker-only sees own)", [("1", "SUMMARY: policy searches (about 4 per product)", "R07", "Section SUMMARY", "Counts only (PageSize 1)."), ("2", "SUMMARY: endorsement searches (2 per product)", "R08", "Section SUMMARY", "Pending and issued cancellations."), ("3", "COMMISSION: search issued policies of one product", "R07", "Section COMMISSION", "Up to DashboardMaxPolicies (60)."), ("4", "COMMISSION: load each policy", "R02", "Section COMMISSION", "Premium and commission per policy, by plan.")]),
 ("UPShare", "/up/share", "POST", "any role", [("1", "Load the proposal / policy", "R02", "DocType PROPOSAL or POLICY", "Channel check; contact from the request or the stored record."), ("2", "Send email", "R17", "Channel EMAIL or BOTH; LIVE only"), ("2", "Send SMS", "R18", "Channel SMS or BOTH; LIVE only")]),
 ("UPMe", "/up/me", "GET", "none", []),
 ("UPCancelPolicy", "/up/cancel-policy", "-", "retired (inactive)", []),
 ("UPSpikeWho", "/up/spike-who", "POST", "inactive probe", []),
]
# ------------------------------------------------------------------ coverage check against the Groovy source
found = set()
for f in glob.glob(SRC + "/*/*/*.groovy"):
    t = open(f).read()
    for m in re.findall(r"new(\w+)RequestBuilder\(\)", t): found.add(m)
    for m in re.findall(r'client\.call\("(\w+)", ?(?:util\.cfgValue\(config, "\w+"\)|util\.cfg\("\w+", "\*"\)|endoBase|[^,]*?)\s*\+?\s*"?([/\w?=]*)', t): pass
need = {"Application", "Load", "Save", "PersistCalculate", "IssuePolicy", "Reject", "QueryPolicy", "GetDataTableByName", "SendEmail", "SendSms"}
assert need <= found, (need - found)
assert found <= need, ("platform call in the source but not in the workbook:", found - need)
used = {c[2] for api in CM for c in api[4]}
for must in ("R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19"): assert must in used, must
rest = set()
for f in glob.glob(SRC + "/*/*/*.groovy"):
    t = open(f).read()
    for m in re.findall(r'"/(createEx|calculateEx|validate|issueEndorsement|suspendEndorsement|queryPendingEndo)', t): rest.add(m)
assert rest == {"createEx", "calculateEx", "validate", "issueEndorsement", "suspendEndorsement", "queryPendingEndo"}, rest
# ------------------------------------------------------------------ workbook
wb = Workbook(); wb.remove(wb.active)
HEAD = PatternFill("solid", fgColor="1F3864"); thin = Side(style="thin", color="BBBBBB"); BORDER = Border(top=thin, bottom=thin, left=thin, right=thin)
def sheet(name, head, rows, widths, mono=()):
    ws = wb.create_sheet(name); ws.append(head)
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = HEAD; c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows: ws.append(r)
    for i, w in enumerate(widths): ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top"); c.border = BORDER
            if c.column in mono: c.font = Font(name="Consolas", size=9)
    ws.freeze_panes = "A2"
    if rows: ws.auto_filter.ref = ws.dimensions
    return ws
S = lambda b: b if isinstance(b, str) else J(b)
sheet("README", ["Item", "Value"], [
    ["Title", "Afillar Insurance APIs: our APIs against the platform APIs they call (v1.2)"],
    ["What it shows", "Per API of ours (routes /up/...), the platform calls it makes, in order, with the platform request. Sheets: Summary (one row per API), Call Map (one row per platform call), Platform Requests (the request of each distinct platform call, with an example body), What We Add (checks and shaping around the call), PA001 vs UP."],
    ["How to read the request", "Angle brackets <...> are values taken at run time. Values in plain text come from UP_ApiConfig (the key is named in the Config keys column). 'SDK' means an iComposer SDK client call; 'REST' means a call made with the caller's bearer token through UPPlatformClient. All platform calls use the caller's own token."],
    ["Source", "Groovy files in ic/src/dev/Tenant/UP_PRODUCTS_API, UP_ApiConfig values of the MC tenant, recorded request samples. The workbook generator checks that every platform call found in the source appears in it."],
    ["Limit", "The requests are rebuilt from the code and samples; they were NOT captured on the wire (no trace access). REST paths are given where the code names a path; for SDK calls the SDK operation is given because the code does not name the underlying path. The field names of the proposal payload are those of our own contract and the platform policy JSON."],
    ["Common to every API", "Every API reads the UP_ tables through the Tables SDK (R19, cached per request), validates the body (UP_FieldRule), checks the role (UPAccess) and returns the standard error body. These are not repeated per row except where they are the only platform call."]], [24, 120])
summ = []
for api, route, meth, roles, calls in CM:
    svc = sorted({RID[c[2]][1] for c in calls if c[2] != "R19"} | ({"Tables"} if any(c[2] == "R19" for c in calls) else set()))
    writes = sorted({RID[c[2]][2] for c in calls if RID[c[2]][2] in ("application (create proposal)", "save (update proposal)", "issuePolicy", "reject", "createEx", "suspendEndorsement", "issueEndorsement", "send email", "send SMS")})
    a = assets.get(api, {})
    summ.append([api, route, meth, roles, len(calls), ", ".join(svc) or "none", ", ".join(writes) or "none (read only)", a.get("version", ""), "inactive" if a.get("status") == 0 else "active"])
sheet("Summary", ["Our API", "Route", "Method", "Role required", "Platform calls (rows in Call Map)", "Platform services touched", "Platform writes", "Server version", "Status"], summ, [26, 32, 8, 34, 14, 40, 56, 10, 10])
rows = []
for api, route, meth, roles, calls in CM:
    for step, purpose, rid, cond, *add in calls:
        r = RID[rid]; rows.append([api, route, step, purpose, r[1], r[2], r[3], r[4], r[5], rid, S(r[6]) if r[6] is not None else "(no body)", r[9], cond, add[0] if add else ""])
sheet("Call Map", ["Our API", "Our route", "Step", "Purpose", "Platform service", "Platform operation", "HTTP", "Platform call (SDK or REST)", "Request parameters", "Request id", "Platform request body (example)", "Platform response used", "Condition", "What our API adds"], rows, [22, 24, 6, 34, 14, 24, 7, 52, 28, 8, 70, 40, 28, 56], mono=(11,))
sheet("Platform Requests", ["Id", "Platform service", "Operation", "HTTP", "Platform call (SDK or REST)", "Request parameters", "Request body (example, built from the code)", "Config keys supplying values", "Code location", "Platform response used"], [[r[0], r[1], r[2], r[3], r[4], r[5], S(r[6]) if r[6] is not None else "(no body)", r[7], r[8], r[9]] for r in R], [6, 14, 26, 7, 56, 30, 70, 44, 40, 44], mono=(7,))
ADD = [
 ["All APIs", "Platform: each API is an independent call with its own input rules.", "Validate every field by rule (UP_FieldRule), scan text for blocked characters, one error body (400 / 403 / 404 / 409 / 500 with trace id), caller's token only, hosts restricted (AllowedHosts), roles (UPAccess), channel isolation (ChannelCode)."],
 ["UPGetPlans", "Platform has quotation and rating services.", "No platform call: plans and premiums come from the UP_ tables, so Get Plans is fast and the premium equals the one the rating gives later."],
 ["UPProposal", "Platform: create a proposal from the full policy JSON; rating `<CODE>_PREM_CALC` runs inside.", "Removes the plan and premium the caller sent, removes server-owned fields, defaults the branch (OrgCode 1 is the only value the endorsement validation accepts), flattens payment info, stamps the maker id, adds the insurer, alerts the checkers."],
 ["UPUpdateProposal", "Platform: save replaces the data and drops the calculated plan row.", "Recalculates and persists after the save; keeps ids and version from the stored record; only the creating maker."],
 ["UPIssue", "Platform: issuePolicy issues whatever proposal number is sent.", "Checks channel, product and open state first; maker-checker rule; optional recalculation; alerts."],
 ["UPProposalReject", "Platform: reject with a reason value.", "Requires the reason by rule, checks channel and open state, maker-checker rule, alert to the maker."],
 ["UPLoadPolicy", "Platform: load returns the full stored policy.", "Channel check, commission hidden, payment info rebuilt, insurer added, code descriptions."],
 ["UPDocGeneration", "Platform: print service merges a template with data.", "Chooses the template per product / variant / document, builds bilingual print data (wording and benefit texts from tables), checks the print host, returns the PDF."],
 ["UPCancelCheck / UPCancelApprove", "Platform: endorsement service (createEx, calculateEx, validate, issueEndorsement, suspendEndorsement) with no refund rule.", "Refund rule (free look then pro-rata x percent) in our code; signed policy id handling; one approve call replaces five steps; fresh endorsement on approval; clear 409 on a platform refusal; maker-checker rule; alerts."],
 ["UPWorklistApi / UPDashboard", "Platform: policy and endorsement search index (1,000 rows per query, no channel, no maker except AgentCode, premium 0).", "Per-product search, merge, paging, row enrichment by load, caps and window limits, maker filter via AgentCode, counts and totals."],
 ["UPShare", "Platform: SNS sends one email or SMS per call.", "Template per event and channel, placeholders, recipients from the request or the stored record, dry-run mode, masked results."],
 ["UPCommissionQuery / UPFeedFile", "Platform: search and load.", "Commission only here; page totals; channel filter; feed columns from UP_FeedColumn; size caps."]]
sheet("What We Add", ["Our API", "What the platform alone does", "What our API adds"], ADD, [30, 60, 100])
sheet("PA001 vs UP", ["Topic", "PA001 APIs (group Policy_API / POLICY_API)", "New products (group UP_PRODUCTS_API)", "Status"], [
    ["Flow", "API -> platform SDK validate -> service function -> IhubCallerIntegrationAdapter -> AdapterServiceCfg (5 rows: 10001 GETPLANS ... 10005 PROPOSALREJECT) -> URL from config-centre key imo.motor.*.url", "API -> UPValidator -> role check -> platform SDK / REST directly -> shape response", "From a read-only copy of the tenant code taken earlier; not re-verified live"],
    ["Branch by product", "ProductMaster.IsResident = Y: ImoAPICallerService posts to the configured URL (an InsureMO API). Otherwise IhubCallerService posts to an iHub integration.", "No branch; no iHub.", "PA001 variants are IsResident = Y"],
    ["Routes", "/get-plans, /proposal, /update-proposal, /issue, /proposal-reject, /load-policy ...", "/up/get-plans, /up/proposal, /up/update-proposal, /up/issue, /up/proposal-reject, /up/load-policy ...", ""],
    ["Where the call goes", "Unknown: the config-centre URLs were not readable.", "Documented in the Call Map.", "Open question"],
    ["Settings", "Config centre and AdapterServiceCfg", "UP_ApiConfig", ""]], [20, 70, 60, 36])
out = B + "/final2/Afillar_API_vs_Platform_Mapping_v1.2.xlsx"; wb.save(out)
print("saved", out, {ws.title: ws.max_row - 1 for ws in wb.worksheets})
