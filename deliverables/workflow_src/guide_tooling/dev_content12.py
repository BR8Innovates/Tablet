"""Developer guide v1.2 content (block list). Reference sections are generated from the real source, tables and scripts; sections 1.4, 1.5 and 15 to 19 are in dev12_sections.py."""
import json, os, re
import code_facts as cf
import dev12_sections as ns
INSURER = "Afillar Insurance Company"
blocks = []
def H1(t): blocks.append(("h1", t))
def H2(t, page=False): blocks.append(("h2", t, page))
def P(t): blocks.append(("p", t))
def NOTE(t): blocks.append(("note", t))
def BUL(i): blocks.append(("bul", i))
def NUM(i): blocks.append(("num", i))
def TBL(h, r, w=None): blocks.append(("tbl", h, r, w))
def KV(k, v): blocks.append(("kv", k, v))
def CODE(t): blocks.append(("code", t))
def LBL(t): blocks.append(("lbl", t))
def FIG(n, c): blocks.append(("fig", n, c))
apis = cf.info("api"); funcs = cf.info("function"); T = cf.tables; use = cf.key_usage()
byname = {x["name"]: x for x in apis + funcs}
# ================================================================== 1
H1("1. Introduction")
H2("1.1 Purpose of this Guide")
P(f"This guide is for the developers who will maintain and extend the {INSURER} insurance APIs after hand-over. It explains how the solution is built, where every piece of logic and data lives, how a request travels through the code, which platform services are called and why, which platform quirks shaped the design, how to change or add things safely, how to test, and how to deploy. The reference sections (4, 6, 11, 12 and the appendices) are generated from the real source files, tables and scripts, so they match what is deployed in the MC tenant at the time of writing. Version 1.2 adds the maker-checker workflow, the dashboard, notifications, the staff portal and an analysis of PA001 and iHub (sections 15 to 19). **Section 1.4 lists what is most likely to surprise a new developer: read it first.**")
H2("1.2 What the Solution Is")
P("A set of 18 active REST APIs (and 2 inactive ones: a retired stub and a test probe) with 13 shared functions, written as iComposer Groovy scripts on the InsureMO platform, plus a staff portal (a UIC page). They orchestrate the platform's proposal, policy, endorsement, search and print services for seven insurance products (UPPA001 Personal Accident, TL001 Term Life, FP001 Female Protection, HC001 Hospital Cash, CI001 Critical Illness, LP001 Life Protect, DH001 Domestic Helper; 11 variants, 57 plans). Partners such as Sohar Bank call the APIs; the APIs validate the request, call the platform and return a stable contract. Bank staff work in three roles (Maker, Proposal Checker, Cancellation Checker) through the portal. Everything that a business user may want to change (validation rules, product data, refund rules, texts, formats, channels, insurers, users and roles, message texts) is data in iTables, not code. The solution is developed in iComposer only: iHub is not used (section 18).")
H2("1.3 Glossary")
TBL(["Term", "Meaning"], [
    ["MC", "The current development tenant in which everything is built and tested (tenant code `uponly`, gateway portal-gw.insuremo.com). UAT is a separate tenant."],
    ["iComposer", "InsureMO's low-code Groovy runtime. An API script is exposed as a REST route; a function (common service) is a shared Groovy class called with `getCommonService`."],
    ["iTables / data table", "Tenant configuration tables read by the code (`UP_ApiConfig`, `UP_FieldRule`, ...)."],
    ["Tech product / market product", "The platform keeps a technical product (`<CODE>_TECH`, holds the data dictionary tree) and a market product (`<CODE>`) per product code."],
    ["DD / binding", "Data dictionary: the fields of the policy tree. A field must be bound to an object before the platform accepts or calculates it."],
    ["Maker", "Bank employee who creates quotations and proposals and raises cancellation requests."],
    ["Proposal Checker", "Bank employee who approves (issues) or rejects a submitted proposal."],
    ["Cancellation Checker", "Bank employee who approves or rejects a cancellation request (named Approver in v1.0 of the cancellation API)."],
    ["AgentCode", "Platform proposal field in which the maker's platform user id is stored (section 15.3)."],
    ["SNS", "The platform's notification service used to send email and SMS (section 16)."],
    ["UIC", "InsureMO UI Connector: hosts the portal as a single-page web app (section 17)."],
    ["Dry run", "Notification mode in which messages are recorded in the response but not sent."],
    ["ChannelCode", "The partner that owns a record (SOHAR = Sohar Bank); sent on every request and saved on every proposal."],
    ["OrgCode", "Issuing branch code; the platform validates it against the code table PubBranch (value 1)."],
    ["Carrier / insurer", "The insurer of a product: `CarrierCode` AFIC, name from table `UP_Carrier`."],
    ["Trace id", "Platform request id, returned as `trace_id` and used to find the log of a call."]], [20, 80])
ns.read_first(globals())
# ================================================================== 2
H1("2. Architecture")
H2("2.1 Layers")
FIG("arch2", "Figure 1: Architecture (v1.2) — channels, gateway, iComposer APIs, common functions, platform services and tables")
P("Every API follows the same pipeline. The API script is thin: it reads the body through `UPSecurity.readInput`, validates it with `UPValidator.validate` (rules in table `UP_FieldRule` plus product and cross-field rules in code), calls the platform through the SDK clients (`ProposalSdkClient`) or the REST helper (`UPPlatformClient`), shapes the answer with `UPShaper.shapeResponse` and returns it. Any exception is turned into the standard error body by `UPErrorHandler.handle`, which also sets the HTTP status. The tables are read-only from the code (the `TablesSdkClient` is read-only); they are changed with the `imo` tool by an administrator. From v1.2 the API also checks the caller's role (`UPAccess`) and the platform search index is read for queues and the dashboard (`UPWorklist`).")
H2("2.2 Design Rules")
BUL(["Everything configurable lives in tables: a missing configuration key stops the request with `UP-CONFIG` (HTTP 500, generic message, detail in the log); there is no silent default. The only exceptions are the security baselines in `UPSecurity`, which have an optional table override.",
     "PA001 (the original product, config and code) is never read or changed by this solution: product data lives in separate `UP_` tables and the new products are new platform products. A snapshot tool (`snapshot.py`) proves this before and after every change.",
     "The caller's own bearer token is used for every platform call; there is no service account. The token is only sent to hosts listed in `UP_ApiConfig.AllowedHosts` (https only).",
     "Responses are shaped for the channel: platform technical fields may be present but are not part of the contract.",
     "One error contract on every API: `status`, `code`, `message`, `errors[]`, `api`, `trace_id`. A missing role or a maker-checker breach is 403 `UP-403`.",
     "Roles come from the table `UP_UserRole` and are checked in the APIs, never in the portal alone. The portal menu is a convenience.",
     "No workflow state is kept in our own tables: proposals and cancellation requests are read from the platform (section 15)."])
