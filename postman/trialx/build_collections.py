#!/usr/bin/env python3
"""Build the Trialx Postman collections for the 34 portal APIs.

Source: "Portal Integration API Specification" v0.2 (API-01 .. API-34).
Outputs (next to this script):
  Trialx-Portal-APIs-Mandatory.postman_collection.json      - mandatory fields only
  Trialx-Portal-APIs-Full-Optional.postman_collection.json  - mandatory + optional fields
  Trialx.postman_environment.json                           - trialx environment

Both collections carry the saved sample responses from the spec, structure
tests, ID chaining between calls, and a "Datatable and LoadTables" folder with
every code table / data table / rate table that an API field is bound to.

Run:  python3 build_collections.py
"""
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NS = uuid.UUID("5b1f3c0e-7a51-4d0c-9d44-7f1e0c2b9a10")


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


# ---------------------------------------------------------------------------
# Postman building helpers
# ---------------------------------------------------------------------------

def url_obj(path, query=None):
    query = query or []
    qs = "&".join(f"{q['key']}={q['value']}" for q in query if not q.get("disabled"))
    raw = "{{baseUrl}}" + path + (("?" + qs) if qs else "")
    u = {"raw": raw, "host": ["{{baseUrl}}"], "path": [p for p in path.strip("/").split("/") if p]}
    if query:
        u["query"] = query
    return u


def q(key, value, desc="", disabled=False):
    d = {"key": key, "value": value}
    if desc:
        d["description"] = desc
    if disabled:
        d["disabled"] = True
    return d


def h(key, value, desc="", disabled=False):
    d = {"key": key, "value": value, "type": "text"}
    if desc:
        d["description"] = desc
    if disabled:
        d["disabled"] = True
    return d


