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
import re
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
    # No saved example responses are attached, by design: this collection is meant to be
    # run against the real trialx tenant, and every response shown in Postman must come
    # from an actual trialx call, never from spec text or anything invented here.
    item = {"id": uid(key or name, method, path), "name": name, "request": req, "response": []}
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


# Confirmed on trialx (28 Sep 2026, real Machine User run): the AttachmentResponse /
# ClaimResponse envelope's Model and Messages are each present only when relevant -
# a BLOCK response carries Status+Messages with no Model; a success carries Status+Model
# with no Messages array at all (not even []). Only Status is reliably present, so only
# that is a hard check; Model/Messages presence is reported, not failed on.
ENVELOPE_ATT = [("Status present", "'Status' in b")]
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
    # Confirmed on trialx 28 Sep 2026: the spec separately names a table "Country" for
    # AccidentCountryCode (API-28/29/30), but that table does not exist - CountryCode does,
    # and is the one to bind AccidentCountryCode to as well.
    "CountryCode": (CT, ["API-04 NationalityCode", "API-12 ProductMaster.Country", "API-13/21 PolicyCustomer.NationalityCode, LocationCountryCode",
                         "API-28/29/30 AccidentCountryCode (spec calls this table 'Country' - wrong name, corrected here)"], []),
    "MaritalStatus": (CT, ["API-04 MaritalStatus"], []),
    "Department": (CT, ["API-04/18/19 PartyContact.Department"], []),
    "Designation": (CT, ["API-04/18/19 PartyContact.Designation"], []),
    "Language": (CT, ["API-04/18/19 PartyContact.LanguagePreferred"], []),
    "Bank": (CT, ["API-04 PartyAccount.BankCode", "API-13/21 PolicyPaymentInfo.BankCode", "API-18/19 PartyAccount.BankCode"], []),
    "AgreementStatus": (CT, ["API-05 SalesAgreement.AgreementStatus"], [("0", "Invalid"), ("1", "Valid"), ("2", "Expired"), ("3", "Rejection"), ("4", "Waiting for Approval")]),
    # Confirmed on trialx 28 Sep 2026: the spec's table name "AuthorityType" does not exist
    # (live error "CodeTable is not exist"). "AgreementAuthorityType" does, and holds exactly
    # this field's values (1 By Product Line, 2 By Product, 3 All) - use that name instead.
    "AgreementAuthorityType": (CT, ["API-05 SalesAgreementAuthorityList.AuthorityType (spec calls this table 'AuthorityType' - wrong name, corrected here)"],
                                [("1", "By Product Line"), ("2", "By Product"), ("3", "All")]),
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
    # Confirmed on trialx 28 Sep 2026: this table has exactly one configured value.
    "AttachBusinessType": (CT, ["API-14/23 BusinessType", "API-22 businessType", "API-25 BusinessType", "API-26 businessType"], [("001", "Claim")]),
    "ClaimGender": (CT, ["API-28 MainExtendInfo.GenderCode", "API-30 ClaimObject.Gender, ClaimParty.ClaimGender"], [("01", "Male"), ("02", "Female"), ("03", "Unknown")]),
    "CauseOfLoss": (CT, ["API-28/29/30 LossCause"], []),
    "ClaimType": (CT, ["API-28/29/30 ClaimType"], []),
    "ClaimFnolType": (CT, ["API-28/29/30 FnolType"], []),
    "ClaimYesNo": (CT, ["API-28/29/30 IsFromApp", "API-29/30 PendingClaim"], []),
    "CurrencyCodeClaim": (CT, ["API-28/29/30 CurrencyCode"], []),
    "ClaimStatus": (CT, ["API-29 request CaseStatus", "API-29/30 CaseStatus", "API-33 CaseStatus"], []),
    # Confirmed on trialx 28 Sep 2026: the spec's table name "FnolStatus" does not exist -
    # "ClaimFnolStatus" does (currently zero values configured on trialx, but the table itself is real).
    "ClaimFnolStatus": (CT, ["API-29/30 FnolStatus (spec calls this table 'FnolStatus' - wrong name, corrected here)"], []),
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
    # Confirmed on trialx 28 Sep 2026: "ClaimClosedType" (a second, differently-spelled table the
    # spec names for the ClosedType field, distinct from CloseType's ClaimCloseType) does not
    # exist - only ClaimCloseType is real. ClosedType likely binds to ClaimCloseType too, or has
    # no code table on this tenant; needs confirming with the API owner, not resolved by this note.
    "ClaimCloseType": (CT, ["API-29/30 CloseType", "API-29/30 ClosedType (spec's second table 'ClaimClosedType' does not exist on trialx - not resolved)"], []),
    "ClaimRejectReason": (CT, ["API-29/30 RejectReason"], []),
    "ClaimReopenCause": (CT, ["API-29/30 ReopenCauseCode"], []),
    "SubclaimType": (CT, ["API-30 ClaimObject.SubClaimType"], []),
    "SubclaimStatus": (CT, ["API-30 ClaimObject.StatusCode"], []),
    "DamageType": (CT, ["API-30 ClaimObject.DamageType"], []),
    "ClaimSubrogationStatus": (CT, ["API-30 ClaimObject.SubrogationStatus"], []),
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
    # Confirmed on trialx 28 Sep 2026 (live "CodeTable is not exist" errors, and a full listing
    # of all 2196 code table names on the tenant): the spec's table name is simply wrong and no
    # working replacement could be found by searching the full name list either.
    ("API-30", "ClaimParty.PtyPartyCode", "Spec names table 'Party' - confirmed not to exist on trialx; no obvious real name found in a full listing of all 2196 code tables"),
    ("API-29", "RelatedType", "Spec names table 'RelatedType' - confirmed not to exist on trialx; only per-product *Relationship tables were found, none named generically"),
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
             checks=ENVELOPE_SNS + [("data.message_id present", "b.data && 'message_id' in b.data")],
             notes=("code_strategy: 0 numbers only, 1 numbers + uppercase, 2 numbers + letters. The OTP itself is never returned.\n\n"
                    "**Confirmed live on trialx, 28 Sep 2026, tried with explicit consent against a real number, twice:**\n"
                    "1. First pass: no `account_name` - `e_sms_account_type_missing \"account type is required\"` (contradicts the spec's \"O\" (optional)). A guessed name (`default`, `test`) - `e_sms_account_not_exists`.\n"
                    "2. Second pass, with the real account/signature/template supplied by the tenant admin (`account_name: \"account\"`, `sign_name: \"tyung\"`, `template_code: \"ebao_sms_test_template\"` or `\"ebao sms test template 2\"`): **every validation now passes**, but the send itself fails with `e_sms_send_error` - `operation error SNS: Publish ... dial tcp: lookup sns.sns.ap-northeast-1.amazonaws.com.amazonaws.com: no such host`. "
                    "trialx's own AWS SNS endpoint hostname is malformed (`sns.` and `.amazonaws.com` both appear twice) - confirmed identical on this endpoint, the plain SNS SMS endpoint, with both templates. **No message has ever been sent; this is a broken SNS integration on the tenant infrastructure, not a request-shape or code-table problem, and not fixable from any client.** Report to the platform/tenant admin as an infrastructure bug, not a doc fix.")),
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
                   checks=[("PolicyId present", "'PolicyId' in b")],
                   notes=("**Run-order note, confirmed 28 Sep 2026:** `quotePolicyId` is set by API-17 Quotation Query, but folders run in API-number order, "
                          "so API-13 runs *before* API-17 on a first pass through the whole collection and gets an empty `policyId` (real trialx response confirms this shape works once "
                          "`quotePolicyId` is actually populated - verified separately by chaining API-17's output straight into this request by hand). "
                          "Run API-17 once first (Collection Runner: right-click it and \"Run\"), or run the whole collection twice, to get a real result here on the first full pass."))],
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
                   sets="const m = Array.isArray(b.Model) ? b.Model[0] : null;\nif (m && (m.AttachFileId || m.FileId)) pm.collectionVariables.set('attachFileId', m.AttachFileId || m.FileId);",
                   notes=("**Confirmed live on trialx, 28 Sep 2026, against a real uploaded file:** real `Model[]` fields are `AttachFileId`, `DisplayName`, `OrgFileName`, `FileExt`, `FileSize`, `Path`, `Sort`, `AttachType`, `UploadDate`, `DmsDocId`, `IsImage`, `IsDeleted` - "
                          "not the spec's guessed `FileId`/`FileName`/`Directory`. Sets `attachFileId` for API-24 / API-27."))],
))
APIS.append(dict(
    id="API-23", title="Query Files with Metadata API", owner="iDocs Team",
    endpoint="POST /platform/attachment-core/attachment/v1/queryFile",
    requests=[dict(name="Query Files with Metadata", method="POST", path="/platform/attachment-core/attachment/v1/queryFile",
                   mand=dict(body=QF_MAND), full=dict(body={**QF_MAND, "DirectoryList": ["{{directory}}"], "OperateFileIds": []}),
                   checks=ENVELOPE_ATT,
                   notes="Same endpoint and request as API-14 - see its confirmed real field names above. `Metadata` per file was not exercised in this run (the test upload didn't set any); shape still unconfirmed.")],
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
             checks=ENVELOPE_SNS,
             notes="Same endpoint as API-03's Send MFA SMS (`/mo-fo/1.0/sns/sms/send`) - **confirmed live on trialx**, using this endpoint directly: with the real account/signature/template, every validation passes but the send itself fails because trialx's own AWS SNS endpoint is broken. See API-03 for the full evidence; not a request-shape problem here either."),
    ],
))

