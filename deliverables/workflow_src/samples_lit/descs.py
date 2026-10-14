import openpyxl, re
WB = "/home/user/Tablet/deliverables/Afillar_PolicyModel_v0.4.xlsx"
ROUTE_SHEET = {"get-plans": "01 Get Plans", "proposal": "02 Create Proposal", "update-proposal": "03 Update Proposal", "issue": "04 Issue Policy", "load-policy": "05 Load Proposal - Policy",
               "proposal-reject": "06 Reject Proposal", "doc_generation": "07 Policy Documents (PDF)", "application_doc_generation": "08 Application Form (PDF)", "cancel-check": "09 Cancel Check (Checker)",
               "cancel-approve": "10 Cancel Approve (Approver)", "list-master-table": "11 Master Data", "commission-query": "12 Commission Query", "generate-feedfile": "13 Policy Feed File"}
SH = {}; GLOB_IN = {}; GLOB_OUT = {}
wb = openpyxl.load_workbook(WB, read_only=True)
for ws in wb:
    if not ws.title[:2].isdigit(): continue
    d = {"Input": {}, "Output": {}}
    for r in ws.iter_rows(values_only=True):
        if r[0] in ("Input", "Output") and r[2]:
            d[r[0]].setdefault(r[2], r)
            (GLOB_IN if r[0] == "Input" else GLOB_OUT).setdefault(r[2], r)
    SH[ws.title] = d
def fmt(r, with_req=True):
    parent, name, typ, req, cond, allowed, rng, ex, desc = r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]
    out = f"[{req}] " if (req and with_req) else ""
    out += (desc or "").strip()
    if allowed: out += f" Allowed: {allowed}."
    if rng: out += f" {rng}."
    if cond: out += f" Condition: {cond}"
    return re.sub(r"\s+", " ", out).strip()
MANUAL = {
 ("me", "Output"): {"UserName": "Platform user name of the caller (from the token).", "UserId": "Platform user id of the caller.", "DisplayName": "Full name of the caller.", "Email": "E-mail of the caller.", "Branch": "Branch of the caller (from UP_UserRole).", "Roles": "Roles of the caller: MAKER, PROPOSAL_CHECKER, CANCELLATION_CHECKER. Absent when the caller holds none.", "RoleEnforcement": "Y when the APIs check the caller's role, N when every signed-in user may call every API.", "AllowSelfApproval": "Y when the person who raised an item may also approve it.", "Insurer": "Insurer shown in the portal."},
 ("worklist", "Input"): {"ChannelCode": "[M] Channel code assigned to the partner (SOHAR).", "Type": "[M] PROPOSAL = proposals waiting for the Proposal Checker, CANCELLATION = cancellation requests for the Cancellation Checker, MINE = the caller's own submissions.", "Status": "[O] PENDING, ISSUED, REJECTED or ALL (cancellations: PENDING or ISSUED).", "ProductCode": "[O] Restrict to one product.", "FromDate": "[O] First date (YYYY-MM-DD).", "ToDate": "[O] Last date (YYYY-MM-DD).", "PageNo": "[O] Page number, starting at 1.", "PageSize": "[O] Rows per page."},
 ("worklist", "Output"): {"Type": "Queue that was read.", "Status": "Status filter applied.", "PageNo": "Page returned.", "PageSize": "Rows per page.", "Total": "Number of rows that match.", "Records": "Rows of the queue."},
 ("dashboard", "Input"): {"ChannelCode": "[M] Channel code assigned to the partner (SOHAR).", "Section": "[M] SUMMARY = counts of proposals and cancellations; COMMISSION = premium and commission of the issued policies of one product.", "ProductCode": "[C] Required for COMMISSION: the product to report.", "Scope": "[O] ALL or MINE (a Maker always sees MINE).", "FromDate": "[O] Start of the window (default: last 30 days).", "ToDate": "[O] End of the window."},
 ("share", "Input"): {"ChannelCode": "[M] Channel code assigned to the partner (SOHAR).", "DocType": "[M] QUOTATION, PROPOSAL or POLICY.", "Channel": "[M] EMAIL, SMS or BOTH.", "Email": "[O] Customer e-mail; the one stored on the proposal or policy is used when omitted.", "Mobile": "[O] Customer mobile number; the stored one is used when omitted.", "ProposalNo": "[C] Proposal number (DocType PROPOSAL).", "PolicyNo": "[C] Policy number (DocType POLICY).", "ProductCode": "[O] Product code.", "ProductSubcode": "[O] Product variant.", "Details": "[C] Quotation content (DocType QUOTATION): InsuredName, ProductName, PlanName, Premium, EffectiveDate."},
 ("share", "Output"): {"DocType": "What was shared.", "Channel": "Channel used.", "Notifications": "One entry per message sent.", "Event": "Notification event.", "Recipient": "Who receives it (CUSTOMER or a staff role).", "Status": "DRYRUN (not sent, the tenant has no SNS account yet), SENT or FAILED.", "To": "Recipient address, masked."},
 ("cancel-detail", "Input"): {"ChannelCode": "[M] Channel code assigned to the partner (SOHAR).", "PolicyNo": "[C] Policy number (send PolicyNo or ProposalNo).", "ProposalNo": "[C] Proposal number."},
 ("cancel-detail", "Output"): {"RequestNo": "Cancellation request number.", "RequestedBy": "Maker who raised the request.", "RequestedOn": "When the request was raised.", "CancelReason": "Reason given by the maker.", "CancellationDate": "Requested cancellation date.", "PolicyInfo": "Policy summary.", "PremiumDetails": "Premium and unexpired-days figures.", "RefundDetails": "Refund type, percent and amount.", "CanDecide": "Y when the caller may approve or reject (not the maker, unless self-approval is allowed)."},
}
GLOSS = {"PolicyCustomerList": "List of customers (one element: customer CIF number and type).", "PolicyLobList": "Line-of-business list (one element: the product and its risk).", "PolicyRiskList": "Insured persons of the policy (one element).", "PlanList": "Plan chosen for the insured (one element).", "PolicyCoverageList": "Coverages of the plan with their sums insured.", "BeneficiaryList": "Beneficiaries of the insured.", "PolicyPaymentInfoList": "Payment (debit account) details.", "Records": "Rows returned.", "Plans": "Plans of the product variant.",
 "TempData": "Platform work area; not used by the partner.", "BusinessObjectId": "Platform internal id.", "PolicyElementId": "Platform internal id of the element.", "ParentPolicyElementId": "Platform internal id of the parent element.", "ParentElementType": "Type of the parent element.",
 "PolicyId": "Platform internal policy id.", "InsertBy": "Platform user id that created the record.", "InsertBy_CodeDesc": "User name that created the record.", "UpdateBy_CodeDesc": "User name that last changed the record.", "InsertTime": "Creation time stamp.",
 "UpdateTime": "Last change time stamp.", "SequenceNumber": "Position of the element in its list.", "PolicyStatus": "Policy status code.", "PolicyStatus_CodeDesc": "Policy status text.", "Mask-IdNo": "Id number as masked for display.", "Mask-Mobile": "Mobile number as masked for display.",
 "MaskAfter-IdNo": "Id number after masking.", "MaskAfter-Mobile": "Mobile number after masking.", "IsInsured": "Y when the party is the insured.", "IsPolicyHolder": "Y when the party is the policy holder.", "IsOrgParty": "Y when the party is an organisation.",
 "AdjustedPremium": "Premium after adjustments.", "AnnualPremium": "Annual premium.", "GrossPremium": "Gross premium.", "StandardGrossPremium": "Standard gross premium before adjustments.", "BeforeVatPremium": "Premium before tax (no VAT applies).",
 "IsPremiumCalcSuccess": "Y when the premium was calculated.", "BusinessCateCode": "Business category.", "AgentCode": "Platform user id of the maker who created the proposal.", "FirstDataEntryDate": "First data-entry date of the policy.", "InstallmentList": "Premium installment schedule.",
 "PlanName": "Plan name.", "CoverageDescription": "Coverage name.", "CoverageCode": "Coverage code (REX repatriation, ACD accidental death, PTD, PPD, TTD, HCB hospital cash, DTH death ...).", "ProductElementCode": "Product element code (coverage code, or R00001 for the risk).", "IsAutoAttachedForm": "Y when the form is attached automatically."}