H2("2.3 Request Lifecycle")
NUM(["Gateway authenticates the bearer token (HTTP 401 on failure) and routes `/up/<path>` to the iComposer API.",
     "API script: `UPSecurity.readInput(RequestBody())` — body must be a JSON object, then every string is scanned for blocked characters (400 `INVALID_BODY` / `INVALID_CHARACTER`).",
     "`UPValidator.validate(api, input)` — rules from `UP_FieldRule` for this API (required, type, length, pattern, range, enum, code table, conditional `WhenPath`), then product rules (age, term, premium mode, plan availability), CarrierCode match, beneficiary total. All problems are returned together as 400 `UP-VALIDATION`.",
     "Role check: `UPAccess.require(...)` (403 `UP-403`), then for approvals the maker-checker rule. State and ownership checks for existing records: record exists (404), belongs to the channel (`requireChannel`), product matches, proposal still open (`requireOpenProposal`, 409).",
     "Platform call(s): `ProposalSdkClient` (application, load, save, persistCalculate, issue, queryPolicy) or `UPPlatformClient` (endorsement REST) or the print service.",
     "`UPShaper.shapeResponse`: commission switch, premium fields, payment info restored, CarrierCode / CarrierName added. Then, where the action triggers one, `UPNotify.fire` adds `Notifications[]`.",
     "Return the map (HTTP 200) or, on any exception, `UPErrorHandler.handle(apiName, ex)`."])
# ================================================================== 3
H1("3. Source Layout and Tooling")
H2("3.1 Workspace Layout")
CODE("ic/\n  src/dev/Tenant/UP_PRODUCTS_API/\n    api/<Name>/<Name>.groovy         20 API scripts (18 active; UPCancelPolicy is a retired stub and UPSpikeWho a probe, both inactive)\n    function/<Name>/<Name>.groovy    13 common functions\n  .metadata/icomposer/{api,function}/<Name>.metadata.json   per-profile server metadata (ids, version, md5, path, method)\nuponly-build/                        build, test and report tooling (section 11)\n  tables/                            the rows written to the UP_ tables (r_*.json), definitions (def_*.json), local copies (rows_*.json)\n  samples/                           recorded request / response of every flow step\n  tests/ security/ carrier/ workflow/ test cases and results\nuic_pages/uponly/portal/sohar-insurance-portal/   the portal (index.html, metadata.json, prompt.md) in the git repository\ndeliverables/workflow_src/           v1.2 iComposer source, set-up and test scripts (git copy)")
P("Module id 70, group id 1188491119; functions have scope `public` and status 1. APIs are POST except `UPLoadPolicy` and `UPMe` (GET). All paths are `/up/<name>`: get-plans, proposal, update-proposal, issue, load-policy, proposal-reject, doc_generation, application_doc_generation, cancel-check, cancel-approve, list-master-table, commission-query, generate-feedfile, and since v1.2 me, worklist (`UPWorklistApi`), dashboard, share, cancel-detail (the inactive ones are cancel-policy and spike-who).")
H2("3.2 The imo Tool")
TBL(["Task", "Command (profile `portal:uponly` = MC)"], [
    ["Push one file (compiles on the server first)", "`imo icomposer push current <file> --profile portal:uponly`"], ["Preview a push", "`... push current <file> --dry-run`"],
    ["Create a function / API", "`imo icomposer create function --name X --module-id 70 --group-id 1188491119 --status 1 --func-scope 1 --profile portal:uponly`"],
    ["Pull the server copy", "`imo icomposer reload ...`; on a conflict choose `--prefer-local` or `--prefer-server`"], ["Read a table / rows", "`imo config datatable by-name --name UP_ApiConfig --json`, `... record-list --id <tableId> --json`"],
    ["Add rows", "`imo config datatable record-batch-save --file rows.json --confirm` (insert only; the primary key `Id` must be unique)"], ["Change one row", "`imo config datatable record-save --file row.json --confirm` (include `RecordId`)"],
    ["Create a table", "`imo config datatable create --file def.json --confirm`"], ["Find a call in the log", "`imo log query` with the trace id from the response (section 9)"]], [32, 68])
H2("3.3 Groovy Rules of This Runtime")
BUL(["The server type-checks Groovy statically on push. `@groovy.transform.Field` is not allowed and script-level variables are not visible inside methods: use a method that returns the constant (see `UPSecurity.blockedBaseline()`).",
     "`log` is not declared: use `org.slf4j.LoggerFactory.getLogger(\"Name\")` (see `UPErrorHandler`).",
     "Shared per-request state goes into the request attributes (`RequestContextHolder`), as the table cache in `UPDataUtil.getRecords` does.",
     "A function that calls another one declares it with `(UPOther) getCommonService(\"UPOther\")`; push the called function first when it is new.",
     "The platform REST client raises its own exception type; `UPPlatformClient` catches it and returns `{status, body}` so that callers decide.",
     "`UPShaper.shapeResponse` returns `Object`: cast it (`(Map<String, Object>) shaper.shapeResponse(r)`) before adding fields. The SNS email and SMS builders take `requestBody(...)`; an anonymous `Comparator` must not use method variables; the accessor of a hyphenated SDK tag is camel case (`emailAccountApi()`).",
     "Empty lists are dropped from the JSON that the platform returns (for example `Roles` in `/up/me`): treat a missing list as empty.",
     "Keep each function focused; the largest file is `UPValidator`."])