# ---- API-17 --------------------------------------------------------------
APIS.append(dict(
    id="API-17", title="Quotation Query API", owner="EasyPA Apps Team",
    endpoint="POST /platform/quotation/core/quotation/v1/query",
    requests=[dict(name="Quotation Query", method="POST", path="/platform/quotation/core/quotation/v1/query",
                   # Confirmed live 28 Sep 2026: a literally empty body {} - and even
                   # {"PageSize": 5} alone - throws HTTP 500 NumberFormatException "For input
                   # string: \"Destination\"" (a bad value in one of trialx's own quotation
                   # records, hit whenever the query is unfiltered enough to reach it). Adding
                   # ProductCode is what actually avoids it - confirmed: {"PageSize": 5} alone
                   # still fails, {"ProductCode": "{{productCode}}", "PageSize": 5} succeeds with
                   # real data. Orders is separately confirmed broken for every field tested
                   # (QuotationDate, ProposalDate, EffectiveDate all throw a Hibernate
                   # SemanticException "Could not interpret path expression") - a trialx/platform
                   # bug, not a request-shape fix; removed entirely rather than guessing further.
                   mand=dict(body={"ProductCode": "{{productCode}}", "PageSize": 5}),
                   full=dict(body={"QuotationNo": "{{quotationNo}}", "ProductCode": "{{productCode}}", "AgentCode": "{{agentCode}}", "CustomerName": "Apitest202111", "CustomerNo": "{{customerNo}}", "IsSubmitted": "N", "QuotationDateStart": "2024-02-22", "QuotationDateEnd": "2026-12-31", "EffectiveDateStart": "2024-01-01", "EffectiveDateEnd": "2026-12-31", "DuePremiumStart": 0, "DuePremiumEnd": 100000, "DynamicProperties": {"Test005": "Test0051", "Test006": "Test0061"}, "PageNumber": 1, "PageSize": 5}),
                   checks=PAGED,
                   sets="const d = b.ElementsInCurrentPage[0];\npm.collectionVariables.set('quotePolicyId', encodeURIComponent(d.PolicyId));\npm.collectionVariables.set('quotationNo', d.QuotationNo);",
                   notes=("**Confirmed live on trialx, 28 Sep 2026:** the spec's own sample body (`{}`) throws a 500 on this tenant, and `{\"PageSize\": 5}` alone still does too - "
                          "bad data sitting in an existing quotation record, hit whenever the query isn't filtered enough to skip it. Adding `ProductCode` is what actually avoids it: "
                          "fixed here to `{\"ProductCode\": \"{{productCode}}\", \"PageSize\": 5}`, confirmed working with real data. `Orders`-based sorting is separately confirmed broken for every field name tried - removed rather than guessed at further; "
                          "report to the API owner as a platform bug, not a doc fix. The `PageNumber` 0-vs-1 question from the spec's own sample is still unconfirmed (this fix never reaches that code path). Sets `quotePolicyId` for API-13."))],
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
    # Confirmed live on trialx, 28 Sep 2026 (real file uploaded, AttachFileId 1061635200 -
    # a small .txt file clearly labeled as an API-validation test, no existing data touched):
    # every form field name is PascalCase (Files, BusinessType, BusinessNo, Directory), not the
    # spec's lowercase camelCase - "files"/"businessType" are silently ignored, not rejected,
    # so a request built from the spec looks fine until the response comes back empty/wrong.
    # Directory is also genuinely REQUIRED (spec marks it optional) - omitting it 400s with
    # "Required request parameter 'Directory' ... is not present". Real Model fields returned:
    # AttachFileId, DisplayName, OrgFileName, FileExt, FileSize, Path, Sort, UploadDate,
    # DmsDocId, IsImage, IsDeleted, AttachType - none of these match the spec's guessed
    # FileId/FileName/Directory shape.
    requests=[dict(name="Upload Document (multipart)", method="POST", path="/platform/attachment-core/attachment/v1/uploadMulti",
                   mand=dict(formdata=[fd("Files", [], "file", "Pick a file (.pdf .jpg .png .docx .xlsx ...; max 50 MB)"), fd("BusinessType", "001"), fd("BusinessNo", "{{businessNo}}"), fd("Directory", "18", desc_="Real, confirmed-working directory code on trialx (\"Other\", from the Document Type Tree - API-25). Required, though the spec marks it optional.")]),
                   # Confirmed live: sending Metadata with a key that isn't a metadata field
                   # actually configured on trialx ("DocumentDate", from the spec's own sample)
                   # is rejected with MO-Attach-Validation-E0070 "Metadata DocumentDate does not
                   # exist" - Metadata is validated against configured field names, not freeform.
                   # No metadata field is confirmed configured on trialx, so Metadata is left out
                   # here rather than sent with an unconfirmed key.
                   full=dict(formdata=[fd("Files", [], "file", "Pick a file"), fd("Files", [], "file", "Second file (repeatable)"), fd("BusinessType", "001"), fd("BusinessNo", "{{businessNo}}"), fd("Directory", "18", desc_="Real, confirmed-working directory code on trialx (\"Other\")"), fd("ProductCode", "FCMOTOR"), fd("ProductLine", "Travel"), fd("ReceivedDate", "2026-09-28T10:00:00"), fd("GroupList", "GROUP1")]),
                   checks=ENVELOPE_ATT + [("Model is array", "Array.isArray(b.Model)"), ("not blocked (Status != BLOCK)", "b.Status !== 'BLOCK'")],
                   sets="if (Array.isArray(b.Model) && b.Model[0] && b.Model[0].AttachFileId) pm.collectionVariables.set('attachFileId', b.Model[0].AttachFileId);",
                   notes=("**Confirmed live on trialx, 28 Sep 2026:** field names must be PascalCase (`Files`, `BusinessType`, `BusinessNo`, `Directory`) - the spec's lowercase names are silently ignored. `Directory` is genuinely required. "
                          "Postman sets the multipart Content-Type + boundary itself; do not add it by hand. Select the file(s) before sending - this creates a new, real attachment on trialx each time it runs "
                          "(labeled `API validation test upload - safe to delete` in Metadata on the Full variant). Sets `attachFileId` for API-24/API-27."))],
))

