import json, sys, copy
sys.argv = [sys.argv[0]]
from gen_samples import *
V = json.load(open("samples_variants.json")); ctx = V["ctx"]; CASES[:] = V["cases"]
hc = ctx["HC001-1"]; pol_ok = hc["pol"]; pno_hc = hc["pno"]
pol_live = next(x["body"]["PolicyNo"] for x in CASES if x["folder"].startswith("HC001-1") and x["name"].startswith("18. Cancel Check"))
pa = ctx["UPPA001-1"]; pol_cancelled = pa["pol"]
def hc_body(appno, mutate=None, term="1"):
    rq = template("HC001", "1", "02_proposal"); b = json.loads(lit(json.dumps(rq["body"]), {"channelCode": "SOHAR", "orgCode": "1", "applyDate": APPLY, "effectiveDate": EFFS}))
    b = person(b, "M4", appno, term)
    if mutate: mutate(b)
    return b
def risk(b): return b["PolicyLobList"][0]["PolicyRiskList"][0]
F = "Staff portal and common APIs"; E_ = "Error cases"
call(F, "1. Who am I", "me", "GET", "/up/me", note="Caller identity and roles from the platform token.")
call(F, "2. Proposal queue (pending)", "worklist", "POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "PROPOSAL", "Status": "PENDING", "PageNo": 1, "PageSize": 5})
call(F, "3. Cancellation queue (pending)", "worklist", "POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "CANCELLATION", "Status": "PENDING", "PageNo": 1, "PageSize": 5})
call(F, "4. My submissions", "worklist", "POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "MINE", "Status": "ALL", "PageNo": 1, "PageSize": 5})
call(F, "5. Dashboard - summary", "dashboard", "POST", "/up/dashboard", {"ChannelCode": "SOHAR", "Section": "SUMMARY", "Scope": "ALL"})
call(F, "6. Dashboard - commission of one product", "dashboard", "POST", "/up/dashboard", {"ChannelCode": "SOHAR", "Section": "COMMISSION", "ProductCode": "HC001", "Scope": "ALL"})
call(F, "7. Share a quotation by Email and SMS", "share", "POST", "/up/share", {"ChannelCode": "SOHAR", "DocType": "QUOTATION", "Channel": "BOTH", "ProductCode": "HC001", "ProductSubcode": "1", "Email": "customer@example.com", "Mobile": "96899999999", "Details": {"InsuredName": "Hamad Al Kindi", "ProductName": "Hospital Cash Benefit", "PlanName": "Plan 1", "Premium": "70.000", "EffectiveDate": EFFS}})
call(F, "8. Master data - insurer", "list-master-table", "POST", "/up/list-master-table", {"DataTableName": "UP_Carrier", "ChannelCode": "SOHAR"})
call(F, "9. Master data - relationship", "list-master-table", "POST", "/up/list-master-table", {"DataTableName": "Relationship", "ChannelCode": "SOHAR"})
call(F, "10. Master data - one value", "list-master-table", "POST", "/up/list-master-table", {"DataTableName": "Relationship", "Id": "2", "ChannelCode": "SOHAR"})
call(F, "11. Commission by policy", "commission-query", "POST", "/up/commission-query", {"PolicyNo": pol_ok, "ChannelCode": "SOHAR"})
call(F, "12. Commission by product configuration", "commission-query", "POST", "/up/commission-query", {"ProductCode": "FP001", "ProductSubcode": "1", "ChannelCode": "SOHAR"})
call(F, "13. Commission by product, variant and plan", "commission-query", "POST", "/up/commission-query", {"ProductCode": "FP001", "ProductSubcode": "1", "PlanId": "2", "ChannelCode": "SOHAR"})
call(F, "14. Commission for a period", "commission-query", "POST", "/up/commission-query", {"ProductCode": "HC001", "FromDate": APPLY, "ToDate": EFFS, "PageNo": 1, "PageSize": 5, "ChannelCode": "SOHAR"})
ms = TODAY.replace(day=1).isoformat(); me_ = (TODAY.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
feed = {"Conditions": {"ProductCode": "HC001"}, "FromRangeConditions": {"EffectiveDate": ms + "T00:00:00"}, "ToRangeConditions": {"EffectiveDate": me_.isoformat() + "T23:59:59"}, "Module": "Policy", "PageNo": 1, "PageSize": 10, "SearchType": "Policy", "SortField": "index_time", "SortType": "desc", "ChannelCode": "SOHAR"}
call(F, "15. Policy feed file (Excel)", "generate-feedfile", "POST", "/up/generate-feedfile", feed)
call(F, "16. Policy feed file (JSON)", "generate-feedfile", "POST", "/up/generate-feedfile", {**feed, "OutputFormat": "JSON"})
call(F, "17. Policy documents - data merged into the template", "doc_generation", "POST", "/up/doc_generation", {"DocType": "Policy", "PolicyNo": pol_ok, "ProductSubcode": "1", "ChannelCode": "SOHAR", "PreviewData": "Y"})
# ---------------- error cases
a = "APP" + TODAY.strftime("%y%m%d") + "9"
def wrong_money(b):
    b["DuePremium"] = 1; b["PolicyLobList"][0]["DuePremium"] = 1; b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]["PolicyCoverageList"][0]["SumInsured"] = 999999
call(F, "18. Create proposal with a wrong premium and sum insured (the platform recalculates)", "proposal", "POST", "/up/proposal", hc_body("APP" + TODAY.strftime("%y%m%d") + "9R1", wrong_money), note="Shows that DuePremium and SumInsured sent by the caller do not decide the price.")
call(E_, "E1. Required field missing (PlanId removed)", "proposal", "POST", "/up/proposal", hc_body(a + "01", lambda b: (b.pop("PlanId"), )))
call(E_, "E2. Insured below the minimum age (born 2010)", "proposal", "POST", "/up/proposal", hc_body(a + "02", lambda b: risk(b).update({"DateOfBirth": "2010-05-01"})))
call(E_, "E3. Unknown plan id (9)", "proposal", "POST", "/up/proposal", hc_body(a + "03", lambda b: (b.update({"PlanId": 9}), b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0].update({"PlanId": 9}))))
call(E_, "E4. Premium mode not allowed for the product (3)", "proposal", "POST", "/up/proposal", hc_body(a + "04", lambda b: b.update({"PremiumModeCode": "3"})))
call(E_, "E5. ProposalNo sent when creating a proposal", "proposal", "POST", "/up/proposal", hc_body(a + "05", lambda b: b.update({"ProposalNo": "PRHC00100000001"})))
call(E_, "E6. Value rejected by the platform (gender 9)", "get-plans", "POST", "/up/get-plans", hc_body(a + "06", lambda b: risk(b).update({"Gender": "9"})))
call(E_, "E7. Invalid character in a field", "proposal", "POST", "/up/proposal", hc_body(a + "07", lambda b: risk(b).update({"InsuredName": "Hamad {Al Kindi}"})))
# beneficiary shares not 100: personal accident variant, update step
rq = template("UPPA001", "1", "03_update-proposal"); 
def pa_update():
    app = "APP" + TODAY.strftime("%y%m%d") + "9PA"
    rq = template("UPPA001", "1", "02_proposal"); b = json.loads(lit(json.dumps(rq["body"]), {"channelCode": "SOHAR", "orgCode": "1", "applyDate": APPLY, "effectiveDate": EFFS})); b = person(b, "M1", app, "1")
    st, r = call(E_, "x", "proposal", "POST", "/up/proposal", b, keep=False); pn = r.get("ProposalNo")
    u = copy.deepcopy(b); u["ProposalNo"] = pn; u["PolicyLobList"][0]["PolicyRiskList"][0]["BeneficiaryList"][0]["Share"] = "90"
    call(E_, "E8. Beneficiary shares do not total 100", "update-proposal", "POST", "/up/update-proposal", u)
    return pn
pa_update()
call(E_, "E9. Policy not found", "load-policy", "GET", "/up/load-policy?policyNo=PO00000000000&ChannelCode=SOHAR")
call(E_, "E10. Proposal already issued", "issue", "POST", "/up/issue", {"ProposalNo": pno_hc, "ProductCode": "HC001", "ChannelCode": "SOHAR"})
call(E_, "E11. Proposal belongs to another product", "issue", "POST", "/up/issue", {"ProposalNo": pno_hc, "ProductCode": "TL001", "ChannelCode": "SOHAR"})
call(E_, "E12. Cancellation of a policy that is already cancelled", "cancel-check", "POST", "/up/cancel-check", {"PolicyNo": pol_cancelled, "CancellationDate": CANCEL_PRORATA, "CancelReason": "Customer request", "ChannelCode": "SOHAR"})
call(E_, "E13. Cancellation date before the policy start", "cancel-check", "POST", "/up/cancel-check", {"PolicyNo": pol_live, "CancellationDate": "2020-01-01", "CancelReason": "Customer request", "ChannelCode": "SOHAR"})
call(E_, "E14. No access token", "get-plans", "POST", "/up/get-plans", hc_body(a + "14"), token=None)
call(E_, "E15. Wrong HTTP method (GET on a POST API)", "get-plans", "GET", "/up/get-plans")
call(E_, "E16. Body is not valid JSON", "proposal", "POST", "/up/proposal", None, raw_body=b'{"ProductCode": "HC001", ')
json.dump(dict(cases=CASES, ctx=ctx, today=APPLY), open("samples_all.json", "w"), ensure_ascii=False, indent=1)
print("done", len(CASES))