H2("3.4 Deployment Order of the Code")
P("Dependencies run from the bottom up. Push in this order (the same order is used for UAT): UPDataUtil, UPSecurity, UPErrorHandler, UPPlatformClient, UPValidator, UPProductData, UPShaper, UPDocBuilder, UPDocService, UPAccess, UPNotify, UPWorklist, UPCancelService, then the 18 active APIs. The tables `UP_UserRole` and `UP_NotifyTemplate` and the new configuration keys must exist before the new code runs. Pushing a caller before a new callee fails the compile check.")
# ================================================================== 4
H1("4. Code Reference")
H2("4.1 Asset Inventory")
rows = []
for a in apis: rows.append([a["name"], "API", f"{a['method'] or ''} {a['path'] or ''}", "inactive" if a["status"] == 0 else "active", str(a["lines"]), str(a["version"]), ", ".join(a["deps"])])
for f in funcs: rows.append([f["name"], "Function", "-", "active", str(f["lines"]), str(f["version"]), ", ".join(f["deps"])])
TBL(["Name", "Kind", "Route", "Status", "Lines", "Server version", "Calls (common functions)"], rows, [18, 8, 20, 8, 7, 8, 31])
P(f"Total: {sum(x['lines'] for x in apis + funcs)} lines of Groovy ({sum(x['lines'] for x in apis)} in APIs, {sum(x['lines'] for x in funcs)} in functions).")
H2("4.2 Common Functions")
for f in funcs:
    LBL(f"{f['name']}  ({f['lines']} lines)")
    P(f["header"])
    extra = []
    if f["tables"]: extra.append("tables read: " + ", ".join(f["tables"]))
    if f["sdks"]: extra.append("SDK: " + ", ".join(f["sdks"]))
    if f["keys"]: extra.append("config keys used: " + ", ".join(f["keys"]))
    if f["deps"]: extra.append("calls: " + ", ".join(f["deps"]))
    if extra: NOTE(" | ".join(extra))
    TBL(["Method", "Parameters", "Returns", "Purpose"], [[m["name"], m["params"], m["ret"], m["doc"]] for m in f["methods"]], [22, 30, 16, 32])
H2("4.3 APIs")
for a in apis:
    LBL(f"{a['name']}  —  {a['method'] or ''} {a['path'] or ''}  ({a['lines']} lines)")
    P(a["header"] or ("Inactive probe API from the identity and SNS spike; delete it before UAT (section 19.4)." if a["name"] == "UPSpikeWho" else "Retired stub (the cancellation is done by cancel-check / cancel-approve)."))
    ex = []
    if a["deps"]: ex.append("calls: " + ", ".join(a["deps"]))
    if a["sdks"]: ex.append("SDK: " + ", ".join(a["sdks"]))
    if a["tables"]: ex.append("tables: " + ", ".join(a["tables"]))
    if a["keys"]: ex.append("config keys: " + ", ".join(a["keys"]))
    if ex: NOTE(" | ".join(ex))
# ================================================================== 5
H1("5. API Walkthroughs")
P("What each API does in code, in the order it does it. Names in backticks are functions or methods listed in section 4.")
ns_walk = [
 ("v1.2 changes to existing APIs", "UPProposal: `UPAccess.require(Maker)`, `prepareProposal`, then `AgentCode` = caller id, create, shape, `UPNotify.fire(\"SUBMITTED\")`, `Notifications[]` added. UPUpdateProposal: Maker and creator only (`requireCreator`), keeps the stored AgentCode. UPIssue: Proposal Checker, `requireNotCreator(existing.AgentCode)`, after the issue `PROPOSAL_ISSUED` to the maker and the customer (contact from the raw loaded proposal). UPProposalReject: Proposal Checker, not the creator, `ProposalRejectDesc` is required by a field rule, `PROPOSAL_REJECTED` to the maker. UPCancelCheck: Maker; a new request sends `CANCEL_REQUESTED`. UPCancelApprove: Cancellation Checker; `UPCancelService.decide` compares the requester (`DataEntryUserId` of the pending endorsement) with the caller and sends `CANCEL_APPROVED` / `CANCEL_REJECTED`. UPGetPlans, UPLoadPolicy, UPDocGeneration, UPApplicationDocGeneration and UPCommissionQuery call `requireAny()`."),
 ("UPMe", "`UPAccess.me()`; no validation, no role needed."),
 ("UPWorklistApi", "Validates (`UP_FieldRule` rows for api name `UPWorklist`), role by Type, then `UPWorklist.proposalList` (PROPOSAL, MINE) or `cancellationList`. Section 15.4."),
 ("UPDashboard", "Validates, `requireAny()`, forces own figures for a maker-only caller, checks the window, then `UPWorklist.summary` or `commissionSection`. Section 15.5."),
 ("UPShare", "Validates, `requireAny()`, builds the placeholders (quotation: from `Details`; proposal / policy: loaded and channel-checked), takes the contact from the request or the stored record and calls `UPNotify.fire(event, ..., onlyChannel)`. Section 16."),
 ("UPCancelDetail", "Validates, Maker or Cancellation Checker, `UPCancelService.detail`: resolves the policy, finds the pending endorsement (signed policy id), recalculates the refund, returns requester, reason and `CanDecide`; creates nothing; 404 when no request is pending.")]