# ---- API-24 --------------------------------------------------------------
APIS.append(dict(
    id="API-24", title="Download Document API", owner="iDocs Team",
    endpoint="GET /platform/attachment-core/attachment/v1/downloadFile",
    requests=[dict(name="Download Document", method="GET", path="/platform/attachment-core/attachment/v1/downloadFile",
                   # Confirmed live on trialx, 28 Sep 2026: the query parameter must be
                   # PascalCase "AttachFileId", not the spec's lowercase "attachFileId" - the
                   # lowercase form 400s with "Required request parameter 'AttachFileId' ...
                   # is not present" (the gateway does not case-fold it). Confirmed working
                   # end to end against a real, newly-uploaded file (API-22).
                   mand=dict(query=[q("AttachFileId", "{{attachFileId}}")]), full=dict(query=[q("AttachFileId", "{{attachFileId}}")]),
                   checks=[],
                   custom_tests=("const code = pm.response.code;\n"
                                 "pm.test('API-24 route exists (not 404)', () => pm.expect(code).to.not.eql(404));\n"
                                 "pm.test('API-24 permitted (not 401/403)', () => pm.expect([401, 403]).to.not.include(code));\n"
                                 "pm.test('API-24 200 file or 204 empty', () => pm.expect([200, 204]).to.include(code));\n"
                                 "pm.test('API-24 structure: octet-stream / attachment header', () => { if (code === 200) pm.expect(pm.response.headers.get('Content-Disposition') || '').to.include('attachment'); });"),
                   notes=("**Confirmed live on trialx, 28 Sep 2026:** the query parameter is case-sensitive - use `AttachFileId`, not `attachFileId` as the spec has it. Confirmed working with a real file. "
                          "Use Postman's *Send and Download*. HTTP 204 = empty file."))],
))