def js(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def request(name, method, path, *, query=None, body=None, raw_body=None, formdata=None,
            headers=None, desc="", examples=None, tests="", no_auth=False, key=""):
    headers = list(headers or [])
    req = {"method": method, "header": headers, "url": url_obj(path, query), "description": desc}
    if body is not None or raw_body is not None:
        headers.append(h("Content-Type", "application/json"))
        req["body"] = {"mode": "raw", "raw": raw_body if raw_body is not None else js(body),
                       "options": {"raw": {"language": "json"}}}
    if formdata is not None:
        req["body"] = {"mode": "formdata", "formdata": formdata}
    if no_auth:
        req["auth"] = {"type": "noauth"}
    item = {"id": uid(key or name, method, path), "name": name, "request": req, "response": []}
    for ex in examples or []:
        ex_name, code, status, ex_body = ex[:4]
        ex_headers = ex[4] if len(ex) > 4 else [{"key": "Content-Type", "value": "application/json"}]
        item["response"].append({
            "id": uid(key or name, ex_name),
            "name": ex_name,
            "originalRequest": {k: v for k, v in req.items() if k != "description"},
            "status": status,
            "code": code,
            "_postman_previewlanguage": "json" if not isinstance(ex_body, str) else "text",
            "header": ex_headers,
            "body": ex_body if isinstance(ex_body, str) else js(ex_body),
        })
    if tests:
        item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": tests.strip("\n").split("\n")}}]
    return item


def folder(name, items, desc=""):
    return {"id": uid("folder", name), "name": name, "description": desc, "item": items}


# ---------------------------------------------------------------------------
# Test-script snippets
# ---------------------------------------------------------------------------

def t_struct(api_id, checks, sets=""):
    """checks: JS boolean expressions evaluated against `b` (parsed body)."""
    lines = [
        f"// {api_id} structure check. Logs PASS/FAIL so a Newman run doubles as the structure report.",
        "const code = pm.response.code;",
        "let b = null; try { b = pm.response.json(); } catch (e) {}",
        f"pm.test('{api_id} route exists (not 404)', () => pm.expect(code, 'gateway 404 = wrong path or unpublished API').to.not.eql(404));",
        f"pm.test('{api_id} permitted (not 401/403)', () => pm.expect([401, 403]).to.not.include(code));",
        f"pm.test('{api_id} HTTP 2xx', () => pm.expect(code).to.be.within(200, 299));",
    ]
    for label, expr in checks:
        lines.append(f"pm.test('{api_id} structure: {label}', () => pm.expect(!!(b !== null && ({expr})), '{label}').to.be.true);")
    if sets:
        lines.append("if (code >= 200 && code < 300 && b) { try {")
        lines.extend("  " + s for s in sets.strip().split("\n"))
        lines.append("} catch (e) { console.log('chain variable not set: ' + e); } }")
    return "\n".join(lines)


ENVELOPE_ATT = [("Status present", "'Status' in b"), ("Model present", "'Model' in b"), ("Messages is array", "Array.isArray(b.Messages)")]
ENVELOPE_SNS = [("code present", "'code' in b"), ("data present", "'data' in b")]
QUERY_RESULT = [("Results is array", "Array.isArray(b.Results)"), ("Total present", "'Total' in b")]
PAGED = [("ElementsInCurrentPage is array", "Array.isArray(b.ElementsInCurrentPage)"), ("TotalElements present", "'TotalElements' in b")]
IS_ARRAY = [("body is JSON array", "Array.isArray(b)")]

GATEWAY_404 = ("Gateway 404 observed on trialx (28 Sep 2026)", 404, "Not Found", "404 page not found",
               [{"key": "Content-Type", "value": "text/plain; charset=utf-8"}])
GATEWAY_401 = ("Gateway 401 - invalid token (observed on trialx)", 401, "Unauthorized", {
    "env": "aws_sg_insuremo_portal", "env_name": "aws_sg_insuremo_portal",
    "trace_id": "687e2ac1693a6d17bc0f525732f82724", "status": 401,
    "flag": "This is an error reported by the container gateway. Please contact with container.",
    "message": "gateway: invalid token"})


# ---------------------------------------------------------------------------
# Code tables referenced by API fields  (name -> (source, [usages], known values))
# ---------------------------------------------------------------------------
SVC = "Service table"
CT = "Code table"
CODE_TABLES = {
    "PartyType": (CT, ["API-01 EsDocs.PartyType", "API-04 PartyType", "API-30 ClaimParty.PtyPartyType"], [("13", "Individual Agent"), ("14", "Agent Company")]),
    "SCTypeIndividual": (CT, ["API-01 EsDocs.ScType (individual)", "API-04 ScType"], [("1", "Agency")]),
    "SCTypeOrg": (CT, ["API-01 EsDocs.ScType (company)", "API-04 ScType"], [("2", "Broker")]),
    "SChannelStatus": (CT, ["API-01 EsDocs.ScStatus / filters", "API-04 ScStatus"], [("0", "In Setup Progress"), ("1", "Active"), ("2", "Rejected"), ("3", "Terminated"), ("4", "Suspended"), ("5", "Legal")]),
    "Gender": (CT, ["API-01 EsDocs.Gender", "API-04 Gender", "API-13/21 PolicyCustomer.GenderCode"], [("M", "Male"), ("F", "Female")]),
    "PartyRoleCategory": (CT, ["API-04 PartyCategory"], []),
    "PartyStatus": (CT, ["API-04 PartyStatus"], []),
    "Currency": (CT, ["API-04 ChannelCurrencyCode", "API-30 ClaimObject.EstimatedLossCurrency", "API-31 CurrencyCode"], []),
    "CountryCode": (CT, ["API-04 NationalityCode", "API-12 ProductMaster.Country", "API-13/21 PolicyCustomer.NationalityCode, LocationCountryCode"], []),
    "MaritalStatus": (CT, ["API-04 MaritalStatus"], []),
    "Department": (CT, ["API-04/18/19 PartyContact.Department"], []),
    "Designation": (CT, ["API-04/18/19 PartyContact.Designation"], []),
    "Language": (CT, ["API-04/18/19 PartyContact.LanguagePreferred"], []),
    "Bank": (CT, ["API-04 PartyAccount.BankCode", "API-13/21 PolicyPaymentInfo.BankCode", "API-18/19 PartyAccount.BankCode"], []),
    "AgreementStatus": (CT, ["API-05 SalesAgreement.AgreementStatus"], [("0", "Invalid"), ("1", "Valid"), ("2", "Expired"), ("3", "Rejection"), ("4", "Waiting for Approval")]),
    "AuthorityType": (CT, ["API-05 SalesAgreementAuthorityList.AuthorityType"], []),
    "PubBranch": (SVC, ["API-06/07 BranchCode", "API-09 BranchCode", "API-20 OrgCode"], []),
    "BcpCollectionStatus": (CT, ["API-06/07 CollectionStatus"], [("1", "Collected"), ("2", "Confirmed"), ("3", "Reversed"), ("4", "Refund")]),
    "BcpCollectionType": (CT, ["API-06/07 CollectionType"], [("1", "Prepay"), ("2", "Collection"), ("3", "Policy Premium")]),
    "YesNo": (CT, ["API-06/07/08 HasNote", "API-08 IsApproved, IsOffsetByCommission, NeedStatement", "API-13/21 IsPolicyHolder, IsInsured, IsOrgParty, IsInstallment", "API-20 IsRenewalPolicy", "API-30/31/32 flags"], [("Y", "Yes"), ("N", "No")]),
    "BcpPaymentMethod": (CT, ["API-06/07/08 PaymentMethod"], [("100", "(code seen in samples)")]),
    "UserInfo": (SVC, ["API-06 ReceiveBy, ReverseBy", "API-07 ReceiveBy, ConfirmBy"], []),
    "BcpBranchAccount": (CT, ["API-07 InsurerAccountCode"], []),
    "BcpPayerPayeeType": (CT, ["API-07/08 PayerPayeeType"], []),
    "BcpArapCate": (CT, ["API-08 Arap.ArapCate"], [("1", "Receivable"), ("2", "Payable")]),
    "BcpArapStatus": (CT, ["API-08 Arap.ArapStatus"], [("1", "Outstanding"), ("2", "Settled"), ("7", "Cancelled")]),
    "BcpArapType": (CT, ["API-08 Arap.ArapType / ArapType"], [("-1001", "(code seen in samples)")]),
    "PayerOrPayeeCategory": (CT, ["API-08 Arap.PayerPayeeCate"], []),
    "SalesCommissionType": (CT, ["API-09 CommissionType"], []),
    "SalesCommissionStatus": (CT, ["API-09 CommissionStatus"], [("2", "Waiting for Issue"), ("4", "Offset")]),
    "BcpFeeType": (CT, ["API-09 FeeType"], [("100600", "Commission")]),
    "SalesChannelAPI": (SVC, ["API-09 ChannelCode", "API-20 AgentCode"], []),
    "SalesAgreementAPI": (SVC, ["API-09 AgreementCode"], []),
    "Products": (SVC, ["API-09 ProductCode", "API-20 ProductCode"], []),
    "ProductLine": (CT, ["API-09 ProductLineCode", "API-12 ProductMaster.ProductLineId"], []),
    "ProductEffectiveStatus": (CT, ["API-12 EffectiveFlag, CashBeforeCover, IsRequired, IsGroup, IsTemplate, IsPackage"], []),
    "ProductSpecialModel": (CT, ["API-12 ChooseModel"], []),
    "PolicyType": (CT, ["API-12 DefinitionSuperObjectName, ProductMaster.PolicyType", "API-20 PolicyType", "API-29/30 PolicyTypeCode"], []),
    "ProductInsuredCategory": (CT, ["API-12 ChildProductTreeNodeList.InsuredCategory"], []),
    "ProductType": (CT, ["API-12 ProductMaster.ProductTypeId"], []),
    "BusinessLine": (CT, ["API-12 ProductMaster.BusinessLine"], []),
    "SecondLine": (CT, ["API-12 ProductMaster.SecondLine"], []),
    "ThirdLine": (CT, ["API-12 ProductMaster.ThirdLine"], []),
    "FourthLine": (CT, ["API-12 ProductMaster.FourthLine"], []),
    "FinanceLine": (CT, ["API-12 ProductMaster.FinanceLine"], []),
    "ContainerCategory": (CT, ["API-12 ProductMaster.ContainerCategory"], []),
    "ProposalStatus": (CT, ["API-13/17/20/21 ProposalStatus"], [("1", "Entry"), ("2", "Bound"), ("3", "Issued"), ("4", "Rejected"), ("5", "Underwriting"), ("6", "Waiting For Payment"), ("10", "Quotation In Progress")]),
    "PolicyStatus": (CT, ["API-17/20/21 PolicyStatus", "API-31 PolicyStatus"], [("1", "Not effective"), ("2", "Effective"), ("3", "Cancelled"), ("4", "To be removed"), ("99", "Expired (deprecated)")]),
    "ProductElementIdAPI": (SVC, ["API-13/21 PolicyLob.ProductElementId, PolicyRisk.ProductElementId"], []),
    "CoverageTerminateCode": (CT, ["API-13/21 PolicyLob.TerminateCode"], []),
    "CustomerIDType": (CT, ["API-13/21 PolicyCustomer.IdType", "API-20 IdType"], [("1", "(code seen in samples)")]),
    "BearStatus": (CT, ["API-13/21 PolicyCustomer.BearStatus"], []),
    "PersonRelation": (CT, ["API-13/21 PolicyCustomer.RelationWithPolicyholder", "API-30 ClaimParty.InsuredRelation"], []),
    "CompanyIndulstry": (CT, ["API-13/21 PolicyCustomer.CompanyIndustry (name spelled as in the data dictionary)"], []),
    "PayMethod": (CT, ["API-13/21 PolicyPaymentInfo.PayModeCode"], [("100", "(code seen in samples)")]),
    "InstallmentType": (CT, ["API-13/21 PolicyPaymentInfo.InstallmentType"], []),
    "AccountNature": (CT, ["API-13/21 PolicyPaymentInfo.AccountType"], []),
    "CertiType": (CT, ["API-13/21 PolicyPaymentInfo.AccountHolderIdType", "API-31 PolicyHolderIdType, InsuredIdType"], []),
    "AttachBusinessType": (CT, ["API-14/23 BusinessType", "API-22 businessType", "API-25 BusinessType", "API-26 businessType"], []),
    "ClaimGender": (CT, ["API-28 MainExtendInfo.GenderCode", "API-30 ClaimObject.Gender, ClaimParty.ClaimGender"], []),
    "Country": (CT, ["API-28/29/30 AccidentCountryCode"], []),
    "CauseOfLoss": (CT, ["API-28/29/30 LossCause"], []),
    "ClaimType": (CT, ["API-28/29/30 ClaimType"], []),
    "ClaimFnolType": (CT, ["API-28/29/30 FnolType"], []),
    "ClaimYesNo": (CT, ["API-28/29/30 IsFromApp", "API-29/30 PendingClaim"], []),
    "CurrencyCodeClaim": (CT, ["API-28/29/30 CurrencyCode"], []),
    "ClaimStatus": (CT, ["API-29 request CaseStatus", "API-29/30 CaseStatus", "API-33 CaseStatus"], []),
    "FnolStatus": (CT, ["API-29/30 FnolStatus"], []),
    "ClaimFnolValidationDecision": (CT, ["API-29/30 FnolValidationDecision"], []),
    "CaseMode": (CT, ["API-29/30 CaseMode"], []),
    "ClaimRecordType": (CT, ["API-29/30 RecordType"], []),
    "Org": (CT, ["API-29 request PolicyOrgCode", "API-29/30 PolicyOrgCode, CaseOrgCode", "API-31 OrgCode"], []),
    "ProductLineClaim": (CT, ["API-29 EcsProductLineCode"], []),
    "BusinessCategory": (CT, ["API-29/30 BusinessCateCode", "API-31 BusinessCateCode"], []),
    "ClaimLossStatus": (CT, ["API-29/30 LossStatus"], []),
    "ClaimSalvageStatus": (CT, ["API-29/30 SalvageStatus"], []),
    "YesOrNoClaim": (CT, ["API-29/30 WithPolicy", "API-30 ClaimObject.TotalLossFlag"], []),
    "InsuranceCompany": (CT, ["API-29 EcsInsuranceCompanyCode"], []),
    "ClaimCloseType": (CT, ["API-29/30 CloseType"], []),
    "ClaimClosedType": (CT, ["API-29/30 ClosedType"], []),
    "ClaimRejectReason": (CT, ["API-29/30 RejectReason"], []),
    "ClaimReopenCause": (CT, ["API-29/30 ReopenCauseCode"], []),
    "RelatedType": (CT, ["API-29 RelatedType"], []),
    "SubclaimType": (CT, ["API-30 ClaimObject.SubClaimType"], []),
    "SubclaimStatus": (CT, ["API-30 ClaimObject.StatusCode"], []),
    "DamageType": (CT, ["API-30 ClaimObject.DamageType"], []),
    "ClaimSubrogationStatus": (CT, ["API-30 ClaimObject.SubrogationStatus"], []),
    "Party": (CT, ["API-30 ClaimParty.PtyPartyCode"], []),
    "IDTypeClaim": (CT, ["API-30 ClaimParty.IdType"], []),
    "PayModeClaim": (CT, ["API-30 ClaimParty.PayModeCode"], []),
    "ProductMaster": (CT, ["API-31 ProductCode"], []),
    "Region": (CT, ["API-31 RegionCode"], []),
    "EndorsementType": (CT, ["API-32 EndoType"], [("3", "Cancellation"), ("20", "Period of insurance extension / shortening / move")]),
    "EndorsementStatus": (CT, ["API-32 EndoStatus"], [("120", "Entry (default)"), ("300", "Issued"), ("401", "Undo")]),
    "EndorsementReason": (CT, ["API-32 CauseType"], []),
    "ShortRateType": (CT, ["API-32 ShortRateType"], []),
    "AutoUnderwritingResult": (CT, ["API-32 AutoUwResultCode"], []),
    "UnderwritingLevel": (CT, ["API-32 CurUwLevelCode, MaxUwLevelCode"], []),
    "OperatorType": (CT, ["API-32 DataEntryUserType"], []),
}

# Fields the spec calls "tenant code tables" without naming the table.
UNNAMED_CODE_FIELDS = [
    ("API-18/19", "CustomerType, IdType, AddressType", "Named only as 'tenant code tables' - table names to confirm"),
    ("API-19", "OrgType, LegalStatus", "Named only as 'tenant code tables' - table names to confirm"),
    ("API-04/18/19", "IdType (party / customer)", "No code table named in the spec"),
]

# Per-API field -> code table map, shown in each request description.
API_CODE_FIELDS = {}
for _name, (_src, _uses, _vals) in CODE_TABLES.items():
    for _u in _uses:
        _api = _u.split(" ", 1)[0]
        API_CODE_FIELDS.setdefault(_api, []).append((_u.split(" ", 1)[1] if " " in _u else "", _name, _src))


def code_table_md(api_ids):
    rows = []
    for key, vals in API_CODE_FIELDS.items():
        ids = set()
        prefix, _, rest = key.partition("-")
        for part in rest.split("/"):
            ids.add(f"API-{part}")
        if ids & set(api_ids):
            rows.extend(vals)
    if not rows:
        return ""
    seen = set()
    out = ["", "### Fields bound to code tables / data tables",
           "Load the values with the matching request in **Datatable and LoadTables**.", "",
           "| Field | Table | Source |", "|---|---|---|"]
    for field, name, src in rows:
        if (field, name) in seen:
            continue
        seen.add((field, name))
        out.append(f"| {field} | `{name}` | {src} |")
    return "\n".join(out)


def desc(api_id, title, endpoint, owner, variant, notes="", mand_table=""):
    parts = [f"**{api_id} {title}**  ", f"`{endpoint}` · Owner: {owner}  ",
             f"Variant: **{variant}**", ""]
    if mand_table:
        parts += [mand_table, ""]
    if notes:
        parts += [notes, ""]
    parts.append(code_table_md([api_id]))
    return "\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------------------
# API definitions. Each entry: dict with id, title, owner, and `requests`, a list
# of request specs {name, method, path, mand:{query,body,...}, full:{...}, examples, tests}
# ---------------------------------------------------------------------------
SEARCH_FULL_KEYS = ["PageNo", "PageSize", "Conditions", "FuzzyConditions", "InConditions", "NotInConditions",
                    "FromRangeConditions", "ToRangeConditions", "ExistFields", "NotExistFields", "OrConditions",
                    "OrFuzzyConditions", "OrInConditions", "OrConditionsList", "OrFuzzyConditionsList",
                    "SortField", "SortType", "SortFieldAndTypeList", "AggConditions", "GroupField", "IncludeFields"]

APIS = []

# ---- API-01 --------------------------------------------------------------
APIS.append(dict(
    id="API-01", title="Search Sales Channel Pool API", owner="EasyPA Apps Team",
    endpoint="POST /platform/saleschannel/channel/pool/list",
    requests=[dict(
        name="Search Sales Channel Pool", method="POST", path="/platform/saleschannel/channel/pool/list",
        mand=dict(body={"Module": "SalesChannel"}),
        full=dict(body={
            "Module": "SalesChannel", "PageNo": 1, "PageSize": 20,
            "Conditions": {"ScStatus": 1},
            "FuzzyConditions": {"PartyName": "abc"},
            "InConditions": {"ScType": ["1", "2"]},
            "NotInConditions": {"PartyType": ["99"]},
            "FromRangeConditions": {"index_time": "2026-01-01"},
            "ToRangeConditions": {"index_time": "2026-12-31"},
            "ExistFields": ["PartyCode"], "NotExistFields": ["FullChildCode"],
            "OrConditions": {"OrgCode": "10002"},
            "OrFuzzyConditions": {"PartyName": "abc", "PartyCode": "abc"},
            "OrInConditions": {"ScStatus": [1, 3, 4, 5]},
            "OrConditionsList": [{"ScType": "1"}, {"ScType": "2"}],
            "OrFuzzyConditionsList": [{"PartyName": "abc"}],
            "SortField": "index_time", "SortType": "desc",
            "SortFieldAndTypeList": [{"SortField": "index_time", "SortType": "desc"}],
            "AggConditions": {"GroupFields": ["ScType"]},
            "GroupField": "entity_type",
            "IncludeFields": ["entity_id", "PartyCode", "PartyName", "PartyType", "ScType", "ScStatus"]}),
        examples=[("200 OK - individual agent + agent company", 200, "OK", {
            "GroupField": "entity_type", "PageNo": 1, "PageSize": 1000, "Total": 2,
            "Results": [{"GroupValue": "SalesChannel", "GroupTotalNum": 2, "EsDocs": [
                {"entity_id": "1000245100,88AD0B57BEB0EC202BAB3E179F0F0CE2", "index_time": "2026-09-15T10:20:31", "PartyCode": "ABC0000001", "PartyName": "Abc Kumar", "PartyType": "13", "ScType": "1", "ScStatus": 1, "SalesChannelLevel": "Branch Manager", "ScSupportOfficer": "SO0001", "BranchInfo": "Mumbai Branch", "OrgCode": "10002", "FullOrgCode": "10002\n10001", "FullParentCode": "", "FullChildCode": "", "Gender": "M", "IdType": "1", "IdNumber": "ABCPK1234F"},
                {"entity_id": "1000245200,5C1E7A2B9D34F0A6B8C7E1D2F3A4B5C6", "index_time": "2026-09-20T14:05:12", "PartyCode": "ABC0000002", "PartyName": "Abc Insurance Brokers Pvt Ltd", "PartyType": "14", "ScType": "2", "ScStatus": 1, "SalesChannelLevel": "Head Office", "ScSupportOfficer": "SO0002", "BranchInfo": "Head Office", "OrgCode": "10001", "FullOrgCode": "10001", "FullParentCode": "", "FullChildCode": "ABC0000003\nABC0000004", "ParentOrgId": 10001, "OrganizationIdType": "2", "OrganizationIdNumber": "U66000MH2020PTC123456", "RegistrationName": "Abc Insurance Brokers Private Limited"}]}]}),
            ("200 OK - with aggregation", 200, "OK", {
                "AggConditions": {"GroupFields": ["ScType"]},
                "Aggs": {"GroupResult": [{"ScType": "1", "docCount": 120}, {"ScType": "2", "docCount": 35}]},
                "GroupField": "entity_type", "PageNo": 1, "PageSize": 10,
                "Results": [{"GroupValue": "SalesChannel", "GroupTotalNum": 155, "EsDocs": []}], "Total": 155}),
            GATEWAY_401],
        checks=QUERY_RESULT,
        sets="const d = b.Results[0].EsDocs[0];\npm.collectionVariables.set('channelId', encodeURIComponent(d.entity_id));",
        notes="Sets `channelId` (URL-encoded signed `entity_id`) for API-04 / API-05.")],
))

# ---- API-02 --------------------------------------------------------------
TOKEN_SETS = ("pm.collectionVariables.set('access_token', b.access_token);\n"
              "pm.collectionVariables.set('token_expires_at', Date.now() + (b.expire_in - 60) * 1000);")
APIS.append(dict(
    id="API-02", title="Service to Service Authentication - Get Token API", owner="EasyPA Apps Team",
    endpoint="POST /cas/get-token",
    requests=[dict(
        name="Get Token", method="POST", path="/cas/get-token", no_auth=True,
        mand=dict(body={"username": "{{username}}", "password": "{{password}}", "tenant_code": "{{tenantCode}}"}),
        full=dict(headers=[h("x-mo-client-id", "member", "Conditional: only for users verified by an external user service (SSO auth type rest)", disabled=True)],
                  body={"username": "{{username}}", "password": "{{password}}", "tenant_code": "{{tenantCode}}",
                        "extend_params": [{"name": "testkey", "value": "testparam"}]}),
        examples=[("200 OK - token issued (spec sample)", 200, "OK", {"access_token": "bbmkLEg7TmmeKuMgDv5Q_A", "expire_in": 7216, "message": "", "retry_times": 0}),
                  ("200 - wrong credentials (observed on trialx gateway)", 200, "OK", {"access_token": "", "expire_in": 0, "message": "user name or password is wrong", "err_code": "w_cas_password_notright", "retry_times": 1, "authResult": False, "auth_result": False, "trace_id": "c7785231ff8504a80b939ad7f7a0fd69"}),
                  ("400 - empty body (observed on trialx gateway)", 400, "Bad Request", {"message": "parameter is empty"})],
        checks=[("access_token non-empty", "typeof b.access_token === 'string' && b.access_token.length > 0"), ("expire_in present", "'expire_in' in b")],
        sets=TOKEN_SETS,
        notes=("Stores `access_token` for every other request (collection auth = Bearer {{access_token}}).\n"
               "Observed on trialx: a failed login still returns HTTP 200 with `access_token: \"\"` and extra fields "
               "`err_code`, `authResult`, `auth_result`, `trace_id` that the spec does not list."))],
))

# ---- API-03 --------------------------------------------------------------
APIS.append(dict(
    id="API-03", title="SMS OTP Dispatch for MFA API", owner="EasyPA Apps Team",
    endpoint="POST /mo-fo/1.0/sns/mfa/sms/send · /verify",
    requests=[
        dict(name="Send MFA SMS code", method="POST", path="/mo-fo/1.0/sns/mfa/sms/send",
             mand=dict(body={"to": "{{mobileNo}}"}),
             full=dict(body={"to": "{{mobileNo}}", "business_code": "LOGIN", "code_length": 6, "code_strategy": 0,
                             "expires_in_minutes": 15, "block_resend_in_seconds": 30, "account_name": "{{smsAccount}}",
                             "sign_name": "{{signName}}", "auto_add_sign": True, "template_code": "{{otpTemplateCode}}",
                             "template_params": {"template_var": "123"}, "sender_params": {}, "use_zh_bracket": False}),
             examples=[("200 OK (spec structure)", 200, "OK", {"code": "string", "message": "string", "trace_id": "traceid0000000000000000000000000", "data": {"message_id": "string", "content_length": 0}})],
             checks=ENVELOPE_SNS + [("data.message_id present", "b.data && 'message_id' in b.data")],
             notes="code_strategy: 0 numbers only, 1 numbers + uppercase, 2 numbers + letters. The OTP itself is never returned."),
        dict(name="Verify MFA SMS code", method="POST", path="/mo-fo/1.0/sns/mfa/sms/verify",
             mand=dict(body={"to": "{{mobileNo}}", "code": "{{otpCode}}"}),
             full=dict(body={"to": "{{mobileNo}}", "code": "{{otpCode}}", "business_code": "LOGIN", "case_sensitive": False, "keep": False, "output_result": True}),
             examples=[("200 OK - verified (spec structure)", 200, "OK", {"code": "string", "message": "string", "trace_id": "traceid0000000000000000000000000", "data": {"to": "+18xxxxx000", "verified": True}})],
             checks=ENVELOPE_SNS + [("data.verified is boolean", "b.data && typeof b.data.verified === 'boolean'")],
             notes="Without output_result=true a wrong/expired code returns an error HTTP status instead of verified:false."),
    ],
))

# ---- API-04 --------------------------------------------------------------
APIS.append(dict(
    id="API-04", title="Load Sales Channel by Channel ID API", owner="EasyPA Apps Team",
    endpoint="GET /platform/saleschannel/core/channel/load/byChannelId",
    requests=[dict(
        name="Load Sales Channel by Channel ID", method="GET", path="/platform/saleschannel/core/channel/load/byChannelId",
        mand=dict(query=[q("channelId", "{{channelId}}", "Signed ID '<number>,<signature>' from API-01 entity_id, comma URL-encoded as %2C")]),
        full=dict(query=[q("channelId", "{{channelId}}", "Signed ID '<number>,<signature>' from API-01 entity_id, comma URL-encoded as %2C")]),
        examples=[("200 OK - individual agent", 200, "OK", {
            "@type": "Party-Party", "PartyId": "1000245100,88AD0B57BEB0EC202BAB3E179F0F0CE2", "PartyCode": "ABC0000001", "PartyName": "Abc Kumar", "PartyType": "13", "PartyCategory": "IND", "IsOrgParty": "N", "ScType": "1", "ScStatus": 1, "SalesChannelLevel": "Branch Manager", "ScSupportOfficer": "SO0001", "OrgCode": "10002", "BranchInfo": "Mumbai Branch", "RegulatoryID": "REG-778812", "ChannelCurrencyCode": "INR", "PrimaryAccountId": 1000245130, "Prefix": "Mr", "FirstName": "Abc", "LastName": "Kumar", "Gender": "M", "DateOfBirth": "1985-04-12", "IdType": "1", "IdNumber": "ABCPK1234F", "NationalityCode": "IND", "Mobile": "+919800000001", "Email": "abc.kumar@example.com", "LanguagePreferred": "en_US", "PayModeCode": "100",
            "PartyContactList": [{"ContactId": 1000245110, "ContactName": "Abc Kumar", "IsPrimaryContact": "Y", "HandPhone": "+919800000001", "Email": "abc.kumar@example.com"}],
            "PartyAddressList": [{"AddressId": 1000245120, "AddressType": "1", "IsPrimaryAddress": "Y", "AddressLine1": "12 MG Road", "City": "Mumbai", "Province": "MH", "CountryCode": "IND", "PostCode": "400001"}],
            "PartyAccountList": [{"AccountId": 1000245130, "IsPrimaryAccount": "Y", "AccountHolderName": "Abc Kumar", "AccountNo": "001234567890", "BankCode": "HDFC", "BankBranch": "Fort", "SwiftCode": "HDFCINBB", "ChannelCurrencyCode": "INR", "PayModeCode": "100"}]})],
        checks=[("PartyId or PartyCode present", "'PartyId' in b || 'PartyCode' in b")],
        notes="Only one parameter (mandatory), so the Mandatory and Full variants are identical.")],
))

# ---- API-05 --------------------------------------------------------------
AGREEMENT_SAMPLE = [{
    "@type": "SalesAgreement-SalesAgreement", "AgreementId": 1000245200, "AgreementCode": "AGR-2026-001", "AgreementStatus": 1, "ChannelId": "1000245100,88AD0B57BEB0EC202BAB3E179F0F0CE2", "EffectiveDate": "2026-01-01", "ExpiredDate": "2028-12-31", "OrgCode": "10002", "IsApprove": "Y", "ApproveUserStaffCode": "STAFF01", "Description": "Travel agency agreement",
    "SalesAgreementAuthorityList": [{"AuthorityId": 1000245210, "AuthorityType": "1", "ProductLineCode": "Travel", "ProductCode": "TBTI", "EffectiveDate": "2026-01-01", "ExpiredDate": "2028-12-31"}],
    "SalesCommissionRateList": [{"CommissionRateId": 1000245220, "ProductName": "TBTI-Oversea Travel", "CtCode": "C100416", "StandardCommissionRateNB": 10.00, "StandardCommissionRateRN": 7.50, "DeviationFromStandardNB": 0, "DeviationFromStandardRN": 0, "ExtraFixedAmountNB": 0, "ExtraFixedAmountRN": 0, "ComRateStatus": 1, "EffectiveDate": "2026-01-01", "ExpiredDate": "2028-12-31"}]}]
CH_Q = [q("channelId", "{{channelId}}", "Signed channel ID from API-01, comma URL-encoded as %2C")]
APIS.append(dict(
    id="API-05", title="Load Sales Agreements by Channel ID API", owner="EasyPA Apps Team",
    endpoint="GET /api/platform/saleschannel/agreement/load/byChannelId (spec) - 404 on trialx",
    requests=[
        dict(name="Load Sales Agreements by Channel ID (spec path - 404 on trialx)", method="GET",
             path="/api/platform/saleschannel/agreement/load/byChannelId", mand=dict(query=CH_Q), full=dict(query=CH_Q),
             examples=[GATEWAY_404, ("200 OK (spec sample)", 200, "OK", AGREEMENT_SAMPLE)], checks=IS_ARRAY,
             notes="**STRUCTURE NOT WORKING:** the `/api` prefix is not routed by the trialx gateway (HTTP 404 `404 page not found`). Use the SDK core path below."),
        dict(name="Load Sales Agreements by Channel ID (SDK core path - use this)", method="GET",
             path="/platform/saleschannel/core/agreement/load/byChannelId", mand=dict(query=CH_Q), full=dict(query=CH_Q),
             examples=[("200 OK (spec sample)", 200, "OK", AGREEMENT_SAMPLE), ("200 OK - no agreements", 200, "OK", [])], checks=IS_ARRAY,
             notes="SDK equivalent `loadByChannelIdCore`. Route answers on trialx (401 without token, so it is routed)."),
    ],
))

# ---- API-06 --------------------------------------------------------------
COLLECTION_ESDOC = {"CollectionId": "1000310046,8F610A1D28C0550C61543DE897210C3D", "ReceiptNo": "RCT20240600000012", "CollectionType": "1", "CollectionStatus": "1", "Amount": 1500.00, "Balance": 420.50, "CurrencyCode": "INR", "PaymentMethod": "100", "PayerPayeeCode": "ABC0000001", "PayerPayeeName": "Abc Kumar", "BankCode": "HDFC", "BranchCode": "10002", "FullOrgCode": "10002\n10001", "FullPolicyNo": "POTBTI01229164", "FullProposalNo": "PABTBTI0001298154", "FullEndoNo": "", "HasNote": "N", "ReceiveBy": 10000001178005, "ReceiveTime": "2024-06-01T11:02:13", "UpdateTime": "2024-06-05T09:40:00"}
APIS.append(dict(
    id="API-06", title="Float Statement - Search Collections API", owner="EasyBCP Apps Team",
    endpoint="POST /platform/bcp-core/query/v1/queryEsData",
    requests=[
        dict(name="Search Collections (SearchCondition per request table)", method="POST", path="/platform/bcp-core/query/v1/queryEsData",
             mand=dict(body={"Module": "Collection"}),
             full=dict(body={
                 "Module": "Collection", "PageNo": 1, "PageSize": 10,
                 "Conditions": {"CollectionType": "1"}, "FuzzyConditions": {"ReceiptNo": "2024"},
                 "InConditions": {"CollectionStatus": ["1", "2"]}, "NotInConditions": {"CollectionStatus": ["3"]},
                 "FromRangeConditions": {"ReceiveTime": "2023-04-30"}, "ToRangeConditions": {"ReceiveTime": "2024-06-09"},
                 "ExistFields": ["ReceiptNo"], "NotExistFields": ["ReverseTime"],
                 "OrConditions": {"PayerPayeeCode": "{{payerCode}}"}, "OrConditionsList": [{"CollectionStatus": "1"}, {"CollectionStatus": "2"}],
                 "OrFuzzyConditions": {"PayerPayeeName": "abc"}, "OrFuzzyConditionsList": [{"ReceiptNo": "RCT"}],
                 "OrInConditions": {"PaymentMethod": ["100"]},
                 "SortField": "index_time", "SortType": "desc", "SortFieldAndTypeList": [{"SortField": "ReceiveTime", "SortType": "desc"}],
                 "AggConditions": {"SumFields": ["Amount", "Balance"]}, "GroupField": "entity_type",
                 "IncludeFields": ["CollectionId", "ReceiptNo", "Amount", "Balance", "CollectionStatus"]}),
             examples=[("200 OK (spec sample)", 200, "OK", {"GroupField": "entity_type", "PageNo": 1, "PageSize": 10, "Total": 1, "Results": [{"GroupValue": "Collection", "GroupTotalNum": 1, "EsDocs": [COLLECTION_ESDOC]}]})],
             checks=QUERY_RESULT,
             sets="const d = b.Results[0].EsDocs[0];\npm.collectionVariables.set('collectionId', encodeURIComponent(d.CollectionId));",
             notes="Sets `collectionId` for API-07 / API-08."),
        dict(name="Search Collections (advanced QueryCondition form from spec sample)", method="POST", path="/platform/bcp-core/query/v1/queryEsData",
             mand=dict(body={"Module": "Collection", "QueryCondition": {}}),
             full=dict(body={"QueryCondition": {"fuzzyConditions": {"ReceiptNo": "2024"}, "orSearchConditionsList": [
                 {"Conditions": {"CollectionStatus": "1"}},
                 {"gteRangeConditions": {"ReceiveTime": "2023-04-30"}, "lteRangeConditions": {"ReceiveTime": "2024-06-09"}},
                 {"gteRangeConditions": {"Amount": "1000"}, "lteRangeConditions": {"Amount": "2000"}}]},
                 "PageNo": 1, "PageSize": 10, "SortField": "index_time", "SortType": "desc", "Module": "Collection"}),
             examples=[("200 OK (spec sample)", 200, "OK", {"GroupField": "entity_type", "PageNo": 1, "PageSize": 10, "Total": 1, "Results": [{"GroupValue": "Collection", "GroupTotalNum": 1, "EsDocs": [COLLECTION_ESDOC]}]})],
             checks=QUERY_RESULT,
             notes=("**STRUCTURE MISMATCH IN SPEC:** the sample request wraps filters in `QueryCondition` with camelCase keys "
                    "(`fuzzyConditions`, `orSearchConditionsList`, `gteRangeConditions`, `lteRangeConditions`), but the request "
                    "table documents a flat SearchCondition (`FuzzyConditions`, `OrConditionsList`, `FromRangeConditions`, "
                    "`ToRangeConditions`). Both forms are included so the tenant can confirm which one the API accepts.")),
    ],
))

# ---- API-07 / API-08 -----------------------------------------------------
COLL_Q = [q("collectionId", "{{collectionId}}", "Signed CollectionId from API-06, comma URL-encoded as %2C")]
APIS.append(dict(
    id="API-07", title="Float Statement - Load Collection (Current Balance) API", owner="EasyBCP Apps Team",
    endpoint="GET /platform/bcp-core/collection/v1/getCollection",
    requests=[dict(name="Load Collection (current balance)", method="GET", path="/platform/bcp-core/collection/v1/getCollection",
                   mand=dict(query=COLL_Q), full=dict(query=COLL_Q),
                   examples=[("200 OK - prepayment (spec sample)", 200, "OK", {"@type": "BcpCollection-Collection", "Amount": 1004.4, "Balance": 1004.4, "BankAccountNo": "", "BankCode": "", "BizTransId": "969XXXXX54,B4FXXXXX6C76AXXXXXBD3F6A080XXXXX", "BookingCurrencyCode": "BRL", "BranchCode": "10002", "ChequeNo": "", "CollectionId": "969XXXXX56,13XXXXXB518A0DXXXXX43F84D58XXXXX", "CollectionStatus": "1", "CollectionType": "1", "CurrencyCode": "BRL", "DetailList": [{"@type": "BcpCollectionDetail-CollectionDetail", "Amount": 1004.4, "CurrencyCode": "BRL", "IsExpense": "N", "RefId": "969XXXXX58,97BXXXXXAC2FXXXXX0B2A2E6AB4XXXXX", "RefType": "2"}], "DirectBookingEr": 1, "DirectEr": 1, "HasMandate": "N", "HasNote": "N"})],
                   checks=[("Balance present", "'Balance' in b"), ("CollectionId present", "'CollectionId' in b")])],
))
APIS.append(dict(
    id="API-08", title="Float Statement - Collection Transaction History API", owner="EasyBCP Apps Team",
    endpoint="GET /platform/bcp-core/collection/v1/getCollectionTransHis",
    requests=[dict(name="Collection Transaction History", method="GET", path="/platform/bcp-core/collection/v1/getCollectionTransHis",
                   mand=dict(query=COLL_Q), full=dict(query=COLL_Q),
                   examples=[("200 OK (spec sample)", 200, "OK", [{"TransactionNo": "OFS20231200000030", "TransactionStatus": "1", "ApplicationDate": "2023-12-20T14:52:54", "Amount": 1004.4, "CurrencyCode": "BRL", "BranchCode": "10006", "ArapId": 9699392278, "ArapNo": "DR20231200002668", "ArapType": "-1001", "HasNote": "N", "Operator": 10000001178005, "Arap": {"ArapNo": "DR20231200002668", "ArapCate": "1", "ArapStatus": "2", "ArapType": "-1001", "Amount": 1004.4, "Balance": 0, "Commission": 93, "CurrencyCode": "BRL", "DueDate": "2023-12-21", "PayerPayeeName": "PolicyCollection", "PaymentMethod": "100", "CurrentPeriod": 1, "TotalPeriods": 1}}])],
                   checks=IS_ARRAY)],
))

# ---- API-09 --------------------------------------------------------------
APIS.append(dict(
    id="API-09", title="Query Commission API", owner="EasyBCP Apps Team",
    endpoint="POST /platform/saleschannel/commission/queryCommission",
    requests=[dict(name="Query Commission", method="POST", path="/platform/saleschannel/commission/queryCommission",
                   mand=dict(body={"Module": "SalesCommission"}),
                   full=dict(body={
                       "Module": "SalesCommission", "PageNo": 1, "PageSize": 20,
                       "Conditions": {"CommissionStatus": "2", "PolicyNo": "{{PolicyNo}}"},
                       "FuzzyConditions": {"ChannelCode": "PTY"}, "InConditions": {"CommissionType": ["1"]},
                       "NotInConditions": {"CommissionStatus": ["4"]},
                       "FromRangeConditions": {"CommissionGenerateDate": "2026-01-01"}, "ToRangeConditions": {"CommissionGenerateDate": "2026-12-31"},
                       "ExistFields": ["PolicyNo"], "NotExistFields": ["SettlementId"],
                       "OrConditions": {"ProductCode": "TBTI"}, "OrConditionsList": [{"CommissionStatus": "2"}, {"CommissionStatus": "4"}],
                       "OrFuzzyConditions": {"PolicyNo": "PO"}, "OrFuzzyConditionsList": [{"TransNo": "T"}],
                       "OrInConditions": {"BranchCode": ["10002", "10006"]},
                       "SortField": "index_time", "SortType": "desc", "SortFieldAndTypeList": [{"SortField": "CommissionGenerateDate", "SortType": "desc"}],
                       "AggConditions": {"SumFields": ["Amount"]}, "GroupField": "entity_type",
                       "IncludeFields": ["CommissionNo", "Amount", "CommissionStatus", "PolicyNo"]}),
                   examples=[("200 OK (spec sample)", 200, "OK", {"ElementsInCurrentPage": [{"CommissionId": 9699392290, "CommissionNo": "COM20231200000021", "CommissionType": "1", "CommissionStatus": "2", "CommissionGenerateDate": "2023-12-20T11:49:38", "Amount": 93.00, "Balance": 93.00, "CurrencyCode": "BRL", "FeeType": "100600", "ChannelCode": "PTY10000052462004", "ChannelName": "TEST0926", "ChannelType": "14", "AgreementCode": "AGR-2026-001", "PayeeCode": "PTY10000052462004", "PolicyNo": "POTBTI01226628", "PolicyEffectiveDate": "2023-12-21T00:00:00", "ProductCode": "TBTI", "ProductLineCode": "Travel", "TransType": "NEWBIZ", "BranchCode": "10006"}], "NumberOfElementsInCurrentPage": 1, "PageQuery": {"PageNumber": 1, "PageSize": 20}, "TotalElements": 1, "TotalPages": 1})],
                   checks=PAGED,
                   notes="Request is a SearchCondition (PageNo/PageSize) but the response is a PagedResult (ElementsInCurrentPage / PageQuery.PageNumber) - different paging conventions in one API.")],
))

# ---- API-10 / API-11 -----------------------------------------------------
DT_SAMPLE = [{"BusinessDataTable": {"DataTableId": 532288534, "Name": "{{ProductListTable}}", "Description": "Products under a product code", "IsSmall": "Y", "Fields": {"ProductCode": {"Name": "ProductCode", "DataType": -4, "IsPrimaryKey": "Y", "Sequence": 0}, "SubProductCode": {"Name": "SubProductCode", "DataType": -4, "Sequence": 1}, "SubProductName": {"Name": "SubProductName", "DataType": -4, "Sequence": 2}}}, "Records": [{"RecordId": 1, "DataTableId": 532288534, "ProductCode": "1001", "SubProductCode": "1001-A", "SubProductName": "Plan A"}, {"RecordId": 2, "DataTableId": 532288534, "ProductCode": "1001", "SubProductCode": "1001-B", "SubProductName": "Plan B"}]}]
APIS.append(dict(
    id="API-10", title="Datatable Lookup by Name List API", owner="EasyPA Apps Team",
    endpoint="POST /platform/dd/public/datatable/v1/dataTableVoList/byNameList",
    requests=[dict(name="Datatable Lookup by Name List", method="POST", path="/platform/dd/public/datatable/v1/dataTableVoList/byNameList",
                   mand=dict(body=[{"DataTableName": "{{ProductListTable}}"}]),
                   full=dict(body=[{"DataTableName": "{{ProductListTable}}", "ConditionMap": {"ProductCode": "1001"}},
                                   {"DataTableName": "{{ProductListTable}}", "ConditionMap": {"ProductCode": "1005"}}]),
                   examples=[("200 OK (spec sample)", 200, "OK", DT_SAMPLE)],
                   checks=IS_ARRAY + [("[0].BusinessDataTable present", "b.length === 0 || 'BusinessDataTable' in b[0]"), ("[0].Records is array", "b.length === 0 || Array.isArray(b[0].Records)")],
                   notes="`{{ProductListTable}}` is a placeholder: the Config/Apps team has not yet named the Load Product / Load Plan data tables.")],
))
APIS.append(dict(
    id="API-11", title="Ratetable Lookup API", owner="EasyPA Apps Team",
    endpoint="POST /platform/ratetable/rate/v1/lookup?code=&version=",
    requests=[dict(name="Ratetable Lookup", method="POST", path="/platform/ratetable/rate/v1/lookup",
                   mand=dict(query=[q("code", "{{PackageTable}}", "Rate / configuration table code")], body={}),
                   full=dict(query=[q("code", "{{PackageTable}}", "Rate / configuration table code"), q("version", "1", "Table version number")], body={"ProductCode": "1001"}),
                   examples=[("200 OK (spec sample)", 200, "OK", [{"ProductCode": "1001", "PackageCode": "TP", "PackageName": "Third Party"}, {"ProductCode": "1001", "PackageCode": "SILVER", "PackageName": "Silver"}, {"ProductCode": "1001", "PackageCode": "GOLD", "PackageName": "Gold"}, {"ProductCode": "1001", "PackageCode": "PLATINUM", "PackageName": "Platinum"}])],
                   checks=IS_ARRAY,
                   notes=("`{{PackageTable}}` is a placeholder (table not yet created).\n"
                          "Spec ambiguity: `conditions` is listed both as a query Map and as the JSON body. This collection sends conditions in the body."))],
))

# ---- API-12 --------------------------------------------------------------
APIS.append(dict(
    id="API-12", title="Product Schema API", owner="EasyPA Apps Team",
    endpoint="GET /platform/product/prd/v1/productSchema",
    requests=[dict(name="Product Schema", method="GET", path="/platform/product/prd/v1/productSchema",
                   mand=dict(query=[q("productCode", "{{productCode}}"), q("versionDate", "{{versionDate}}", "YYYY-MM-DDTHH:MM:SS")]),
                   full=dict(query=[q("productCode", "{{productCode}}"), q("versionDate", "{{versionDate}}", "YYYY-MM-DDTHH:MM:SS"), q("withCodeDesc", "Y"), q("withI18n", "Y")]),
                   examples=[("200 OK - TBTI (spec sample, abridged)", 200, "OK", {"ProductId": 351925022, "BusinessCode": "TBTI", "ProductName": "Oversea Travel", "ProductVersion": "1.0", "EffectiveDate": "2019-01-01T00:00:00", "ExpireDate": "9999-12-31T23:59:59", "EffectiveFlag": "Y", "ProductMaster": {"ProductCode": "TBTI", "ProductName": "Oversea Travel", "PolicyType": "1", "IsPackage": "N"}, "ChildProductTreeNodeList": [{"ProductElementCode": "TBTI", "ProductElementName": "Oversea Travel", "ChildProductTreeNodeList": [{"ProductElementCode": "R10007", "ProductElementName": "Insured Person", "ChildProductTreeNodeList": [{"ProductElementCode": "C100416", "ProductElementName": "Accident Death & Dismemberment", "IsRequired": "Y"}]}]}]})],
                   checks=[("ChildProductTreeNodeList is array", "Array.isArray(b.ChildProductTreeNodeList)"), ("BusinessCode present", "'BusinessCode' in b")])],
))

# ---- Policy samples reused by API-13 / API-21 ----------------------------
QUOTE_SAMPLE = {"PolicyId": "10387340006,3F8601E69CC9ECFAB363EACE899108F4", "QuotationNo": "Q2026000000123", "ProposalStatus": "10", "ProposalStatus_CodeDesc": "Quotation In Progress", "PolicyType": "1", "ProductCode": "PRD001", "ProductVersion": "1.0", "EffectiveDate": "2026-10-01", "ExpiryDate": "2027-09-30", "ApplyDate": "2026-09-28", "BranchId": 1,
                "PolicyCustomerList": [{"CustomerName": "John Smith", "IsPolicyHolder": "Y", "IsInsured": "Y", "IdType": "1", "IdNo": "A1234567", "DateOfBirth": "1985-04-12", "GenderCode": "M", "Mobile": "+10000000000", "Email": "john.smith@example.com"}],
                "PolicyLobList": [{"ProductCode": "PRD001", "SumInsured": 100000, "GrossPremium": 1200, "BeforeVatPremium": 1200, "Vat": 60, "DuePremium": 1260, "PolicyRiskList": [{"RiskName": "Risk 1", "SumInsured": 100000, "GrossPremium": 1200, "PolicyCoverageList": [{"ProductElementCode": "C001", "SumInsured": 100000, "GrossPremium": 1200}]}]}],
                "PolicyPaymentInfoList": [{"PayModeCode": "100", "IsInstallment": "N"}]}
POLICY_SAMPLE = {"AgentCode": "XXXXX0000524XXXXX", "BusinessCateCode": "1", "BusinessCateCode_CodeDesc": "Direct issuance", "DuePremium": 680.4, "EffectiveDate": "2021-04-22", "ExpiryDate": "2022-04-21T23:59:59", "IssueDate": "2024-01-30T15:08:48", "OrgCode": "10002", "PolicyId": "9943000003,A15FCE5FDF40DAB310514CDC4F565C42",
                 "PolicyLobList": [{"PolicyRiskList": [{"CustomerName": "Customer", "DateOfBirth": "1988-10-01", "IdType": "1", "PolicyCoverageList": [{"CoverageName": "Accident Death & Dismemberment", "PolicyStatus": 2, "PolicyStatus_CodeDesc": "Effective", "ProductElementCode": "C100416", "SumInsured": 300000}], "ProductElementCode": "R10007", "SumInsured": 900000}], "ProductElementCode": "TBTI"}],
                 "ProductCode": "TBTI", "ProposalNo": "PABTBTI0001300189", "ProposalStatus": "3", "ProposalStatus_CodeDesc": "Issued", "SumInsured": 900000}

APIS.append(dict(
    id="API-13", title="Load Quote Details API", owner="EasyPA Apps Team",
    endpoint="GET /platform/quotation/core/quotation/v1/load",
    requests=[dict(name="Load Quote Details", method="GET", path="/platform/quotation/core/quotation/v1/load",
                   mand=dict(query=[q("policyId", "{{quotePolicyId}}", "Signed PolicyId from API-17, comma URL-encoded")]),
                   full=dict(query=[q("policyId", "{{quotePolicyId}}", "Signed PolicyId from API-17, comma URL-encoded"), q("withCodeDesc", "Y", "Adds <field>_CodeDesc")]),
                   examples=[("200 OK (spec sample)", 200, "OK", QUOTE_SAMPLE)],
                   checks=[("PolicyId present", "'PolicyId' in b")])],
))

# ---- API-14 / API-23 (same endpoint) -------------------------------------
QF_MAND = {"BusinessType": "{{businessType}}", "BusinessNo": "{{businessNo}}"}
APIS.append(dict(
    id="API-14", title="Fetch Document API", owner="EasyPA Apps Team / iDocs Team",
    endpoint="POST /platform/attachment-core/attachment/v1/queryFile",
    requests=[dict(name="Fetch Document", method="POST", path="/platform/attachment-core/attachment/v1/queryFile",
                   mand=dict(body=QF_MAND), full=dict(body={**QF_MAND, "DirectoryList": [], "OperateFileIds": []}),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": [{"FileId": 0, "FileName": "string", "Directory": "string", "BusinessType": "string", "BusinessNo": "string"}]})],
                   checks=ENVELOPE_ATT,
                   sets="const m = Array.isArray(b.Model) ? b.Model[0] : null;\nif (m && (m.FileId || m.AttachFileId)) pm.collectionVariables.set('attachFileId', m.FileId || m.AttachFileId);",
                   notes="Model file field names are not confirmed in the spec (FileId assumed). Sets `attachFileId` for API-24 / API-27.")],
))
APIS.append(dict(
    id="API-23", title="Query Files with Metadata API", owner="iDocs Team",
    endpoint="POST /platform/attachment-core/attachment/v1/queryFile",
    requests=[dict(name="Query Files with Metadata", method="POST", path="/platform/attachment-core/attachment/v1/queryFile",
                   mand=dict(body=QF_MAND), full=dict(body={**QF_MAND, "DirectoryList": ["{{directory}}"], "OperateFileIds": []}),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": [{"FileId": 0, "FileName": "invoice.pdf", "Directory": "string", "Metadata": {"InvoiceNo": "INV-001", "InvoiceDate": "2026-09-01"}}]})],
                   checks=ENVELOPE_ATT,
                   notes="Same endpoint and request as API-14. Metadata shape per file is not confirmed in the spec.")],
))

# ---- API-15 / API-16 / API-34 (Notifications Hub) ------------------------
HUB_NOTE = ("**STRUCTURE NOT WORKING:** `/comm/v1/notifications/send` returns HTTP 404 on the trialx gateway "
            "(also tried `/platform/comm/v1/notifications/send`), and the spec has no request contract for it - "
            "the body below is a placeholder until the Notifications Hub team publishes one. "
            "The documented InsureMO SNS alternative is in the next request and is routed on trialx.")
APIS.append(dict(
    id="API-15", title="Email Quote API", owner="Notifications Hub Team",
    endpoint="POST /comm/v1/notifications/send (404 on trialx) · alt POST /mo-fo/1.0/sns/email/send",
    requests=[
        dict(name="Email Quote via Notifications Hub (contract TBC - 404 on trialx)", method="POST", path="/comm/v1/notifications/send",
             mand=dict(body={"Channel": "EMAIL", "Recipient": "{{customerEmail}}", "TemplateCode": "QUOTE_EMAIL", "TemplateParams": {"quotationNo": "{{quotationNo}}"}}),
             full=dict(body={"Channel": "EMAIL", "Recipient": "{{customerEmail}}", "TemplateCode": "QUOTE_EMAIL", "TemplateParams": {"customerName": "John Smith", "quotationNo": "{{quotationNo}}"}, "Attachments": [{"content": "<base64>", "content_id": "quote.pdf", "mime_type": "application/pdf"}]}),
             examples=[GATEWAY_404], checks=[("body is JSON", "true")], notes=HUB_NOTE),
        dict(name="Email Quote via SNS Email Service (documented alternative)", method="POST", path="/mo-fo/1.0/sns/email/send",
             mand=dict(body={"account_name": "{{emailAccount}}", "to": ["{{customerEmail}}"], "template_code": "QUOTE_EMAIL", "template_params": {"quotationNo": "{{quotationNo}}"}}),
             full=dict(body={"account_name": "{{emailAccount}}", "alias": "Quotations", "to": ["{{customerEmail}}"], "cc": [], "bcc": [], "subject": "Your quotation {{quotationNo}}", "template_code": "QUOTE_EMAIL", "template_params": {"customerName": "John Smith", "quotationNo": "{{quotationNo}}"}, "attachments": [{"content": "<base64>", "content_id": "quote.pdf", "headers": {}, "mime_type": "application/pdf"}], "reply_to": "noreply@example.com", "priority": 3, "auto_format_html": True, "custom_headers": {}, "sender_params": {}}),
             examples=[("200 OK (spec structure)", 200, "OK", {"code": "string", "message": "string", "trace_id": "string", "data": {"message_id": "string"}})],
             checks=ENVELOPE_SNS,
             notes="Mandatory: account_name, to, and either content+content_type or template_code (+template_params). This request uses the template option."),
    ],
))
APIS.append(dict(
    id="API-16", title="SMS Quote API", owner="Notifications Hub Team",
    endpoint="POST /comm/v1/notifications/send (404 on trialx) · alt POST /mo-fo/1.0/sns/sms/send",
    requests=[
        dict(name="SMS Quote via Notifications Hub (contract TBC - 404 on trialx)", method="POST", path="/comm/v1/notifications/send",
             mand=dict(body={"Channel": "SMS", "Recipient": "{{mobileNo}}", "TemplateCode": "QUOTE_SMS", "TemplateParams": {"quotationNo": "{{quotationNo}}"}}),
             full=dict(body={"Channel": "SMS", "Recipient": "{{mobileNo}}", "TemplateCode": "QUOTE_SMS", "TemplateParams": {"customerName": "John Smith", "quotationNo": "{{quotationNo}}", "premium": "1260.00"}}),
             examples=[GATEWAY_404], checks=[("body is JSON", "true")], notes=HUB_NOTE),
        dict(name="SMS Quote via SNS SMS Service (documented alternative)", method="POST", path="/mo-fo/1.0/sns/sms/send",
             mand=dict(body={"to": "{{mobileNo}}", "account_name": "{{smsAccount}}", "sign_name": "{{signName}}", "template_code": "QUOTE_SMS"}),
             full=dict(body={"to": "{{mobileNo}}", "account_name": "{{smsAccount}}", "sign_name": "{{signName}}", "template_code": "QUOTE_SMS", "template_params": {"customerName": "John Smith", "quotationNo": "{{quotationNo}}", "premium": "1260.00"}}),
             examples=[("200 OK (spec structure)", 200, "OK", {"code": "string", "message": "string", "trace_id": "string", "data": {"message_id": "string", "content_length": 0}})],
             checks=ENVELOPE_SNS),
    ],
))

# ---- API-17 --------------------------------------------------------------
APIS.append(dict(
    id="API-17", title="Quotation Query API", owner="EasyPA Apps Team",
    endpoint="POST /platform/quotation/core/quotation/v1/query",
    requests=[dict(name="Quotation Query", method="POST", path="/platform/quotation/core/quotation/v1/query",
                   mand=dict(body={}),
                   full=dict(body={"QuotationNo": "{{quotationNo}}", "ProductCode": "TBTI", "TechProductCode": "TR_POC", "AgentCode": "{{agentCode}}", "CustomerName": "Apitest202111", "CustomerNo": "{{customerNo}}", "IsSubmitted": "N", "QuotationDateStart": "2024-02-22", "QuotationDateEnd": "2026-12-31", "EffectiveDateStart": "2024-01-01", "EffectiveDateEnd": "2026-12-31", "DuePremiumStart": 0, "DuePremiumEnd": 100000, "DynamicProperties": {"Test005": "Test0051", "Test006": "Test0061"}, "PageNumber": 1, "PageSize": 5, "Orders": [{"FieldName": "QuotationDate", "Ascending": False}]}),
                   examples=[("200 OK (spec sample, abridged)", 200, "OK", {"ElementsInCurrentPage": [{"AgentCode": "XXXXX0000545XXXXX", "BookCurrencyCode": "USD", "BusinessCateCode": "1", "CustomerName": "Apitest202111", "EffectiveDate": "2024-04-22", "ExpiryDate": "2025-04-21T23:59:59", "IsSubmitted": "N", "LocalCurrencyCode": "USD", "OrgCode": "10002", "PolicyId": "10387340006,3F8601E69CC9ECFAB363EACE899108F4", "PolicyStatus": 1, "PolicyType": "1", "PremiumCurrencyCode": "USD", "ProductCode": "TBTI", "ProductVersion": "1.0", "ProposalDate": "2024-04-22", "ProposalStatus": "5", "QuotationDate": "2024-04-28T11:32:55", "QuotationId": 10387340006, "QuotationNo": "QTBTI000001790113", "TechProductCode": "TR_POC"}], "NumberOfElementsInCurrentPage": 4, "PageQuery": {"PageNumber": 1, "PageSize": 5, "ProductCode": "TBTI", "IsSubmitted": "N"}, "TotalElements": 4, "TotalPages": 1})],
                   checks=PAGED,
                   sets="const d = b.ElementsInCurrentPage[0];\npm.collectionVariables.set('quotePolicyId', encodeURIComponent(d.PolicyId));\npm.collectionVariables.set('quotationNo', d.QuotationNo);",
                   notes=("Every field is optional, so the Mandatory variant sends `{}`.\n"
                          "Spec inconsistency: sample request sends `PageNumber: 0` but the response echoes `PageNumber: 1` - confirm whether paging is 0- or 1-based. Sets `quotePolicyId` for API-13."))],
))

# ---- API-18 / API-19 -----------------------------------------------------
CUST_ADDR = {"AddressId": 300000001, "AddressType": "1", "IsPrimaryAddress": "Y", "AddressLine1": "10 Main Street", "City": "Springfield", "CountryCode": "USA", "PostCode": "12345"}
APIS.append(dict(
    id="API-18", title="Load Individual Customer API", owner="EasyPA Apps Team",
    endpoint="GET /platform/custv2/core/customer/indi/byCustomerId",
    requests=[dict(name="Load Individual Customer", method="GET", path="/platform/custv2/core/customer/indi/byCustomerId",
                   mand=dict(query=[q("customerId", "{{indiCustomerId}}")]), full=dict(query=[q("customerId", "{{indiCustomerId}}")]),
                   examples=[("200 OK (spec sample)", 200, "OK", {"CustomerId": 200000123, "CustomerNumber": "C000000123", "CustomerType": "1", "CustomerStatus": "1", "FirstName": "John", "LastName": "Smith", "FullName": "John Smith", "Gender": "M", "DateOfBirth": "1985-04-12", "IdType": "1", "IdNumber": "A1234567", "NationalityCode": "USA", "MaritalStatus": "2", "OccupationCode": "0001", "IsPep": "N", "PartyAddressList": [CUST_ADDR], "PartyContactList": [{"ContactId": 400000001, "IsPrimaryContact": "Y", "Email": "john.smith@example.com", "HomeTel": "+10000000000"}], "PartyAccountList": [{"AccountId": 500000001, "IsPrimaryAccount": "Y", "BankCode": "B001", "AccountNo": "0000123456", "AccountHolderName": "John Smith"}]})],
                   checks=[("CustomerId present", "'CustomerId' in b")],
                   notes="customerId is typed Long in the spec; there is no customer search API in the list to obtain it, and it may be a signed field at the gateway (to confirm).")],
))
APIS.append(dict(
    id="API-19", title="Load Organisation Customer API", owner="EasyPA Apps Team",
    endpoint="GET /platform/custv2/core/customer/org/byCustomerId",
    requests=[dict(name="Load Organisation Customer", method="GET", path="/platform/custv2/core/customer/org/byCustomerId",
                   mand=dict(query=[q("customerId", "{{orgCustomerId}}")]), full=dict(query=[q("customerId", "{{orgCustomerId}}")]),
                   examples=[("200 OK (spec sample)", 200, "OK", {"CustomerId": 200000456, "CustomerNumber": "C000000456", "CustomerType": "2", "CustomerStatus": "1", "RegistrationName": "Example Trading Ltd", "DateOfRegistration": "2010-06-01", "IdType": "9", "IdNumber": "REG-0012345", "OrgType": "1", "LegalStatus": "1", "IndustryCategory": "RETAIL", "IsPep": "N", "PartyAddressList": [{**CUST_ADDR, "AddressId": 300000002, "AddressType": "2", "AddressLine1": "1 Commerce Park"}], "PartyContactList": [{"ContactId": 400000002, "ContactName": "Jane Doe", "IsPrimaryContact": "Y", "Email": "jane.doe@example.com", "BusinessTel": "+10000000001"}], "PartyAccountList": [{"AccountId": 500000002, "IsPrimaryAccount": "Y", "BankCode": "B001", "AccountNo": "0000987654", "AccountHolderName": "Example Trading Ltd"}]})],
                   checks=[("CustomerId present", "'CustomerId' in b")])],
))

# ---- API-20 --------------------------------------------------------------
POLICY_Q_SAMPLE = {"GroupField": "entity_type", "PageNo": 1, "PageSize": 100, "Results": [{"EsDocs": [{"AgentCode": "XXXXX0000524XXXXX", "DuePremium": 38.52, "EffectiveDate": "2024-01-04", "ExpiryDate": "2024-01-18", "IdNo": "106290*******0629", "IdType": "1", "InsuredName": "InsuredName", "IssueDate": "2024-01-11T10:41:09", "OrgCode": "10002", "PolicyHolder": "Customer", "PolicyId": "9854370003,64F246781A66A74A4DA130CAF3720145", "PolicyNo": "POTBTI01229164", "PolicyStatus": 2, "ProductCode": "TBTI", "ProductName": "Oversea Travel (PBU for Auto Test)", "ProposalNo": "PABTBTI0001298154", "ProposalStatus": 3, "SumInsured": 900000}], "GroupTotalNum": 1, "GroupValue": "Policy"}], "Total": 1}
POLICY_Q_FULL = {"Module": "Policy", "Conditions": {"ProductCode": "TBTI", "PolicyNo": "{{PolicyNo}}"}, "FuzzyConditions": {"PolicyHolder": "Cust"}, "InConditions": {"PolicyStatus": [1, 2]}, "NotInConditions": {"ProposalStatus": [4]}, "FromRangeConditions": {"EffectiveDate": "2024-01-01"}, "ToRangeConditions": {"EffectiveDate": "2024-12-31"}, "OrConditions": {"OrgCode": "10002"}, "OrConditionsList": [{"ProposalStatus": 3}, {"ProposalStatus": 6}], "OrFuzzyConditions": {"InsuredName": "Insured"}, "OrFuzzyConditionsList": [{"PolicyNo": "PO"}], "OrInConditions": {"ProductCode": ["TBTI"]}, "ExistFields": ["PolicyNo"], "NotExistFields": ["MasterPolicyNo"], "IncludeFields": ["PolicyId", "PolicyNo", "ProposalNo", "ProposalStatus", "PolicyStatus", "DuePremium"], "AggConditions": {"SumFields": ["DuePremium"], "AvgFields": ["DuePremium"], "GroupFields": ["ProductCode"]}, "GroupField": "entity_type", "SortField": "index_time", "SortType": "desc", "SortFieldAndTypeList": [{"SortField": "EffectiveDate", "SortType": "desc"}], "PageNo": 1, "PageSize": 100}
POLICY_SETS = ("const d = b.Results[0].EsDocs[0];\npm.collectionVariables.set('policyId', encodeURIComponent(d.PolicyId));\n"
               "pm.collectionVariables.set('PolicyNo', d.PolicyNo || d.ProposalNo);")
APIS.append(dict(
    id="API-20", title="Proposal and Policy Query API", owner="EasyPA Apps Team",
    endpoint="POST /platform/proposal/v1/query (portal list) · documented /proposal/core/proposal/v1/query",
    requests=[
        dict(name="Proposal and Policy Query (portal list path)", method="POST", path="/platform/proposal/v1/query",
             mand=dict(body={"Module": "Policy"}), full=dict(body=POLICY_Q_FULL),
             examples=[("200 OK (spec sample)", 200, "OK", POLICY_Q_SAMPLE)], checks=QUERY_RESULT, sets=POLICY_SETS,
             notes="Sets `policyId` and `PolicyNo` for API-21 / API-32 / API-14 / API-28."),
        dict(name="Proposal and Policy Query (documented core path)", method="POST", path="/platform/proposal/core/proposal/v1/query",
             mand=dict(body={"Module": "Policy"}), full=dict(body=POLICY_Q_FULL),
             examples=[("200 OK (spec sample)", 200, "OK", POLICY_Q_SAMPLE)], checks=QUERY_RESULT, sets=POLICY_SETS,
             notes="Spec lists three paths for this API (portal `/proposal/v1/query`, guide `/proposal/core/proposal/v1/query`, SDK `/proposal/v1/queryPolicy`). Both routed paths are included so the tenant can confirm which returns the documented QueryResult."),
    ],
))

# ---- API-21 --------------------------------------------------------------
APIS.append(dict(
    id="API-21", title="Load Proposal or Policy API", owner="EasyPA Apps Team",
    endpoint="GET /platform/proposal/core/proposal/v1/load",
    requests=[dict(name="Load Proposal or Policy", method="GET", path="/platform/proposal/core/proposal/v1/load",
                   mand=dict(query=[q("policyId", "{{policyId}}", "Signed PolicyId from API-20, comma URL-encoded")]),
                   full=dict(query=[q("policyId", "{{policyId}}", "Signed PolicyId from API-20, comma URL-encoded"), q("withCodeDesc", "Y", "Adds <field>_CodeDesc")]),
                   examples=[("200 OK (spec sample, abridged)", 200, "OK", POLICY_SAMPLE)],
                   checks=[("PolicyId present", "'PolicyId' in b"), ("PolicyLobList is array", "Array.isArray(b.PolicyLobList)")],
                   notes="Response also carries TempData with masked values - do not display it.")],
))

# ---- API-22 --------------------------------------------------------------
def fd(key, value, ftype="text", desc_="", disabled=False):
    d = {"key": key, "type": ftype}
    if ftype == "file":
        d["src"] = value
    else:
        d["value"] = value
    if desc_:
        d["description"] = desc_
    if disabled:
        d["disabled"] = True
    return d


APIS.append(dict(
    id="API-22", title="Upload Document API", owner="iDocs Team",
    endpoint="POST /platform/attachment-core/attachment/v1/uploadMulti (multipart/form-data)",
    requests=[dict(name="Upload Document (multipart)", method="POST", path="/platform/attachment-core/attachment/v1/uploadMulti",
                   mand=dict(formdata=[fd("files", [], "file", "Pick a file (.pdf .jpg .png .docx .xlsx ...; max 50 MB)"), fd("businessType", "{{businessType}}"), fd("businessNo", "{{businessNo}}")]),
                   full=dict(formdata=[fd("files", [], "file", "Pick a file"), fd("files", [], "file", "Second file (repeatable)"), fd("businessType", "{{businessType}}"), fd("businessNo", "{{businessNo}}"), fd("directory", "{{directory}}", desc_="Lowest-level node from API-25"), fd("metadata", "{\"DocumentDate\":\"2026-09-28\"}"), fd("productCode", "{{productCode}}"), fd("productLine", "{{productLine}}"), fd("receivedDate", "2026-09-28T10:00:00"), fd("groupList", "GROUP1")]),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": [{"FileId": 0, "FileName": "id-proof.pdf", "Directory": "string"}, {"FileId": 0, "FileName": "photo.jpg", "Directory": "string"}]})],
                   checks=ENVELOPE_ATT,
                   notes="Postman sets the multipart Content-Type + boundary itself; do not add it by hand. Select the files before sending.")],
))

# ---- API-24 --------------------------------------------------------------
APIS.append(dict(
    id="API-24", title="Download Document API", owner="iDocs Team",
    endpoint="GET /platform/attachment-core/attachment/v1/downloadFile",
    requests=[dict(name="Download Document", method="GET", path="/platform/attachment-core/attachment/v1/downloadFile",
                   mand=dict(query=[q("attachFileId", "{{attachFileId}}")]), full=dict(query=[q("attachFileId", "{{attachFileId}}")]),
                   examples=[("200 OK - file stream", 200, "OK", "<binary file content>", [{"key": "Content-Type", "value": "application/octet-stream"}, {"key": "Content-Disposition", "value": "attachment;filename=document.pdf"}]),
                             ("204 No Content - empty file", 204, "No Content", "", [])],
                   checks=[],
                   custom_tests=("const code = pm.response.code;\n"
                                 "pm.test('API-24 route exists (not 404)', () => pm.expect(code).to.not.eql(404));\n"
                                 "pm.test('API-24 permitted (not 401/403)', () => pm.expect([401, 403]).to.not.include(code));\n"
                                 "pm.test('API-24 200 file or 204 empty', () => pm.expect([200, 204]).to.include(code));\n"
                                 "pm.test('API-24 structure: octet-stream / attachment header', () => { if (code === 200) pm.expect(pm.response.headers.get('Content-Disposition') || '').to.include('attachment'); });"),
                   notes="Use Postman's *Send and Download*. HTTP 204 = empty file.")],
))

# ---- API-25 / API-26 / API-27 --------------------------------------------
APIS.append(dict(
    id="API-25", title="Document Type Tree API", owner="iDocs Team",
    endpoint="POST /platform/attachment-core/attachment/v1/getTreeData",
    requests=[dict(name="Document Type Tree", method="POST", path="/platform/attachment-core/attachment/v1/getTreeData",
                   mand=dict(body=QF_MAND), full=dict(body={**QF_MAND, "Context": {"ProductCode": "{{productCode}}"}}),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": [{"Code": "CLAIM_DOCS", "Name": "Claim Documents", "Children": [{"Code": "PHOTO", "Name": "Damage Photos", "Children": []}, {"Code": "INVOICE", "Name": "Repair Invoice", "Children": []}]}]})],
                   checks=ENVELOPE_ATT, notes="Tree node field names are not confirmed in the spec.")],
))
APIS.append(dict(
    id="API-26", title="Document Checklist by Business Info API", owner="iDocs Team",
    endpoint="GET /platform/attachment-core/checklist/v1/loadByBusinessInfoWithPathDetail",
    requests=[dict(name="Document Checklist by Business Info", method="GET", path="/platform/attachment-core/checklist/v1/loadByBusinessInfoWithPathDetail",
                   mand=dict(query=[q("businessType", "{{businessType}}"), q("businessNo", "{{businessNo}}")]),
                   full=dict(query=[q("businessType", "{{businessType}}"), q("businessNo", "{{businessNo}}")]),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": [{"DocumentType": "PHOTO", "Path": "Claim Documents/Damage Photos", "Status": "Received"}, {"DocumentType": "INVOICE", "Path": "Claim Documents/Repair Invoice", "Status": "Outstanding"}]})],
                   checks=ENVELOPE_ATT)],
))
APIS.append(dict(
    id="API-27", title="Load All Document Versions API", owner="iDocs Team",
    endpoint="GET /platform/attachment-core/attachment/version/v1/loadAllVersions",
    requests=[dict(name="Load All Document Versions", method="GET", path="/platform/attachment-core/attachment/version/v1/loadAllVersions",
                   mand=dict(query=[q("attachFileId", "{{attachFileId}}")]), full=dict(query=[q("attachFileId", "{{attachFileId}}")]),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": [{"FileId": 0, "Version": 2, "IsActive": "Y", "FileName": "invoice.pdf", "UploadTime": "2026-09-20T10:15:00"}, {"FileId": 0, "Version": 1, "IsActive": "N", "FileName": "invoice.pdf", "UploadTime": "2026-09-10T09:00:00"}]})],
                   checks=ENVELOPE_ATT)],
))

# ---- API-28 --------------------------------------------------------------
FNOL_CASE_FULL = {"PolicyNo": "{{PolicyNo}}", "ProductCode": "{{productCode}}", "ProductVersion": "1.0", "ProductLineCode": "{{productLine}}", "AccidentTime": "2026-09-27T14:30:00", "AccidentAddress": "10 Main Street, Springfield", "AccidentCountryCode": "USA", "AccidentRegionCode": "R01", "AccidentDesc": "Rear-end collision at traffic light", "LossCause": "{{lossCause}}", "ClaimType": "{{claimType}}", "FnolType": "{{fnolType}}", "ContactName": "John Smith", "ContactPhone": "+10000000000", "ContactEmail": "john.smith@example.com", "ContactType": "1", "HasOtherPolicies": "N", "IsFromApp": "N", "CurrencyCode": "USD"}
FNOL_RESP = {"Status": "OK", "Messages": [], "Model": {"CaseId": 0, "ClaimNo": "string", "FnolNo": "string", "CaseStatus": "string", "FnolStatus": "string", "PolicyNo": "string", "AccidentTime": "2026-09-27T14:30:00"}}
APIS.append(dict(
    id="API-28", title="Submit First Notification of Loss (FNOL) API", owner="EasyClaims Team",
    endpoint="POST /platform/api-orchestration/v1/flow/ECS_business_fnol",
    requests=[
        dict(name="Submit FNOL", method="POST", path="/platform/api-orchestration/v1/flow/ECS_business_fnol",
             mand=dict(body={"ClaimCase": {"PolicyNo": "{{PolicyNo}}", "AccidentTime": "2026-09-27T14:30:00"}}),
             full=dict(body={"ReportChannel": "{{reportChannel}}", "OperationType": "{{operationType}}", "IsManualPolicy": False, "ClaimNo": "", "TaskId": "", "MainExtendInfo": {"Name": "John Smith", "IdNumber": "A1234567", "GenderCode": "M", "RegistrationDate": "2026-09-27"}, "ThirdInsuranceList": [], "ClaimCase": FNOL_CASE_FULL}),
             examples=[("200 OK (spec structure)", 200, "OK", FNOL_RESP)], checks=ENVELOPE_ATT,
             sets="if (b.Model && b.Model.ClaimNo) pm.collectionVariables.set('claimNo', b.Model.ClaimNo);",
             notes="Creates data on trialx. OperationType / ReportChannel values and tenant-mandatory ClaimCase fields are open points in the spec."),
    ],
    full_only=[
        dict(name="Submit FNOL - manual policy (conditional ClaimPolicy)", method="POST", path="/platform/api-orchestration/v1/flow/ECS_business_fnol",
             full=dict(body={"ReportChannel": "{{reportChannel}}", "OperationType": "{{operationType}}", "IsManualPolicy": True,
                             "ClaimPolicy": {"PolicyNo": "{{PolicyNo}}", "ProductCode": "{{productCode}}", "ProductVersion": "1.0", "EffDate": "2026-01-01", "ExpDate": "2026-12-31", "SumInsured": 100000, "CurrencyCode": "USD", "PolicyHolderName": "John Smith", "InsuredName": "John Smith"},
                             "ClaimCase": FNOL_CASE_FULL}),
             examples=[("200 OK (spec structure)", 200, "OK", FNOL_RESP)], checks=ENVELOPE_ATT,
             notes="ClaimPolicy is required only when IsManualPolicy = true (policy not held in InsureMO)."),
    ],
))

# ---- API-29 / API-30 / API-31 --------------------------------------------
CLAIM_Q_FULL = {"ClaimNo": "{{claimNo}}", "PolicyNo": "{{PolicyNo}}", "CaseStatus": "{{caseStatus}}", "ClaimantName": "John Smith", "InsuredName": "John Smith", "PolicyHolderName": "John Smith", "EcsPolicyHolderIdNo": "A1234567", "ProductCode": "{{productCode}}", "ProductVersion": "1.0", "ProductLineCode": "{{productLine}}", "PolicyOrgCode": "10002", "RiskName": "Risk 1", "AccidentTimeFrom": "2026-01-01T00:00:00", "AccidentTimeTo": "2026-12-31T23:59:59", "NoticeTimeFrom": "2026-01-01T00:00:00", "NoticeTimeTo": "2026-12-31T23:59:59", "UpdateTimeFrom": "2026-01-01T00:00:00", "UpdateTimeTo": "2026-12-31T23:59:59", "PageNo": 1, "PageSize": 10}
CLAIM_Q_RESP = {"Status": "OK", "Messages": [], "Model": {"Total": 1, "Results": [{"ClaimNo": "string", "PolicyNo": "string", "ProductCode": "string", "CaseStatus": "string", "AccidentTime": "2026-09-27T14:30:00", "AccidentDesc": "Rear-end collision at traffic light", "LossCause": "string", "PolicyHolderName": "John Smith", "CurrencyCode": "USD"}]}}
CLAIM_SETS = ("const list = (b.Model && (b.Model.Results || b.Model.ElementsInCurrentPage || b.Model)) || [];\n"
              "const c = Array.isArray(list) ? list[0] : null;\n"
              "if (c && c.ClaimNo) pm.collectionVariables.set('claimNo', c.ClaimNo);\n"
              "if (c && (c.ClmPolicyId || c.ClaimPolicyId)) pm.collectionVariables.set('clmPolicyId', c.ClmPolicyId || c.ClaimPolicyId);")
APIS.append(dict(
    id="API-29", title="Claim Search API", owner="EasyClaims Team",
    endpoint="POST /platform/api-orchestration/v1/flow/ECS_claim_queryClaimForScenes",
    requests=[dict(name="Claim Search", method="POST", path="/platform/api-orchestration/v1/flow/ECS_claim_queryClaimForScenes",
                   mand=dict(body={}), full=dict(body=CLAIM_Q_FULL),
                   examples=[("200 OK (spec structure)", 200, "OK", CLAIM_Q_RESP)], checks=ENVELOPE_ATT, sets=CLAIM_SETS,
                   notes="Every field is optional, so the Mandatory variant sends `{}`. Paging wrapper inside Model is unconfirmed (Total/Results assumed). Sets `claimNo`, and `clmPolicyId` when present.")],
))
APIS.append(dict(
    id="API-30", title="Load Claim Case Detail API", owner="EasyClaims Team",
    endpoint="GET /platform/api-orchestration/v1/flow/ECS_claimquery_loadCaseDetail",
    requests=[dict(name="Load Claim Case Detail", method="GET", path="/platform/api-orchestration/v1/flow/ECS_claimquery_loadCaseDetail",
                   mand=dict(query=[q("claimNo", "{{claimNo}}")]), full=dict(query=[q("claimNo", "{{claimNo}}")]),
                   examples=[("200 OK (spec structure)", 200, "OK", {"Status": "OK", "Messages": [], "Model": {"ClaimNo": "string", "FnolNo": "string", "CaseStatus": "string", "PolicyNo": "string", "ProductCode": "string", "AccidentTime": "2026-09-27T14:30:00", "AccidentDesc": "Rear-end collision at traffic light", "LossCause": "string", "CurrencyCode": "USD", "ClaimObjectList": [{"ObjectId": 0, "SubClaimType": "string", "StatusCode": "string", "DamageObject": "Insured vehicle", "EstimatedLossAmount": 2500, "EstimatedLossCurrency": "USD"}], "ClaimPartyList": [{"PartyName": "John Smith", "PtyPartyType": "string", "InsuredRelation": "string"}]}})],
                   checks=ENVELOPE_ATT,
                   sets="const m = b.Model || {};\nif (m.ClmPolicyId || m.ClaimPolicyId) pm.collectionVariables.set('clmPolicyId', m.ClmPolicyId || m.ClaimPolicyId);")],
))
CLAIM_POLICY_RESP = {"Status": "OK", "Messages": [], "Model": {"CaseId": 0, "PolicyNo": "string", "ProductCode": "string", "ProductVersion": "1.0", "PolicyStatus": 2, "EffDate": "2026-01-01", "ExpDate": "2026-12-31", "SumInsured": 100000, "Premium": 1260, "CurrencyCode": "USD", "DeductibleAmount": 500, "PolicyHolderName": "John Smith", "PolicyHolderIdType": "1", "PolicyHolderIdNo": "A1234567", "InsuredName": "John Smith", "IsCoInsurance": "N", "OrgCode": "string"}}
APIS.append(dict(
    id="API-31", title="Load Claim Policy API", owner="EasyClaims Team",
    endpoint="GET /platform/api-orchestration/v1/flow/ECS_common_loadClaimPolicy",
    requests=[dict(name="Load Claim Policy", method="GET", path="/platform/api-orchestration/v1/flow/ECS_common_loadClaimPolicy",
                   mand=dict(query=[q("clmPolicyId", "{{clmPolicyId}}")]), full=dict(query=[q("clmPolicyId", "{{clmPolicyId}}")]),
                   examples=[("200 OK (spec structure)", 200, "OK", CLAIM_POLICY_RESP)], checks=ENVELOPE_ATT,
                   notes="Spec open point: which Claim Search / case detail field carries clmPolicyId.")],
))

# ---- API-32 --------------------------------------------------------------
APIS.append(dict(
    id="API-32", title="Query Endorsement History API", owner="EasyPA Apps Team",
    endpoint="GET /platform/endo/core/endo/v1/queryEndorsementHistory",
    requests=[dict(name="Query Endorsement History", method="GET", path="/platform/endo/core/endo/v1/queryEndorsementHistory",
                   mand=dict(query=[q("policyId", "{{policyId}}", "Signed PolicyId from API-20")]), full=dict(query=[q("policyId", "{{policyId}}", "Signed PolicyId from API-20")]),
                   examples=[("200 OK (spec sample)", 200, "OK", [{"EndoId": 0, "EndoNo": "string", "EndoType": "20", "EndoStatus": "300", "CauseType": "string", "EndoEffectiveDate": "2026-06-01", "IssueDate": "2026-05-28", "PolicyNo": "POTBTI01229164", "ProductCode": "TBTI", "SumInsuredDelta": 0, "DuePremium": 45.5, "Content": "Period of insurance extended by 7 days"}, {"EndoId": 0, "EndoNo": "string", "EndoType": "3", "EndoStatus": "120", "EndoEffectiveDate": "2026-09-01", "PolicyNo": "POTBTI01229164", "DuePremium": -120.0}])],
                   checks=IS_ARRAY, notes="Spec open point: bare list vs wrapped response.")],
))

# ---- API-33 --------------------------------------------------------------
APIS.append(dict(
    id="API-33", title="Retrieve Complete Claim and Policy Context for Survey API", owner="EasyClaims Team",
    endpoint="POST ECS_claim_queryClaimForScenes -> GET ECS_common_loadClaimPolicy",
    requests=[
        dict(name="Step 1 - Claim Search", method="POST", path="/platform/api-orchestration/v1/flow/ECS_claim_queryClaimForScenes",
             mand=dict(body={}), full=dict(body={"ClaimNo": "{{claimNo}}", "PolicyNo": "{{PolicyNo}}", "CaseStatus": "{{caseStatus}}", "ClaimantName": "John Smith", "InsuredName": "John Smith", "PolicyHolderName": "John Smith", "EcsPolicyHolderIdNo": "A1234567", "ProductCode": "{{productCode}}", "ProductVersion": "1.0", "ProductLineCode": "{{productLine}}", "AccidentTimeFrom": "2026-01-01T00:00:00", "AccidentTimeTo": "2026-12-31T23:59:59", "NoticeTimeFrom": "2026-01-01T00:00:00", "NoticeTimeTo": "2026-12-31T23:59:59", "UpdateTimeFrom": "2026-01-01T00:00:00", "UpdateTimeTo": "2026-12-31T23:59:59", "PageNo": 1, "PageSize": 10}),
             examples=[("200 OK (spec structure)", 200, "OK", CLAIM_Q_RESP)], checks=ENVELOPE_ATT, sets=CLAIM_SETS),
        dict(name="Step 2 - Load Claim Policy", method="GET", path="/platform/api-orchestration/v1/flow/ECS_common_loadClaimPolicy",
             mand=dict(query=[q("clmPolicyId", "{{clmPolicyId}}")]), full=dict(query=[q("clmPolicyId", "{{clmPolicyId}}")]),
             examples=[("200 OK (spec structure)", 200, "OK", CLAIM_POLICY_RESP)], checks=ENVELOPE_ATT),
    ],
))

# ---- API-34 --------------------------------------------------------------
APIS.append(dict(
    id="API-34", title="SMS OTP Dispatch via Notifications Hub API", owner="Notifications Hub Team / EasyPA Apps Team",
    endpoint="Option A POST /comm/v1/notifications/send (404 on trialx) · Option B SNS MFA send/verify",
    requests=[
        dict(name="Option A - OTP via Notifications Hub (contract TBC - 404 on trialx)", method="POST", path="/comm/v1/notifications/send",
             mand=dict(body={"Channel": "SMS", "Recipient": "{{mobileNo}}", "TemplateCode": "{{otpTemplateCode}}", "TemplateParams": {"otp": "{{portalOtp}}"}}),
             full=dict(body={"Channel": "SMS", "Recipient": "{{mobileNo}}", "TemplateCode": "{{otpTemplateCode}}", "TemplateParams": {"otp": "{{portalOtp}}", "expiresInMinutes": "5"}}),
             examples=[GATEWAY_404], checks=[("body is JSON", "true")], notes=HUB_NOTE),
        dict(name="Option B - Send MFA SMS (SNS)", method="POST", path="/mo-fo/1.0/sns/mfa/sms/send",
             mand=dict(body={"to": "{{mobileNo}}"}),
             full=dict(body={"to": "{{mobileNo}}", "business_code": "LOGIN", "block_resend_in_seconds": 30, "code_length": 6, "code_strategy": 0, "expires_in_minutes": 15, "account_name": "{{smsAccount}}", "sign_name": "{{signName}}", "template_code": "{{otpTemplateCode}}", "template_params": {}}),
             examples=[("200 OK (spec structure)", 200, "OK", {"code": "string", "message": "string", "trace_id": "string", "data": {"message_id": "string", "content_length": 0}})],
             checks=ENVELOPE_SNS),
        dict(name="Option B - Verify MFA SMS (SNS)", method="POST", path="/mo-fo/1.0/sns/mfa/sms/verify",
             mand=dict(body={"to": "{{mobileNo}}", "code": "{{otpCode}}"}),
             full=dict(body={"to": "{{mobileNo}}", "code": "{{otpCode}}", "business_code": "LOGIN", "case_sensitive": False, "keep": False, "output_result": True}),
             examples=[("200 OK - verified (spec structure)", 200, "OK", {"code": "string", "message": "string", "trace_id": "string", "data": {"to": "+18xxxxx000", "verified": True}})],
             checks=ENVELOPE_SNS),
    ],
))


# ---------------------------------------------------------------------------
# Datatable and LoadTables folder
# ---------------------------------------------------------------------------
CT_PATH = "/platform/dd/public/codetable/v1/codeTableVoList/byNameList"
CT_DATA_PATH = "/platform/dd/public/codetable/v1/data/list/byName"
CT_CHECKS = [("body is JSON array", "Array.isArray(b)"),
             ("BusinessCodeTableValueList present", "b.length > 0 && Array.isArray(b[0].BusinessCodeTableValueList)")]


def ct_example(names):
    out = []
    for n in names:
        vals = CODE_TABLES[n][2]
        out.append({"BusinessCodeTable": {"Name": n},
                    "BusinessCodeTableValueList": [{"Id": i + 1, "Code": c, "Description": d} for i, (c, d) in enumerate(vals)]
                    or [{"Id": 1, "Code": "<code>", "Description": "<tenant value - not published in spec>"}]})
    return out


def load_tables_folder():
    names = sorted(CODE_TABLES)
    svc = [n for n in names if CODE_TABLES[n][0] == SVC]
    rows = ["| Code table | Source | Used by (API field) | Known values in spec |", "|---|---|---|---|"]
    for n in names:
        src, uses, vals = CODE_TABLES[n]
        rows.append(f"| `{n}` | {src} | {'; '.join(uses)} | {', '.join(f'{c}={d}' for c, d in vals) or '-'} |")
    unnamed = ["", "Fields the spec binds to a tenant code table without naming it:", "", "| API | Fields | Note |", "|---|---|---|"]
    unnamed += [f"| {a} | {f} | {n} |" for a, f, n in UNNAMED_CODE_FIELDS]
    folder_desc = ("Every code table, data table and rate/config table that a field in API-01..API-34 is bound to.\n\n"
                   "* **Code Tables** - `POST " + CT_PATH + "` with `[{\"CodeTableName\": \"<name>\"}]` returns "
                   "`[{BusinessCodeTable:{Name}, BusinessCodeTableValueList:[{Id, Code, Description}]}]`.\n"
                   "* **Service tables** (UserInfo, PubBranch, Products, SalesChannelAPI, SalesAgreementAPI, ProductElementIdAPI) are code tables fed by a platform service; they load through the same API.\n"
                   "* **Data Tables** - API-10. **Rate / Config Tables** - API-11.\n\n" + "\n".join(rows) + "\n" + "\n".join(unnamed))

    ct_items = [request("Load ALL portal code tables (one call)", "POST", CT_PATH,
                        body=[{"CodeTableName": n} for n in names],
                        desc="Loads every code table referenced by the 34 portal APIs in one call. Missing names (not configured on trialx) are the ones to raise with the Config team.",
                        examples=[("200 OK (structure; values from spec where published)", 200, "OK", ct_example(names))],
                        tests=t_struct("CODETABLES", CT_CHECKS) + "\nif (Array.isArray(b)) { const got = b.map(x => (x.BusinessCodeTable || {}).Name); console.log('Code tables returned: ' + got.length + ' / " + str(len(names)) + "'); pm.collectionVariables.set('codeTablesMissing', JSON.stringify(" + json.dumps(names) + ".filter(n => !got.includes(n)))); }",
                        key="ct-all")]
    ct_items.append(request("Load code table values filtered (data/list/byName)", "POST", CT_DATA_PATH,
                            query=[q("codeTableName", "SChannelStatus")], body={"CodeTableName": "SChannelStatus", "ConditionMap": {}, "Keyword": ""},
                            headers=[h("x-mo-lang-id", "en_US", "Optional language", disabled=True)],
                            desc="Runtime variant with ConditionMap / Keyword filtering (InsureMO iTables runtime API). Swap the code table name as needed.",
                            examples=[("200 OK (structure)", 200, "OK", [{"Id": 1, "Code": "1", "Description": "Active"}])],
                            tests=t_struct("CODETABLE-DATA", [("body present", "true")]), key="ct-data"))
    per_ct = []
    for n in names:
        src, uses, vals = CODE_TABLES[n]
        d = (f"**Code table `{n}`** ({src})\n\nUsed by:\n" + "\n".join(f"* {u}" for u in uses) +
             ("\n\nKnown values in spec: " + ", ".join(f"`{c}` {dd}" for c, dd in vals) if vals else "\n\nValues not published in the spec - load from trialx."))
        per_ct.append(request(f"{n}", "POST", CT_PATH, body=[{"CodeTableName": n}], desc=d,
                              examples=[("200 OK" + (" (values from spec)" if vals else " (structure)"), 200, "OK", ct_example([n]))],
                              tests=t_struct(f"CT {n}", CT_CHECKS), key=f"ct-{n}"))
    svc_items = [it for it in per_ct if it["name"] in svc]
    ct_only = [it for it in per_ct if it["name"] not in svc]

    dt_items = [
        request("Data table - Load Product list ({{ProductListTable}})", "POST", "/platform/dd/public/datatable/v1/dataTableVoList/byNameList",
                body=[{"DataTableName": "{{ProductListTable}}", "ConditionMap": {"ProductCode": "1001"}}],
                desc="Data table behind API-10 (products under a product code 1001 / 1005). Table name TBC by the Config/Apps team.",
                examples=[("200 OK (spec sample)", 200, "OK", DT_SAMPLE)], tests=t_struct("DT ProductList", IS_ARRAY), key="dt-product"),
        request("Data table - Load Plan list ({{PlanListTable}})", "POST", "/platform/dd/public/datatable/v1/dataTableVoList/byNameList",
                body=[{"DataTableName": "{{PlanListTable}}"}],
                desc="Data table for Load Plan (API-10 use case). Table name TBC by the Config/Apps team.",
                examples=[("200 OK (structure)", 200, "OK", [{"BusinessDataTable": {"Name": "{{PlanListTable}}", "Fields": {}}, "Records": []}])],
                tests=t_struct("DT PlanList", IS_ARRAY), key="dt-plan"),
        request("Data table - runtime data by name", "POST", "/platform/dd/public/datatable/v1/data/list/byName",
                body={"dataTableName": "{{ProductListTable}}", "conditionMap": {"ProductCode": "1001"}},
                desc="Cached runtime read of one data table (iTables runtime API). Note the camelCase body keys used by this endpoint.",
                examples=[("200 OK (structure)", 200, "OK", [{"ProductCode": "1001", "SubProductCode": "1001-A", "SubProductName": "Plan A"}])],
                tests=t_struct("DT runtime", [("body present", "true")]), key="dt-runtime"),
    ]
    rt_items = [request("Rate/config table - Packages ({{PackageTable}})", "POST", "/platform/ratetable/rate/v1/lookup",
                        query=[q("code", "{{PackageTable}}"), q("version", "1")], body={"ProductCode": "1001"},
                        desc="Package table behind API-11 (TP / Silver / Gold / Platinum). Table code TBC.",
                        examples=[("200 OK (spec sample)", 200, "OK", [{"ProductCode": "1001", "PackageCode": "TP", "PackageName": "Third Party"}, {"ProductCode": "1001", "PackageCode": "SILVER", "PackageName": "Silver"}, {"ProductCode": "1001", "PackageCode": "GOLD", "PackageName": "Gold"}, {"ProductCode": "1001", "PackageCode": "PLATINUM", "PackageName": "Platinum"}])],
                        tests=t_struct("RT Packages", IS_ARRAY), key="rt-package")]
    return folder("Datatable and LoadTables", [
        folder("Code Tables (LoadTables)", ct_items + ct_only, "One request per code table bound to an API field, plus a one-call loader."),
        folder("Service-backed Code Tables", svc_items, "Code tables whose values come from a platform service (users, branches, products, channels, agreements, product elements)."),
        folder("Data Tables", dt_items, "Data tables used by the portal (API-10)."),
        folder("Rate - Config Tables", rt_items, "Rate / configuration tables used by the portal (API-11)."),
    ], folder_desc)


# ---------------------------------------------------------------------------
# Collection assembly
# ---------------------------------------------------------------------------
PRE_REQUEST = r"""
// Auto-fetch a trialx token (API-02) when none is cached or it is about to expire.
const skip = pm.info.requestName === 'Get Token';
const token = pm.collectionVariables.get('access_token');
const exp = Number(pm.collectionVariables.get('token_expires_at') || 0);
if (!skip && (!token || Date.now() > exp) && pm.environment.get('username')) {
  pm.sendRequest({
    url: pm.environment.get('baseUrl') + '/cas/get-token',
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    body: { mode: 'raw', raw: JSON.stringify({
      username: pm.environment.get('username'),
      password: pm.environment.get('password'),
      tenant_code: pm.environment.get('tenantCode') }) }
  }, (err, res) => {
    if (err) { console.error('get-token failed', err); return; }
    const b = res.json();
    if (b.access_token) {
      pm.collectionVariables.set('access_token', b.access_token);
      pm.collectionVariables.set('token_expires_at', Date.now() + (b.expire_in - 60) * 1000);
    } else { console.error('get-token: ' + b.message); }
  });
}
"""

CHAIN_VARS = ["access_token", "token_expires_at", "channelId", "collectionId", "quotePolicyId", "quotationNo",
              "policyId", "PolicyNo", "attachFileId", "claimNo", "clmPolicyId", "codeTablesMissing"]


def build(variant):
    is_full = variant == "full"
    label = "Full (Mandatory + Optional fields)" if is_full else "Mandatory fields only"
    api_folders = []
    for api in APIS:
        items = []
        specs = list(api["requests"]) + (api.get("full_only", []) if is_full else [])
        for r in specs:
            v = r["full"] if is_full else r.get("mand")
            if v is None:
                continue
            tests = r.get("custom_tests") or t_struct(api["id"], r["checks"], r.get("sets", ""))
            items.append(request(
                r["name"], r["method"], r["path"], query=v.get("query"), body=v.get("body"), formdata=v.get("formdata"),
                headers=v.get("headers"), no_auth=r.get("no_auth", False),
                desc=desc(api["id"], api["title"], f"{r['method']} {r['path']}", api["owner"], label, r.get("notes", "")),
                examples=r["examples"], tests=tests, key=f"{variant}-{api['id']}-{r['name']}"))
        api_folders.append(folder(f"{api['id']} {api['title']}", items,
                                  f"{api['endpoint']}  \nOwner: {api['owner']}" + code_table_md([api["id"]])))
    api_folders.sort(key=lambda f: f["name"])
    name = f"Trialx - Portal Integration APIs - {'Full + Optional' if is_full else 'Mandatory'}"
    return {
        "info": {
            "_postman_id": uid("collection", variant),
            "name": name,
            "description": (
                f"Portal Integration API Specification v0.2 - all 34 APIs on InsureMO tenant **trialx**.\n\n"
                f"Variant: **{label}**.\n\n"
                "1. Import `Trialx.postman_environment.json`, select it, fill `username` / `password` (Machine User).\n"
                "2. Any request auto-fetches a token (collection pre-request script). Or run *API-02 > Get Token*.\n"
                "3. Run in order (Collection Runner / Newman): search APIs store the signed IDs used by the load APIs.\n"
                "4. Each request has structure tests; a failing test names the broken part. Saved examples hold the spec samples "
                "and the responses observed on trialx.\n\n"
                "See `STRUCTURE-CHECK.md` for which API structures are not working."),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
        "event": [{"listen": "prerequest", "script": {"type": "text/javascript", "exec": PRE_REQUEST.strip().split("\n")}}],
        "variable": [{"key": k, "value": ""} for k in CHAIN_VARS],
        "item": api_folders + [load_tables_folder()],
    }


def environment():
    vals = [
        ("baseUrl", "https://portal-gw.insuremo.com", "default", "InsureMO portal API gateway (trialx tenant domain trialx-gimc.insuremo.com)"),
        ("tenantCode", "trialx", "default", ""),
        ("username", "", "default", "Machine User account name"),
        ("password", "", "secret", "Machine User password"),
        ("mobileNo", "+10000000000", "default", ""),
        ("otpCode", "123456", "default", "Code the user typed"),
        ("portalOtp", "123456", "default", "OTP generated by the portal (Option A)"),
        ("smsAccount", "", "default", "SNS SMS account"),
        ("signName", "", "default", "SNS SMS signature"),
        ("otpTemplateCode", "", "default", "SNS OTP template code"),
        ("emailAccount", "", "default", "SNS email account"),
        ("customerEmail", "customer@example.com", "default", ""),
        ("payerCode", "", "default", ""),
        ("agentCode", "", "default", ""),
        ("customerNo", "", "default", ""),
        ("indiCustomerId", "", "default", "Individual customer ID"),
        ("orgCustomerId", "", "default", "Organisation customer ID"),
        ("productCode", "TBTI", "default", ""),
        ("productLine", "Travel", "default", ""),
        ("versionDate", "2026-01-01T00:00:00", "default", ""),
        ("ProductListTable", "", "default", "Data table name for Load Product (TBC)"),
        ("PlanListTable", "", "default", "Data table name for Load Plan (TBC)"),
        ("PackageTable", "", "default", "Rate table code for packages (TBC)"),
        ("businessType", "", "default", "AttachBusinessType code"),
        ("businessNo", "", "default", "Policy / claim / quotation number"),
        ("directory", "", "default", "Document type node from API-25"),
        ("reportChannel", "", "default", "FNOL report channel (TBC)"),
        ("operationType", "", "default", "FNOL operation type (TBC)"),
        ("lossCause", "", "default", "CauseOfLoss code"),
        ("claimType", "", "default", "ClaimType code"),
        ("fnolType", "", "default", "ClaimFnolType code"),
        ("caseStatus", "", "default", "ClaimStatus code"),
    ]
    return {"id": uid("env", "trialx"), "name": "Trialx (InsureMO)",
            "values": [{"key": k, "value": v, "type": t, "enabled": True, **({"description": d} if d else {})} for k, v, t, d in vals],
            "_postman_variable_scope": "environment"}


def main():
    out = {
        "Trialx-Portal-APIs-Mandatory.postman_collection.json": build("mandatory"),
        "Trialx-Portal-APIs-Full-Optional.postman_collection.json": build("full"),
        "Trialx.postman_environment.json": environment(),
    }
    for fn, data in out.items():
        with open(os.path.join(HERE, fn), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("wrote", fn)


if __name__ == "__main__":
    main()