W = [
 ("UPGetPlans", "Validates the body (`validator.validate(\"UPGetPlans\")`: product, variant, premium mode, term, age from DateOfBirth). Reads the variant (`UPProductData.getVariant`) and rule (`getRule`) and builds the `PlanList` directly from the tables: `getPlanRows` (`UP_ProductPlanRelation`: plan id, name, premium, commission) and `getBenefitRows` (`UP_PlanBenefitRelation`: code, description, sum insured) — no platform call. The premium shown here is therefore the table premium; the proposal premium is calculated by the platform rating `<CODE>_PREM_CALC` from the same tables, so the two stay equal as long as the data is consistent. Defaults of the policy skeleton (status, zero premium fields, flags, customer flags) come from `UP_ApiConfig` (`PolicyStatusEffective`, `ZeroPremiumFields`, `CustomerFlagNo`, ...). Like PA001, it first runs the platform's own quotation validation (`QuotationSdkClient.quotationApi().newValidateRequestBuilder()`, empty event code and language, a copy of the request) when `UP_ApiConfig.GetPlansPlatformValidate` = Y (MC: Y); the result is not used, a rejection stops the request (HTTP 400, code `UP-PLATFORM-VALIDATION` for policy validation errors such as a code value outside its code table, or the platform's own 400). The plans themselves are still built without a platform call. It does not use `shapeResponse`, so `CarrierCode` / `CarrierName` are added with `products.addCarrier` before the return."),
 ("UPProposal", "Rejects `ProposalNo` (409-style 400), validates, then `UPProductData.prepareProposal`: drops client `PlanList` and `DuePremium` (the platform rating builds plan, covers, premium and commission), removes server-owned fields and defaults `OrgCode` (`UPSecurity`), flattens `PolicyPaymentInfoList` into `Payment*` policy fields (the platform instalment rating would otherwise re-round the premium) and returns the payload. The API then calls `proposalApi().newApplicationRequestBuilder()` and returns `shaper.shapeResponse`, which rebuilds the payment structure, applies the commission switch and adds the insurer."),
 ("UPUpdateProposal", "Same preparation as create. Loads the stored proposal by `ProposalNo` (404), checks channel, product match and that it is open (409), copies `PolicyId`, `PolicyElementId` and `VersionSeq` of the stored record into the payload, calls `newSaveRequestBuilder()` and then `newPersistCalculateRequestBuilder()` because the save drops the calculated plan row."),
 ("UPIssue", "Loads the proposal (404), checks channel, product match (`MISMATCH`) and open state (409). When the optional request field `Recalculate` = Y it first runs persistCalculate on the stored proposal (not part of the public specification). Then `newIssuePolicyRequestBuilder` issues it and the shaped policy with the new `PolicyNo` is returned."),
 ("UPLoadPolicy", "GET. Exactly one of `policyNo` / `proposalNo` (400); loads with code descriptions (`withCodeDesc`), 404 when missing, `requireChannel`, `shapeResponse`."),
 ("UPProposalReject", "Loads the proposal (404), checks channel and open state (409), calls `newRejectRequestBuilder` with a `RejectVo` (proposal number and reason) and returns `{status: SUCCESS (SuccessStatusText), message: <the reason>}`."),
 ("UPDocGeneration / UPApplicationDocGeneration", "Thin wrappers over `UPDocService.generate`: resolve the template name from `UP_DocTemplate` (product, sub-product, DocType), build the print data with `UPDocBuilder` (wording from `UP_DocWording`, benefit names from `UP_BenefitText`, formats from `UP_ApiConfig`), call the print service at `PrintUrl` (host checked against `AllowedHosts`) with the caller's token and return the PDF (or the print data when `PreviewData` = Y)."),
 ("UPCancelCheck / UPCancelApprove", "See section 8 for the complete sequence: `UPCancelService.check` and `decide`."),
 ("UPListMasterTable", "Allows only tables listed in `UP_ApiConfig.MasterTables`; returns all records or the one with `Id` (commission column removed)."),
 ("UPCommissionQuery", "Three modes: by `PolicyNo` (`UPDocBuilder.commissionOfPolicy`), by product configuration (rows of `UP_ProductPlanRelation` with premium, commission and rate), or for a period (search on the platform, load each policy, keep only the caller's channel, page totals). Page size is capped by `CommissionMaxPageSize`."),
 ("UPFeedFile", "Searches policies with the platform query API (period, product, paging), loads each hit, keeps the caller's channel, shapes it and writes the columns defined in `UP_FeedColumn` (heading + source path, alternatives separated by `|`) to an Excel sheet or to JSON. Capped by `FeedMaxRecords` / `FeedMaxPages` (400 `RANGE_TOO_LARGE`).")]
W = ns_walk + W
TBL(["API", "Flow in code"], [[a, b] for a, b in W], [20, 80])
# ================================================================== 6
H1("6. Data and Configuration Reference")
H2("6.1 Tables")
PURP = {"UP_ApiConfig": ("Key / value configuration of the code (Api, Scope, Key, Value). `configMap(scope)` merges `*` rows with product-specific rows.", "UPDataUtil.cfg / cfgValue, every function"),
        "UP_FieldRule": ("Validation rules per API and field path: Required, DataType, MinLength, MaxLength, Pattern, MinValue, MaxValue, EnumValues, CodeTable + CodeColumn, WhenPath + WhenValue (conditional), AppliesTo.", "UPValidator.validate"),
        "UP_ProductMaster": ("Product variants (IMOProductCode, CarrierProductCode = sub-product, name, LOB, CarrierCode, IsActive).", "UPProductData.getVariant, carrierOf"),
        "UP_ProductPlanRelation": ("Plans per variant with premium, commission, premium mode.", "UPProductData, UPGetPlans, commission configuration view"),
        "UP_PlanBenefitRelation": ("Covers and sums insured per plan.", "UPProductData, UPGetPlans, documents"),
        "UP_ProductRule": ("Per variant: MinAge, MaxAge, MaxEntryAge, MaxExitAge, MinTerm, MaxTerm, PremiumModes, FreeLookDays, ProRataRefundPercent, mandatory documents.", "UPValidator.entryErrors, UPCancelService.refundCalc"),
        "UP_DocTemplate": ("Output template name per product, sub-product and document type.", "UPDocService"), "UP_DocWording": ("Wording for premium modes and benefit limit bases (`BASIS:*`), English / Arabic.", "UPDocBuilder"),
        "UP_BenefitText": ("Official English / Arabic benefit names per product.", "UPDocBuilder"), "UP_FeedColumn": ("Columns of the policy feed file (Sequence, Heading, Source).", "UPFeedFile"),
        "UP_Channel": ("Registered channels (ChannelCode, Description, IsActive).", "UPValidator (ChannelCode rule)"), "UP_Carrier": ("Insurers (CarrierCode, CarrierName, IsActive); linked from UP_ProductMaster.CarrierCode.", "UPProductData.carrierOf"),
        "UP_UserRole": ("Staff roles: UserRoleKey (user|ROLE), UserName, UserId (platform id), Role (MAKER / PROPOSAL_CHECKER / CANCELLATION_CHECKER), DisplayName, Branch, Email, Mobile, IsActive. Never exposed through master data.", "UPAccess"),
        "UP_NotifyTemplate": ("Email / SMS texts per event, recipient and channel (TemplateKey, Event, Recipient, Channel, Subject, Body, SmsTemplateCode, IsActive).", "UPNotify")}
rows = []
for n, d in T.items():
    cols = ", ".join(f[0] for f in d["fields"] if f[0] not in ("Id",))
    rows.append([n, str(d["id"]), str(d["rows"]), cols, PURP[n][0], PURP[n][1]])