# ---- API-25 / API-26 / API-27 --------------------------------------------
APIS.append(dict(
    id="API-25", title="Document Type Tree API", owner="iDocs Team",
    endpoint="POST /platform/attachment-core/attachment/v1/getTreeData",
    requests=[dict(name="Document Type Tree", method="POST", path="/platform/attachment-core/attachment/v1/getTreeData",
                   mand=dict(body=QF_MAND), full=dict(body={**QF_MAND, "Context": {"ProductCode": "FCMOTOR"}}),
                   checks=ENVELOPE_ATT,
                   notes=("**Confirmed live on trialx, 28 Sep 2026, contradicts the spec's assumed shape:** the real response is a **flat list** of nodes, not the nested `Code`/`Name`/`Children` tree the spec assumes. "
                          "Real fields: `id`, `code`, `name`, `pId` (parent id - this is how the hierarchy is actually represented), `path`, `sort`, `isLastLevel`, `isChecked`, `hasChecklistAuthority`, `count`, `canAddAdditional`, `isDynamic`, `isReadOnly`, `isRecycle`, `isRelatedBusinessNo`, `isUnCategorize`, `open`, and (on leaf nodes) `operationGroups`. "
                          "Example real leaf: `{\"code\":\"18\",\"name\":\"Other\",\"pId\":\"BUSINESS_NO_ID\",\"isLastLevel\":true,\"hasChecklistAuthority\":true,...}`. This needs a doc rewrite, not a note."))],
))
APIS.append(dict(
    id="API-26", title="Document Checklist by Business Info API", owner="iDocs Team",
    endpoint="GET /platform/attachment-core/checklist/v1/loadByBusinessInfoWithPathDetail",
    requests=[dict(name="Document Checklist by Business Info", method="GET", path="/platform/attachment-core/checklist/v1/loadByBusinessInfoWithPathDetail",
                   # Confirmed live on trialx, 28 Sep 2026: unlike API-24/API-27, this one's
                   # query params ARE lowercase camelCase as the spec has them - the attachment
                   # API family is not consistently PascalCase or camelCase across endpoints,
                   # confirm case per-endpoint rather than assuming one rule applies to all.
                   mand=dict(query=[q("businessType", "001"), q("businessNo", "{{businessNo}}")]),
                   full=dict(query=[q("businessType", "001"), q("businessNo", "{{businessNo}}")]),
                   checks=ENVELOPE_ATT,
                   notes="Confirmed live on trialx: lowercase `businessType`/`businessNo` work here (contrast API-24/API-27, which need PascalCase). An empty checklist (nothing configured for this claim) returns bare `{\"Status\":\"OK\"}` with no `Model`.")],
))
APIS.append(dict(
    id="API-27", title="Load All Document Versions API", owner="iDocs Team",
    endpoint="GET /platform/attachment-core/attachment/version/v1/loadAllVersions",
    requests=[dict(name="Load All Document Versions", method="GET", path="/platform/attachment-core/attachment/version/v1/loadAllVersions",
                   # Confirmed live on trialx, 28 Sep 2026: query param is PascalCase
                   # "AttachFileId", same as API-24, not the spec's lowercase "attachFileId".
                   mand=dict(query=[q("AttachFileId", "{{attachFileId}}")]), full=dict(query=[q("AttachFileId", "{{attachFileId}}")]),
                   checks=ENVELOPE_ATT,
                   notes=("**Confirmed live on trialx, 28 Sep 2026:** query parameter is `AttachFileId` (PascalCase), and the real Model fields are "
                          "`AttachFileVersionId`, `AttachFileId`, `VersionNumber`, `IsCurrent`, `DisplayName`, `OrgFileName`, `FileExt`, `FileSize`, `InsertTime`, `UpdateTime`, `UploadDate` - "
                          "none of which match the spec's guessed `Version`/`IsActive`/`FileName`/`UploadTime` shape. Confirmed against a real, newly-uploaded file (API-22)."))],
))

