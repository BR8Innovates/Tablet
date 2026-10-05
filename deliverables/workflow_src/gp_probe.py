import sys, json; sys.path.insert(0, ".")
import wf
from datetime import datetime, timedelta
eff = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
def b(**risk):
    r = {"ProductElementCode": "R00001", "DateOfBirth": "1990-05-05", "Gender": "1"}; r.update(risk)
    return {"ProductCode": "HC001", "ProductSubcode": "1", "ChannelCode": "SOHAR", "PremiumModeCode": "2", "EffectiveDate": eff, "PolicyLobList": [{"ProductCode": "HC001", "PolicyRiskList": [r]}]}
cases = {"valid": b(), "bad gender code 9": b(Gender="9"), "unknown risk element": b(ProductElementCode="ZZZ"), "bad id type 7": b(IdType="7"), "bad residency 9": b(ResidentStatus="9"), "bad marital 9": b(MaritalStatus="9"), "salary text": b(MonthSalaryIncome="abc")}
for k, v in cases.items():
    st, j, t = wf.call("POST", "/up/get-plans", v); print(f"{k:24} -> {st} {t}s", (json.dumps(j.get("errors") or j.get("message"))[:200] if st != 200 else "ok"))