TBL(["Table", "Table id (MC)", "Rows", "Columns", "Purpose", "Read by"], rows, [12, 9, 5, 22, 32, 20])
P("The code maps a few logical names to the `UP_` tables (`UPDataUtil.readRecords`): ProductMaster, ProductPlanRelation, UP_PlanBenefitRelation, ProductRule and DocTemplate. Tables are read once per request and cached in the request attributes, so a changed row is visible on the next request without any deployment.")
H2("6.2 Configuration Keys (UP_ApiConfig)")
P("Every key with its current MC value and the functions that read it. Environment specific keys are marked in section 13.")
rows = []
for r in sorted(T["UP_ApiConfig"]["records"], key=lambda x: x["Key"]):
    v = str(r["Value"]); v = v if len(v) < 70 else v[:67] + "..."
    rows.append([r["Key"], v, ", ".join(use.get(r["Key"], [])) or "(read through a pattern or documented only)"])
TBL(["Key", "Value (MC)", "Used in"], rows, [24, 36, 40])
H2("6.3 Field Rules (UP_FieldRule)")
rules = T["UP_FieldRule"]["records"]; per = {}
for r in rules: per[r["Api"]] = per.get(r["Api"], 0) + 1
TBL(["API", "Rules"], [[a, str(n)] for a, n in sorted(per.items())], [60, 40])
P("A rule row is evaluated by `UPValidator.validate`: `Path` uses indexes (`PolicyLobList[0].PolicyRiskList[0].InsuredName`); `Required` Y/N; `DataType` string / integer / decimal / date / enum; `Pattern` is a regular expression (length and input size are capped by `PatternMaxLength` / `PatternMaxInput`); `CodeTable` + `CodeColumn` check the value against a table (`UP_Channel`, `UP_Carrier`, `BranchCode`, ...); `WhenPath` + `WhenValue` make the rule conditional (for example PolicyNo is required when DocType = Policy); `AppliesTo` limits a rule to a product. Changing a rule is a row change and needs no deployment.")
H2("6.4 Security Baselines (UPSecurity)")
TBL(["Control", "Baseline in code", "Optional override key in UP_ApiConfig"], [
    ["Blocked characters in any text value", "control characters and `< > $ { } ` \\ | ^ ~ ;`", "BlockedCharacters"], ["Free-text fields", "InsuredName, Address, BeneficaryName, CancelReason, OtherCancelReason, ProposalRejectDesc", "FreeTextFields"],
    ["Free-text allow-list", "letters of any script, digits, space and `. , ' - / @ + ( )`", "FreeTextPattern"], ["Server-owned fields removed from a proposal", "PolicyNo, PolicyId, PolicyElementId, ProposalStatus, PolicyStatus, AgentCode (v1.2: the maker stamp)", "ServerOwnedFields"],
    ["Default OrgCode", "1", "OrgCode"]], [30, 44, 26])
NOTE("These are the only values that have a built-in default; a missing override key never fails a request. Moving them fully into tables (and treating a missing key as UP-CONFIG) is on the backlog.")
# ================================================================== 7
H1("7. Platform Configuration (Products)")
H2("7.1 What Exists on the Platform")
P("For each of the seven product codes the platform holds a tech product `<CODE>_TECH` and a market product `<CODE>` (ids in the deployment plan), the policy data dictionary tree (Policy, PolicyLob, PolicyRisk R00001, Plan, PolicyCoverage, Beneficiary), a premium rating definition `<CODE>_PREM_CALC` bound to the market product, the plan and cover data in the `UP_` tables, and the output templates named in `UP_DocTemplate` (22 rows).")
H2("7.2 Data Dictionary Bindings")
P("The new products bind only the fields the flows need (24 policy-level, 17 tech-level, 8 risk-level, 4 plan, 6 coverage, 4 beneficiary fields) at product level (RecordUsage 5). PA001 binds far more (408 policy-level fields). The cancellation endorsement rating additionally reads delta fields; `fix_endo_fields.py` bound the ones the platform reported as missing (`StandardGrossPremiumDelta`, `AnnualPremiumDelta`, `ShortRate` on the risk and coverage objects) on the new tech products only. The script never creates `VAT` (there is no VAT in this solution) and refuses to touch any context that is not one of the seven tech products.")
H2("7.3 How the Products Were Built")
TBL(["Step", "Tool"], [["Tech and market products, tree, DD fields, code tables", "`build_product.py <spec.json> <step>` with `spec_<CODE>.json`"], ["Rating definition per product", "`rating_build.py <CODE> --confirm` (copy of PA001_PREM_CALC bound to the market product), patched by `patch_rating.py` / `patch_rating2.py`"],
    ["Tables and rows", "`make_tables.py`, `data_rows.py`, `uptab.py` (create table, save rows), `make_rules.py` (field rules), `stage_*_rows.py` (config keys)"], ["Output templates", "`make_templates2.py` builds the bilingual HTML templates from the form designs; `gen_all_tpl.py` / `os_gen.py` upload and test them"],
    ["Cancellation fields", "`fix_endo_fields.py`, `bind_cancel_field.py` (optional IsAdminChange, not used)"], ["PA001 guard", "`snapshot.py before|after`"]], [40, 60])
# ================================================================== 8
H1("8. Business Algorithms")
H2("8.1 Premium Mode, Term and Age")
P("`UPValidator.entryErrors` reads the variant's `UP_ProductRule` row: the premium mode must be in `PremiumModes`; single premium (`SinglePremiumModeCode`) needs a term between MinTerm and MaxTerm, other modes need `NonSingleTermYears` (1); the age at the effective date must be within MinAge / MaxAge and MaxEntryAge, and age + term within MaxExitAge. `PremiumModeCode` is mandatory where the plans of a variant differ by mode (`UPPA001`, `TL001`, `CI001`, `LP001`). Premium and commission are never taken from the request: the platform rating calculates them from the plan tables.")
H2("8.2 Cancellation (Checker / Approver)")
FIG("cancel", "Figure 2: Cancellation — Checker and Approver sequence in UPCancelService")
P("The request is the platform's own pending cancellation endorsement; its number is the `RequestNo`. From v1.2 the Checker step is the **Maker** role and the Approver step the **Cancellation Checker** role (the code and routes are unchanged); the requester cannot decide their own request; `cancel-detail` shows a pending request without creating one; and the steps send alerts (section 16).")
LBL("Checker — UPCancelService.check")
NUM(["`resolvePolicy`: by PolicyNo or ProposalNo (a proposal must be issued: 409), `requireChannel`, the product must be enabled (`UP_ProductMaster`).", "Policy must be in force (status `PolicyStatusInforce`); a cancelled policy is 409.",
     "`pendingCancellation`: queries the pending endorsement with the **signed policy id** (`id,signature`) returned by the platform's own load (`ProposalLoadPath`), sent once-encoded. Another kind of pending endorsement blocks the request (409). An existing cancellation request is shown again with the date it was created with.",
     "`refundCalc(policy, date)`: free look when elapsed days <= `FreeLookDays` (refund 100%), otherwise premium x unexpired days / policy days x `ProRataRefundPercent` (rounded `MoneyScale`, `RoundingMode`).",
     "`createRequest`: `POST EndoBasePath/createEx` with EndoType 3, CancelType 31 (free look) or 32 (pro-rata), reason, payment info; for free look the effective date is the policy start.", "Response: RequestNo, RequestStatus PENDING, PolicyInfo (with insurer), PolicyStatus, PremiumDetails, RefundDetails."])