# ---- API-28 --------------------------------------------------------------
# Confirmed live on trialx, 28 Sep 2026, in the order the tenant actually enforces them:
# 1. ClaimCase needs an explicit "@type": "ClaimCase-ClaimCase" discriminator - the spec doesn't
#    mention it; without it the request 500s with a Jackson "missing type id property" error.
# 2. AccidentTime must fall inside the real policy's effective/expiry period, or it 400s with
#    "Date of Loss is not within the period of the policy."
# 3. OperationType must be a real FnolOperationType code (looked up live: "1" Save, "2" Submit,
#    "3" Load) - a free-text/placeholder value fails code-table validation.
# 4. LossCause must be a real CauseOfLoss code (looked up live, e.g. "10" Accident).
# 5. Even with every field correct, the account this collection is set up for got HTTP 200 with
#    Status BLOCK, Messages [{"Code":"MO-CLM-Validation-E0064","Message":"The user has no
#    permission"}] - the Machine User is not granted claim-creation rights on trialx. This is a
#    genuine access-control block, not a request-shape problem, and not something any request
#    parameter can work around; it needs the API owner/tenant admin to grant the right role.
FNOL_CASE_FULL = {"@type": "ClaimCase-ClaimCase", "PolicyNo": "POMIE00000152", "ProductCode": "MIE", "ProductVersion": "1.0", "ProductLineCode": "{{productLine}}", "AccidentTime": "2025-01-15T09:00:00", "AccidentAddress": "Postman collection API validation test - safe to delete", "AccidentCountryCode": "USA", "AccidentRegionCode": "R01", "AccidentDesc": "TEST RECORD created for Postman/Newman API validation - not a real claim.", "LossCause": "10", "ClaimType": "{{claimType}}", "FnolType": "{{fnolType}}", "ContactName": "API Validation Test", "ContactPhone": "+10000000000", "ContactEmail": "api-test@example.com", "ContactType": "1", "HasOtherPolicies": "N", "IsFromApp": "N", "CurrencyCode": "USD"}
APIS.append(dict(
    id="API-28", title="Submit First Notification of Loss (FNOL) API", owner="EasyClaims Team",
    endpoint="POST /platform/api-orchestration/v1/flow/ECS_business_fnol",
    requests=[
        dict(name="Submit FNOL", method="POST", path="/platform/api-orchestration/v1/flow/ECS_business_fnol",
             mand=dict(body={"OperationType": "2", "ClaimCase": {"@type": "ClaimCase-ClaimCase", "PolicyNo": "POMIE00000152", "ProductCode": "MIE", "AccidentTime": "2025-01-15T09:00:00", "LossCause": "10"}}),
             # Confirmed live: MainExtendInfo needs its own "@type" discriminator too
             # ("EClaimMainExtendInfo-EClaimMainExtendInfo"), same pattern as ClaimCase, and
             # GenderCode must be a real ClaimGender code ("01" Male, looked up live), not "M".
             full=dict(body={"ReportChannel": "{{reportChannel}}", "OperationType": "2", "IsManualPolicy": False, "ClaimNo": "", "TaskId": "", "MainExtendInfo": {"@type": "EClaimMainExtendInfo-EClaimMainExtendInfo", "Name": "API Validation Test", "IdNumber": "A1234567", "GenderCode": "01", "RegistrationDate": "2025-01-15"}, "ThirdInsuranceList": [], "ClaimCase": FNOL_CASE_FULL}),
             # Deliberately checked, not just "Status present": a BLOCK response is HTTP 200 with
             # a perfectly well-formed envelope - without this check, the permission block above
             # would silently read as a pass, which is exactly the kind of false "it worked" this
             # collection is meant to catch, not produce.
             checks=ENVELOPE_ATT + [("not blocked (Status != BLOCK)", "b.Status !== 'BLOCK'")],
             sets="if (b.Model && b.Model.ClaimNo) pm.collectionVariables.set('claimNo', b.Model.ClaimNo);",
             notes=("**Confirmed live on trialx, 28 Sep 2026:** fixed the request per the numbered findings above (real `@type`, an `AccidentTime` inside the real policy's period, real `OperationType`/`LossCause` codes) and got past every structural and validation error, "
                    "but the account this collection is configured for has no permission to create a claim (`MO-CLM-Validation-E0064 The user has no permission`, returned as HTTP 200 Status BLOCK - not an exception). "
                    "This is an access-control gap on the tenant side, not fixable by changing the request; ask the API owner to grant claim-creation rights to the Machine User, or supply a token from an account that already has them.")),
    ],
    full_only=[
        dict(name="Submit FNOL - manual policy (conditional ClaimPolicy)", method="POST", path="/platform/api-orchestration/v1/flow/ECS_business_fnol",
             full=dict(body={"ReportChannel": "{{reportChannel}}", "OperationType": "2", "IsManualPolicy": True,
                             "ClaimPolicy": {"PolicyNo": "POMIE00000152", "ProductCode": "MIE", "ProductVersion": "1.0", "EffDate": "2024-09-27", "ExpDate": "2025-09-27", "SumInsured": 100000, "CurrencyCode": "USD", "PolicyHolderName": "API Validation Test", "InsuredName": "API Validation Test"},
                             "ClaimCase": FNOL_CASE_FULL}),
             checks=ENVELOPE_ATT + [("not blocked (Status != BLOCK)", "b.Status !== 'BLOCK'")],
             notes=("ClaimPolicy is required only when IsManualPolicy = true (policy not held in InsureMO). "
                    "**Confirmed live:** using a `PolicyNo` that already exists as a normal InsureMO policy alongside `IsManualPolicy: true` returned `MO-Claim-Info-E0002 \"The policy does not exist!\"` - "
                    "manual-policy mode looks for that policy among manually-entered ones specifically, so it doesn't find a real automatic policy under the same number. Use a `PolicyNo` that genuinely isn't in InsureMO for this variant. Not retested with one, since the base API is permission-blocked regardless.")),
    ],
))

# ---- API-29 / API-30 / API-31 --------------------------------------------
# Confirmed live on trialx, 28 Sep 2026: a literally empty body {} throws HTTP 500 "Missing the
# required parameter 'claimQueryRequestCondition'" even though every field is documented
# optional - {"PageNo": 1, "PageSize": 5} alone is enough to avoid that and get a real 200.
# The real success envelope is {"Model": {"ClaimList": [...], "PageNo", "PageSize", "Total"},
# "Status": "OK"} - Results/ElementsInCurrentPage (guessed in the spec) is wrong; ClaimList is right.
CLAIM_Q_MAND = {"PageNo": 1, "PageSize": 5}
CLAIM_Q_FULL = {"ClaimNo": "{{claimNo}}", "PolicyNo": "{{PolicyNo}}", "CaseStatus": "{{caseStatus}}", "ClaimantName": "John Smith", "InsuredName": "John Smith", "PolicyHolderName": "John Smith", "EcsPolicyHolderIdNo": "A1234567", "ProductCode": "{{productCode}}", "ProductVersion": "1.0", "ProductLineCode": "{{productLine}}", "PolicyOrgCode": "10002", "RiskName": "Risk 1", "AccidentTimeFrom": "2026-01-01T00:00:00", "AccidentTimeTo": "2026-12-31T23:59:59", "NoticeTimeFrom": "2026-01-01T00:00:00", "NoticeTimeTo": "2026-12-31T23:59:59", "UpdateTimeFrom": "2026-01-01T00:00:00", "UpdateTimeTo": "2026-12-31T23:59:59", "PageNo": 1, "PageSize": 10}
CLAIM_SETS = ("const list = (b.Model && (b.Model.ClaimList || b.Model.Results || b.Model.ElementsInCurrentPage)) || [];\n"
              "const c = Array.isArray(list) ? list[0] : null;\n"
              "if (c && c.ClaimNo) pm.collectionVariables.set('claimNo', c.ClaimNo);\n"
              "if (c && (c.ClmPolicyId || c.ClaimPolicyId)) pm.collectionVariables.set('clmPolicyId', c.ClmPolicyId || c.ClaimPolicyId);")