ERR = {"api": "Name of the API that returned the error.", "code": "Error code: UP-VALIDATION (a field is wrong), UP-PLATFORM-VALIDATION (a platform rule failed), UP-400, UP-403 (role not allowed), UP-404 (not found), UP-409 (not possible in the current state), UP-CONFIG / UP-500 (service problem). Gateway errors use their own code.",
       "errors": "List of field errors (one entry per wrong field).", "field": "Path of the wrong field in the request.", "message": "Reason in plain words.", "status": "HTTP status of the response.",
       "trace_id": "Trace id; quote it when asking support to look at the call.", "traceId": "Trace id; quote it when asking support to look at the call.", "timestamp": "Time of the error (tenant time).", "timestampServer": "Time of the error (server time, UTC).",
       "path": "Path that was called.", "env": "Platform environment that answered.", "tenant": "Tenant that answered.", "_raw": "Raw text of the answer."}
def describe(route, direction, key):
    if direction == "Error":
        if key in ERR: return ERR[key]
        direction = "Output"
    """Description of a field of a request (Input) or response (Output)."""
    m = MANUAL.get((route, direction), {})
    if key in m: return m[key]
    sh = SH.get(ROUTE_SHEET.get(route, ""), {}).get(direction, {})
    if key in sh: return fmt(sh[key])
    if direction == "Input" and key in GLOB_IN: return fmt(GLOB_IN[key], False)
    if direction == "Output" and key in GLOB_OUT: return fmt(GLOB_OUT[key], False)
    if key in GLOB_IN: return fmt(GLOB_IN[key], False)
    if key in GLOB_OUT: return fmt(GLOB_OUT[key], False)
    if key in GLOSS: return GLOSS[key]
    if key.endswith("_CodeDesc"): return f"Text of the code in {key[:-9]}."
    if key in ("DuePremium", "SumInsured") and direction == "Input": return "Sample value only: premium / sum insured come from the plan configuration and are calculated by the platform (not part of the specified input)."
    if key in ("DuePremium", "SumInsured"): return "Premium / sum insured of the element, calculated by the platform."
    return "Platform field returned by the policy service."