LBL("Approver — UPCancelService.decide")
NUM(["Same lookup; `RequestNo` must be the pending endorsement (404 otherwise, also on a second approval).", "REJECT: `suspendEndorsement`, answer REJECTED.",
     "APPROVE: suspend the saved (thin) request, create a **fresh** endorsement with the same terms (`createEx`), then `calculateEx`, `validate`, `issueEndorsement`. The saved request is replaced because `calculateEx` needs the full NewPolicy, which only `createEx` returns.",
     "If the platform refuses a step the exception text is capped (`PlatformErrorMaxLength`) and returned as 409 `The platform refused the cancellation of <policy>; the request is still pending as <EndoNo>`.", "Success: status 3, `RefundPremium` (same calculation as the Checker), `EndorsementNo`, RequestStatus APPROVED."])
H2("8.3 Platform Quirks That Shaped the Code")
TBL(["Quirk", "Effect / handling"], [
    ["Endorsement service needs the signed policy id (`id,signature`) and rejects a double-encoded id", "Signed id taken from the platform load and sent once-encoded in `pendingCancellation`."],
    ["`calculateEx` needs the full NewPolicy; a saved pending endorsement is thin", "On APPROVE the saved request is suspended and a fresh `createEx` is used."],
    ["The platform REST client throws its own business exception", "`UPPlatformClient` returns `{status, body}`; the approver answers 409 instead of 500."],
    ["A policy created without OrgCode gets -1; `validate` of the endorsement checks OrgCode against code table PubBranch (only value 1)", "`UPSecurity.defaultOrgCode` sets 1 when it is missing; callers send OrgCode 1."],
    ["A policy status sent by the caller made the platform fail (500 / 502); a caller policy number was accepted", "`UPSecurity.stripServerOwned` removes PolicyNo, PolicyId, PolicyElementId, ProposalStatus, PolicyStatus."],
    ["The cancellation rating reads delta fields that were not bound on the new products", "`fix_endo_fields.py` bound them on the seven tech products (section 7.2)."],
    ["The platform save drops the calculated plan row", "`UPUpdateProposal` calls persistCalculate after save."],
    ["Platform instalment rating re-rounds the premium", "Payment info is flattened to `Payment*` fields and rebuilt in `UPShaper.restorePayment`."],
    ["Responses contain a `TempData` block with masked / encrypted copies of ID and mobile", "Not part of the contract; flagged for review (section 14)."],
    ["Wrong HTTP method returns 422 from the gateway, not from the code", "Documented in the specification."]], [48, 52])
# ================================================================== 9
H1("9. Errors, Logging and Tracing")
TBL(["Situation", "Exception thrown in code", "HTTP / code"], [
    ["Validation problems", "`IllegalArgumentException(\"VALIDATION:\" + json)` via `util.throwValidation`", "400 `UP-VALIDATION` with `errors[]`"], ["Simple bad request", "`util.fail(msg)` -> `IllegalArgumentException`", "400 `UP-400`"],
    ["State conflict", "`IllegalArgumentException(\"CONFLICT:...\")`", "409 `UP-409`"], ["Bad number", "`NumberFormatException`", "400 `UP-400`, text `MsgInvalidNumber`"], ["Missing configuration / table row", "`IllegalStateException`", "500 `UP-CONFIG`, text `MsgConfigError`; detail in the log"],
    ["Platform business error", "`ApiException` (message sanitised by `isInternalText`)", "status of the platform, its code; internal text replaced by `MsgServerError`"], ["Missing role / maker-checker breach", "`IllegalArgumentException(\"FORBIDDEN:...\")` from `UPAccess`", "403 `UP-403`, texts `MsgForbidden`, `MsgSelfApproval`, `MsgNotOwner`"], ["Platform policy validation rejected the request (a `MultipleBusinessException` whose text starts \"Policy Validation Error\")", "handled in `UPErrorHandler.handle` by class name", "400 `UP-PLATFORM-VALIDATION`, message = the platform text"], ["Not found", "`errorHandler.notFound(api, msg)`", "404 `UP-404`"], ["Anything else", "`Exception`", "500 `UP-500`, generic text; full exception logged with the trace id"]], [24, 44, 32])