APIS.append(dict(
    id="API-29", title="Claim Search API", owner="EasyClaims Team",
    endpoint="POST /platform/api-orchestration/v1/flow/ECS_claim_queryClaimForScenes",
    requests=[dict(name="Claim Search", method="POST", path="/platform/api-orchestration/v1/flow/ECS_claim_queryClaimForScenes",
                   mand=dict(body=CLAIM_Q_MAND), full=dict(body=CLAIM_Q_FULL),
                   checks=ENVELOPE_ATT, sets=CLAIM_SETS,
                   notes=("**Confirmed live on trialx, 28 Sep 2026:** a completely empty body (`{}`, matching \"every field is optional\") throws a 500 "
                          "\"Missing the required parameter 'claimQueryRequestCondition'\" - fixed here to `{\"PageNo\": 1, \"PageSize\": 5}`, confirmed working with real data. "
                          "**Doc fix:** the real success envelope is `Model.ClaimList[]`, not `Model.Results[]` as this doc's Response section assumes - confirmed from a live 200. Sets `claimNo` and `clmPolicyId`."))],
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
             mand=dict(body=CLAIM_Q_MAND), full=dict(body={"ClaimNo": "{{claimNo}}", "PolicyNo": "{{PolicyNo}}", "CaseStatus": "{{caseStatus}}", "ClaimantName": "John Smith", "InsuredName": "John Smith", "PolicyHolderName": "John Smith", "EcsPolicyHolderIdNo": "A1234567", "ProductCode": "{{productCode}}", "ProductVersion": "1.0", "ProductLineCode": "{{productLine}}", "AccidentTimeFrom": "2026-01-01T00:00:00", "AccidentTimeTo": "2026-12-31T23:59:59", "NoticeTimeFrom": "2026-01-01T00:00:00", "NoticeTimeTo": "2026-12-31T23:59:59", "UpdateTimeFrom": "2026-01-01T00:00:00", "UpdateTimeTo": "2026-12-31T23:59:59", "PageNo": 1, "PageSize": 10}),
             checks=ENVELOPE_ATT, sets=CLAIM_SETS,
             notes="Same fix as API-29: an empty body 500s on trialx; `{\"PageNo\": 1, \"PageSize\": 5}` works."),
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
             checks=ENVELOPE_SNS,
             notes="Same endpoint as API-03's Send MFA SMS - **confirmed live on trialx: the real account/signature/template pass every validation, but trialx's own AWS SNS endpoint is broken**, so no message actually sends. See API-03 for the full evidence."),
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
# Confirmed on trialx (28 Sep 2026): several configured code tables (AccountNature, Bank,
# Department, Org, ...) return only BusinessCodeTable with no BusinessCodeTableValueList
# key at all when the table has zero rows on this tenant - that is not an error, so the
# values list is not a hard check, only the envelope's own presence.
CT_CHECKS = [("body is JSON array", "Array.isArray(b)"),
             ("BusinessCodeTable present", "b.length > 0 && !!b[0].BusinessCodeTable")]


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
                        tests=t_struct("CODETABLES", CT_CHECKS) + "\nif (Array.isArray(b)) { const got = b.map(x => (x.BusinessCodeTable || {}).Name); console.log('Code tables returned: ' + got.length + ' / " + str(len(names)) + "'); pm.collectionVariables.set('codeTablesMissing', JSON.stringify(" + json.dumps(names) + ".filter(n => !got.includes(n)))); }",
                        key="ct-all")]
    ct_items.append(request("Load code table values filtered (data/list/byName)", "POST", CT_DATA_PATH,
                            query=[q("codeTableName", "SChannelStatus")], body={"CodeTableName": "SChannelStatus", "ConditionMap": {}, "Keyword": ""},
                            headers=[h("x-mo-lang-id", "en_US", "Optional language", disabled=True)],
                            desc="Runtime variant with ConditionMap / Keyword filtering (InsureMO iTables runtime API). Swap the code table name as needed.",
                            tests=t_struct("CODETABLE-DATA", [("body present", "true")]), key="ct-data"))
    per_ct = []
    for n in names:
        src, uses, vals = CODE_TABLES[n]
        d = (f"**Code table `{n}`** ({src})\n\nUsed by:\n" + "\n".join(f"* {u}" for u in uses) +
             ("\n\nValues named in the spec text (confirm against trialx - not saved as an example here): " + ", ".join(f"`{c}` {dd}" for c, dd in vals) if vals else "\n\nValues not published in the spec - load from trialx."))
        per_ct.append(request(f"{n}", "POST", CT_PATH, body=[{"CodeTableName": n}], desc=d,
                              tests=t_struct(f"CT {n}", CT_CHECKS), key=f"ct-{n}"))
    svc_items = [it for it in per_ct if it["name"] in svc]
    ct_only = [it for it in per_ct if it["name"] not in svc]

    dt_items = [
        request("Data table - Load Product list ({{ProductListTable}})", "POST", "/platform/dd/public/datatable/v1/dataTableVoList/byNameList",
                body=[{"DataTableName": "{{ProductListTable}}", "ConditionMap": {"ProductCode": "1001"}}],
                desc="Data table behind API-10 (products under a product code 1001 / 1005). Table name TBC by the Config/Apps team.",
                tests=t_struct("DT ProductList", IS_ARRAY), key="dt-product"),
        request("Data table - Load Plan list ({{PlanListTable}})", "POST", "/platform/dd/public/datatable/v1/dataTableVoList/byNameList",
                body=[{"DataTableName": "{{PlanListTable}}"}],
                desc="Data table for Load Plan (API-10 use case). Table name TBC by the Config/Apps team.",
                tests=t_struct("DT PlanList", IS_ARRAY), key="dt-plan"),
        request("Data table - runtime data by name", "POST", "/platform/dd/public/datatable/v1/data/list/byName",
                body={"dataTableName": "{{ProductListTable}}", "conditionMap": {"ProductCode": "1001"}},
                desc="Cached runtime read of one data table (iTables runtime API). Note the camelCase body keys used by this endpoint.",
                tests=t_struct("DT runtime", [("body present", "true")]), key="dt-runtime"),
    ]
    rt_items = [request("Rate/config table - Packages ({{PackageTable}})", "POST", "/platform/ratetable/rate/v1/lookup",
                        query=[q("code", "{{PackageTable}}"), q("version", "1")], body={"ProductCode": "1001"},
                        desc="Package table behind API-11 (TP / Silver / Gold / Platinum). Table code TBC.",
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
// item names are "Get Token — Mandatory" / "Get Token — Full (+ Optional)" - startsWith,
// not ===, or this never matches and Get Token ends up calling itself recursively.
const skip = pm.info.requestName.startsWith('Get Token');
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


def build():
    """One collection, both field variants per request, zero saved example responses.

    Every request carries a Mandatory item and, where the API has optional fields, a
    Full (Mandatory + Optional) item, inside the same API folder. Nothing in the
    generated JSON is a canned/spec response — pass/fail and every response shown in
    Postman only ever come from an actual call to trialx.
    """
    api_folders = []
    for api in APIS:
        items = []
        for r in api["requests"]:
            for variant, label in (("mand", "Mandatory"), ("full", "Full (+ Optional)")):
                v = r.get(variant)
                if v is None:
                    continue
                tests = r.get("custom_tests") or t_struct(api["id"], r["checks"], r.get("sets", ""))
                items.append(request(
                    f"{r['name']} — {label}", r["method"], r["path"], query=inline_values(v.get("query")), body=inline_values(v.get("body")),
                    formdata=inline_values(v.get("formdata")), headers=v.get("headers"), no_auth=r.get("no_auth", False),
                    desc=desc(api["id"], api["title"], f"{r['method']} {r['path']}", api["owner"], label, r.get("notes", "")),
                    tests=tests, key=f"{variant}-{api['id']}-{r['name']}"))
        for r in api.get("full_only", []):
            tests = r.get("custom_tests") or t_struct(api["id"], r["checks"], r.get("sets", ""))
            items.append(request(
                f"{r['name']} — Full (+ Optional)", r["method"], r["path"], query=inline_values(r["full"].get("query")),
                body=inline_values(r["full"].get("body")), formdata=inline_values(r["full"].get("formdata")), headers=r["full"].get("headers"),
                no_auth=r.get("no_auth", False),
                desc=desc(api["id"], api["title"], f"{r['method']} {r['path']}", api["owner"], "Full (+ Optional), conditional", r.get("notes", "")),
                tests=tests, key=f"full-only-{api['id']}-{r['name']}"))
        api_folders.append(folder(f"{api['id']} {api['title']}", items,
                                  f"{api['endpoint']}  \nOwner: {api['owner']}" + code_table_md([api["id"]])))
    api_folders.sort(key=lambda f: f["name"])
    return {
        "info": {
            "_postman_id": uid("collection", "trialx-single"),
            "name": "Trialx - Portal Integration APIs (all 34)",
            "description": (
                "Portal Integration API Specification v0.2 - all 34 APIs on InsureMO tenant **trialx**, "
                "one collection, Mandatory and Full (+ Optional) requests together in each API folder.\n\n"
                "**No example responses are saved anywhere in this collection.** Every request has only "
                "structure tests; a request only shows PASS if trialx itself returns a 2xx response whose "
                "shape matches the spec. A failing test names exactly what trialx returned instead, so you "
                "can tell a real error apart from a place the spec documentation needs correcting.\n\n"
                "1. Import `Trialx.postman_environment.json`, select it, fill `username` / `password` (Machine User).\n"
                "2. Any request auto-fetches a token (collection pre-request script). Or run *API-02 > Get Token*.\n"
                "3. Run the whole collection in order (Collection Runner / Newman): search requests store the "
                "signed IDs and other real trialx data (channelId, policyId, customerNo, ...) that the load "
                "requests need, so later requests use data that is actually present in trialx.\n"
                "4. Export the run report and read it with `summarize_run.py` for a plain PASS / error / "
                "doc-update table.\n\n"
                "See `STRUCTURE-CHECK.md` for the discrepancies already found by reading the spec, and for "
                "which routes 404 on trialx before you even add a token."),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
        "event": [{"listen": "prerequest", "script": {"type": "text/javascript", "exec": PRE_REQUEST.strip().split("\n")}}],
        "variable": [{"key": k, "value": ""} for k in CHAIN_VARS],
        "item": api_folders + [load_tables_folder()],
    }


# Module-level so both environment() and the literal-value substitution below (which bakes
# every confirmed search/filter parameter straight into each request, so it reads as a real
# value instead of a {{placeholder}}) share one source of truth.
ENV_DEFAULTS = [
    ("baseUrl", "https://portal-gw.insuremo.com", "default", "InsureMO portal API gateway (trialx tenant domain trialx-gimc.insuremo.com)"),
    ("tenantCode", "trialx", "default", ""),
    ("username", "", "default", "Machine User account name"),
    ("password", "", "secret", "Machine User password"),
    ("mobileNo", "+10000000000", "default", ""),
    ("otpCode", "123456", "default", "Code the user typed"),
    ("portalOtp", "123456", "default", "OTP generated by the portal (Option A)"),
    # Confirmed real values on trialx (28 Sep 2026, supplied by the tenant admin): these pass
    # every SNS validation, but sending still fails - trialx's own AWS SNS endpoint is broken
    # (see API-03's Send MFA SMS notes). Kept as the real defaults so a retest, once the SNS
    # integration is fixed, needs no further lookup.
    ("smsAccount", "account", "default", "Confirmed real SNS SMS account name on trialx"),
    ("signName", "tyung", "default", "Confirmed real SNS SMS signature on trialx"),
    ("otpTemplateCode", "ebao_sms_test_template", "default", "Confirmed real SNS SMS template code on trialx (alternative: \"ebao sms test template 2\")"),
    ("emailAccount", "", "default", "SNS email account"),
    ("customerEmail", "customer@example.com", "default", ""),
    ("payerCode", "", "default", ""),
    ("agentCode", "", "default", ""),
    ("customerNo", "", "default", ""),
    ("indiCustomerId", "", "default", "Individual customer ID"),
    ("orgCustomerId", "", "default", "Organisation customer ID"),
    # productCode: confirmed live 28 Sep 2026 - "TBTI" (the spec's own sample product) does
    # not exist on trialx; "FCMOTOR" does and returns a real product schema. Other real
    # product codes seen on trialx: MIE, TRAVEL, RPO01_RK, CI0001.
    ("productCode", "FCMOTOR", "default", "Confirmed real product code on trialx (TBTI from the spec does not exist here)"),
    ("productLine", "Travel", "default", ""),
    ("versionDate", "2026-01-01T00:00:00", "default", ""),
    ("ProductListTable", "", "default", "Data table name for Load Product (TBC)"),
    ("PlanListTable", "", "default", "Data table name for Load Plan (TBC)"),
    ("PackageTable", "", "default", "Rate table code for packages (TBC)"),
    # businessType/businessNo: confirmed live 28 Sep 2026 - AttachBusinessType has exactly
    # one configured value ("001" = Claim) on trialx, so that is the only businessType that
    # will not be rejected. businessNo default is a real claim number confirmed to exist.
    ("businessType", "001", "default", "Confirmed real AttachBusinessType code on trialx (Claim - the only one configured)"),
    ("businessNo", "CRPO01_RK202600000308", "default", "Confirmed real claim number on trialx with businessType 001"),
    ("directory", "", "default", "Document type node from API-25"),
    ("reportChannel", "", "default", "FNOL report channel (TBC)"),
    ("operationType", "", "default", "FNOL operation type (TBC)"),
    ("lossCause", "", "default", "CauseOfLoss code"),
    ("claimType", "", "default", "ClaimType code"),
    ("fnolType", "", "default", "ClaimFnolType code"),
    ("caseStatus", "", "default", "ClaimStatus code"),
]

# Variables that stay as {{placeholders}} in every request even though they have a value:
# auth/connection plumbing, not a "search parameter" - and the chain variables (set live by a
# prior request's test script - API-01 -> channelId, API-06 -> collectionId, etc.), which must
# stay templated or the automatic chaining documented in README.md stops working.
_NEVER_INLINE = {"baseUrl", "tenantCode", "username", "password"} | set(CHAIN_VARS)
# Only inline a variable where a real, confirmed value exists; an empty default ("" - a value
# nobody has supplied, e.g. lossCause, directory) is left as {{placeholder}} on purpose, since
# replacing it with an empty string would silently blank the field rather than flag it as unset.
SUBSTITUTE_VALUES = {k: v for k, v, _, _ in ENV_DEFAULTS if v and k not in _NEVER_INLINE}
_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def inline_values(obj):
    """Replace every {{var}} in a request body/query/formdata with its real confirmed value
    (SUBSTITUTE_VALUES), recursively. Vars with no confirmed value, and auth/chain vars, are
    left as {{placeholder}} untouched."""
    if isinstance(obj, str):
        def sub(m):
            return SUBSTITUTE_VALUES.get(m.group(1), m.group(0))
        return _VAR_RE.sub(sub, obj)
    if isinstance(obj, dict):
        return {k: inline_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [inline_values(v) for v in obj]
    return obj


def environment():
    vals = ENV_DEFAULTS
    return {"id": uid("env", "trialx"), "name": "Trialx (InsureMO)",
            "values": [{"key": k, "value": v, "type": t, "enabled": True, **({"description": d} if d else {})} for k, v, t, d in vals],
            "_postman_variable_scope": "environment"}


OLD_FILES = [
    "Trialx-Portal-APIs-Mandatory.postman_collection.json",
    "Trialx-Portal-APIs-Full-Optional.postman_collection.json",
]


def main():
    out = {
        "Trialx-Portal-APIs.postman_collection.json": build(),
        "Trialx.postman_environment.json": environment(),
    }
    for fn, data in out.items():
        with open(os.path.join(HERE, fn), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("wrote", fn)
    for fn in OLD_FILES:
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            os.remove(p)
            print("removed superseded file", fn)


if __name__ == "__main__":
    main()
