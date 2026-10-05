import sys, json, time; sys.path.insert(0, ".")
import wf
from datetime import datetime, timedelta
eff = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
PRODUCTS = [("UPPA001", "1", "2"), ("UPPA001", "2", "2"), ("TL001", "1", "2"), ("FP001", "1", "2"), ("HC001", "1", "2"), ("CI001", "1", "2"), ("LP001", "1", "3"), ("DH001", "1", "2")]
def body(code, sub, mode, full):
    risk = {"ProductElementCode": "R00001", "DateOfBirth": "1990-05-05", "Gender": "2" if code == "FP001" else "1"}
    if full: risk.update({"InsuredName": "Test User", "Salutation": "1", "ResidentStatus": "1"})
    b = {"ProductCode": code, "ProductSubcode": sub, "ChannelCode": "SOHAR", "PremiumModeCode": mode, "EffectiveDate": eff, "PolicyLobList": [{"ProductCode": code, "PolicyRiskList": [risk]}]}
    if full: b.update({"ApplyDate": datetime.now().strftime("%Y-%m-%d"), "BranchCode": "001", "UserName": "portal", "PolicyTerm": 1, "ExpiryDate": eff[:3] + str(int(eff[3]) + 1) + eff[4:] + "T23:59:59"})
    return b
out = []
for code, sub, mode in PRODUCTS:
    for full in (False, True):
        st, j, t = wf.call("POST", "/up/get-plans", body(code, sub, mode, full))
        plans = len(((((j.get("PolicyLobList") or [{}])[0].get("PolicyRiskList") or [{}])[0]).get("PlanList") or [])) if st == 200 else 0
        print(f"{code}/{sub} {'full   ' if full else 'minimal'} -> {st} {t}s plans={plans}", (json.dumps(j.get("errors") or j.get("message"))[:230] if st != 200 else ""))
        out.append((code, sub, full, st, plans))
json.dump(out, open("workflow/gp_validate_%s.json" % sys.argv[1], "w"))