P("Tracing: every error body carries `trace_id`. Find the call in the platform log with `imo log query` using that trace id (application logs of the iComposer runtime); `UP-CONFIG` messages name the missing key only in the log. Do not add `println` or secrets to the code; use the slf4j logger.")
# ================================================================== 10
H1("10. How-To Recipes")
rec = [
 ("Add or change a validation rule", ["Read the rows of `UP_FieldRule` (`imo config datatable record-list --id 1188575333`).", "Add a row (`record-batch-save`, a new unique Id) or change one (`record-save` with its RecordId): Api, Path, Label, Required, DataType, limits, Pattern, CodeTable.", "Test the API with a valid and an invalid value; no deployment is needed.", "Update the specification (`api_spec_data.py` reads the rules) and the policy model."]),
 ("Rule that needs code (cross-field, product rule)", ["Edit `UPValidator.entryErrors` / `validate` (keep one `util.fieldError(path, code, message)` per problem).", "Push `UPValidator`; push nothing else unless a signature changed.", "Add a test case (`run_tests.py`, business cases) and a line in the specification."]),
 ("Change free look days or refund percent", ["Edit `FreeLookDays` / `ProRataRefundPercent` of the variant row in `UP_ProductRule` (`record-save`).", "Check with `cancel-check` on a test policy; update the specification section 6.2 if the value differs from the documented 15 / 80."]),
 ("Add a plan or change a premium", ["Add or change rows in `UP_ProductPlanRelation` and `UP_PlanBenefitRelation`; add the plan id to the `Plan` code table if it is new.", "Run Get Plans and Create Proposal for the plan and compare the premium with the table (the rating reads the tables)."]),
 ("Add a product variant (sub-product)", ["Add `UP_ProductMaster`, `UP_ProductRule`, plan and cover rows, `UP_DocTemplate` rows and the output templates (`make_templates2.py`).", "Add test samples (`samples/req/<TAG>_proposal.json`) so `ref_flow.py` can run the variant."]),
 ("Add a new product code", ["Create the tech and market product, the DD tree and bindings and the rating definition with `build_product.py` and `rating_build.py` (section 7.3).", "Bind the cancellation delta fields with `fix_endo_fields.py <TAG>`.", "Add the table rows as for a variant; add the code to the product lists of the tooling (`products.json`, test scripts)."]),
 ("Add a channel", ["Add a row to `UP_Channel` (ChannelCode, Description, IsActive Y). The `ChannelCode` rule checks the value against this table."]),
 ("Add or change the insurer", ["Add a row to `UP_Carrier`; set `UP_ProductMaster.CarrierCode` of the variants to it. Responses show the name from the table; a product whose carrier row is missing or inactive returns `UP-CONFIG`."]),
 ("Add a master (code) table to Master Data", ["Append the table name to the value of `UP_ApiConfig.MasterTables` (`record-save` of the row with its RecordId)."]),
 ("Add a field to a response", ["Policy-level: set it in `UPShaper.shapeResponse` (or the API for Get Plans, which does not use the shaper). Cancellation: `UPCancelService.policyInfo` and the `out` maps. Commission: `UPDocBuilder.commissionOfPolicy`. Feed: add a `UP_FeedColumn` row.", "Add the field to the specification (`api_spec_data.py` reads recorded responses: re-run `ref_flow.py` for one plan per product)."]),
 ("Add a new API", ["`imo icomposer create api ...` (path `/up/<name>`), copy the pattern of a small API (readInput, validate, call, shape, errorHandler).", "Add `UP_FieldRule` rows for the new API name, push, add cases to `run_tests.py` and `security_probe.py`, document in the specification."]),
 ("Change a message text or format", ["Edit the `UP_ApiConfig` value (`MsgServerError`, `MsgConfigError`, `MsgInvalidNumber`, `DateFormatDoc`, `MoneyFormat`, ...)."]),
 ("Move to another environment", ["Change `AllowedHosts`, `GatewayUrl`, `PrintUrl` (section 13) and re-check the ids listed in the deployment plan."])]
rec += [
 ("Add a user or change a role", ["Section 19.2: rows in `UP_UserRole` (`record-batch-save` / `record-save`); no deployment."]),
 ("Change a message text or add an event", ["Edit the `Subject` / `Body` of the row in `UP_NotifyTemplate` (`record-save`). For a new event add rows (TemplateKey = Event|Recipient|Channel) and call `notify.fire(\"EVENT\", notify.paramsOf(policy, extra), customer, makerUserId, \"\")` from the API; add the placeholders to `paramsOf` if needed."]),
 ("Send real email / SMS", ["Section 16.5."]),
 ("Add a menu item or screen to the portal", ["Add a `<section class=\"view\" id=\"v_x\">` and an entry in `NAV` (roles list or null for all); load its data in `go()`; call the API through `api()`; add a browser check to `flow2.js`; push with `imo uic page push`."]),
 ("Add a column to a queue", ["Add the field to `UPWorklist.policyRow`, push `UPWorklist`, then add a column object to `colsProposal` / `colsCancel` in the portal."]),
 ("Turn role enforcement on or off, or allow self approval", ["`python3 setcfg.py RoleEnforcement Y|N` and `AllowSelfApproval Y|N` (section 19.1)."]),
 ("Apply the Sohar brand", ["Edit the variables in the first `:root` block of `index.html` (colours, font) and the text badge; push the page."])]
for t, steps in rec: LBL(t); NUM(steps)
# ================================================================== 11
H1("11. Test Tooling")
P("All scripts live in `uponly-build` and read the token and gateway from `env.sh` (`source env.sh` sets `B`, `GW`, `TOK`; the token is fetched with `imo auth prepare --profile portal:uponly`). Never commit tokens.")
GUIDE = {"run_tests.py": "Generates and runs the API test suite (1,085 cases: field validation, business rules, state transitions, cancellation incl. refund checks per product, master data, feed file, robustness). Results in `tests/results/` and `tests/results.json`.",
         "ref_flow.py": "Runs the 13-step flow (get plans ... cancel approve, load cancelled policy) for every plan of a variant; `ONLY_PLAN=1` limits it to one plan; output in `samples/ref/<TAG>_P<plan>/`.",
         "security_probe.py": "Live security probe (token tampering, channel isolation, injection, tampering, resource abuse, headers, errors, request hygiene); output `security/results.json`.",
         "carrier_check.py": "One flow per product (first plan): CarrierCode / CarrierName in every API, wrong CarrierCode, master data and feed file; output `carrier/results.json`.",
         "snapshot.py": "Read-only snapshot of PA001 related objects; compare `before` and `after` to prove PA001 is unchanged.",
         "role_check.py": "v1.2: 35 live checks of roles, maker-checker rule, queues, cancellation detail, notifications (dry run), share, dashboard; switches `UP_UserRole` rows and `AllowSelfApproval` during the run and restores them.",
         "workflow_setup.py": "v1.2 set-up: creates `UP_UserRole`, `UP_NotifyTemplate` and the first configuration keys / field rules (`workflow_setup2..5.py` add the later keys and rules).",
         "setcfg.py": "Changes `UP_ApiConfig` values with `record-save` and prints the old value.",
         "refresh_devdata.py": "Rebuilds `devdata/assets.json` and `devdata/tables.json` offline for this guide."}
rows = [[n, GUIDE.get(n, d)] for n, d in cf.tool_docs() if n in GUIDE]
TBL(["Script", "What it does"], rows, [22, 78])
P("Collections: `make_sohar_collection.py` (single Sohar Bank collection, one flow per product), `make_plan_collections.py` (one collection per plan with recorded failure examples), `make_cases_by_product.py`. Reports: `gen_report.py`, `make_excel.py`. Documents: `build_policy_model.py` (workbook), `spec_content.py` + `render_spec.py` / `render_docx.py` (specification), `dev_content12.py` + `dev12_sections.py` (this guide; the v1.1 generator is `dev_content.py`). Browser tests of the portal (`flow2.js`, `login.js`, `run.js`, Playwright) are described in section 17.6.")
LBL("All scripts in the build folder")
TBL(["Script", "Purpose (first docstring line)"], [[n, d[:150]] for n, d in cf.tool_docs()], [26, 74])
# ================================================================== 12
H1("12. Test Procedure for a Change")
NUM(["Before: `snapshot.py before` (PA001 guard) and copy `ic` to a backup folder.", "Make the change; push with `imo icomposer push current` (the compile check must say `Compiled: yes`).",
     "Run the affected cases (`run_tests.py all <filter>`) and, for response changes, `ref_flow.py` for one plan per product and `carrier_check.py`.",
     "For anything touching input handling or errors run `security_probe.py`.", "After: `snapshot.py after` and compare with `before` (PA001 and PA001_TECH hashes identical).",
     "Update the documents (specification, policy model, this guide) and the collection (`make_sohar_collection.py`), then run the collection in Newman.", "Rollback: push the saved files back; for tables restore the saved row."])
# ================================================================== 13
H1("13. Environments and Deployment")
P("The complete inventory, ordered steps, verification and rollback for deploying to UAT are in the separate document *Afillar API UAT Deployment Plan*. In short: 13 functions and 18 APIs (v1.2), 14 `UP_` tables with their rows (v1.2 added `UP_UserRole` and `UP_NotifyTemplate`), the product configuration on the platform, the output templates and the environment settings. The keys that differ per environment are `AllowedHosts`, `GatewayUrl` and `PrintUrl`; the ids of products, data tables and templates are tenant specific and must be re-resolved, not copied. **The UAT plan was written for v1.1: for v1.2 also deploy the portal page, the two new tables, the new keys and rules, set up users and roles, and the SNS accounts (section 19).**")
# ================================================================== 14
H1("14. Known Limitations and Backlog")
TBL(["Item", "Description", "Suggested action"], [
    ["Role / branch access", "Any authenticated user of a channel can call any API; the ChannelCode check isolates channels only.", "Access table per API and role (deferred by decision)."],
    ["Security baselines in code", "UPSecurity constants with optional override keys.", "Add the override keys / UP_FieldRule patterns and make a missing key UP-CONFIG."],
    ["Gateway findings", "Wildcard CORS, no rate limiting, OPTIONS 500, attack-like query strings hold the connection.", "Platform team."],
    ["ID number and TempData in responses", "The ID number is returned in clear and a `TempData` block with encrypted copies is part of the platform body.", "Decide on masking; strip `TempData` in `UPShaper`."],
    ["Idempotency and audit", "No idempotency key; no audit record of who approved a cancellation beyond the platform endorsement.", "Idempotency key on create / approve; audit table."],
    ["Unit tests", "Only black-box API tests exist.", "Data-driven tests for pure functions (refundCalc, entryErrors, scan)."],
    ["Per-plan collections", "52 per-plan collections were not regenerated after the insurer fields were added (still valid; examples lack the two fields).", "Re-run `make_plan_collections.py` after `ref_flow.py` for all plans."],
    ["PDF templates", "The insurer name is not printed on the documents.", "Add `CarrierName` to the print data and the templates."],
    ["v1.2 items", "See the consolidated list in section 19.6 (notifications live, sign-in, portal URL, role checks on feed and master data, maker stamp, dashboard accuracy, documents).", "Section 19.6."]], [22, 46, 32])
H2("14.1 Troubleshooting")
TBL(["Symptom", "Likely cause", "Check"], [
    ["HTTP 500 `UP-CONFIG`", "A configuration key, table row (carrier, channel, product) is missing", "Log of the trace id names the key / table"], ["Cancel approve returns 409 `platform refused`", "Platform validation of the endorsement (for example OrgCode -1 on an old policy)", "Text after the policy number; run `probe_approve.py <PolicyNo>` to see each step"],
    ["Get Plans returns no plan", "No active plan row for the variant and premium mode", "`UP_ProductPlanRelation`"], ["400 `UNKNOWN_VALUE` on a code", "Value missing in the code table", "`imo config codetable data --name X`"],
    ["Push fails to compile", "Callee not pushed yet or a Groovy static type error", "Push order (section 3.4)"], ["401 from every call", "Token expired", "Get a new token"],
    ["Document not generated", "Template missing or print host not in `AllowedHosts`", "`UP_DocTemplate`, `PrintUrl`, `AllowedHosts`"]], [28, 40, 32])
H2("14.2 First-Day Checklist for a New Developer")
NUM(["Install `imo`, log in to the MC tenant (`imo auth login --profile portal:uponly`).", "Clone the source export, read sections 2 and 4 of this guide.", "`source env.sh`, run `carrier_check.py` (one flow per product) to see the APIs work.",
     "Open `UPCancelService.groovy` and `UPValidator.groovy` next to sections 8 and 6.3.", "Make a harmless change in a copy tenant or a branch: add a `UP_FieldRule` row and see the 400.", "Read the specification and the policy model workbook (API-Field sheets) for the contract."])
ns.sections(globals())
# ================================================================== annex
H1("Appendix A. File Inventory")
rows = [[x["file"], str(x["lines"]), "inactive" if x.get("status") == 0 else "active"] for x in apis + funcs]
TBL(["File (under ic/)", "Lines", "Status"], rows, [70, 12, 18])
H1("Appendix B. Table Definitions")
for n, d in T.items():
    LBL(f"{n}  (id {d['id']}, {d['rows']} rows)")
    TYPES = {-4: "String", -3: "Decimal", -2: "Integer (long)", -1: "Integer"}
    TBL(["Column", "Data type", "Primary key"], [[f[0], TYPES.get(f[1], str(f[1])), "Y" if f[2] == "Y" else ""] for f in d["fields"]], [50, 25, 25])
