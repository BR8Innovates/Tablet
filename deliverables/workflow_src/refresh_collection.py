#!/usr/bin/env python3
"""Re-runs every request of the Sohar Bank collection live (as the signed-in imo user, role checks off), saves fresh examples, adds the workflow / portal APIs."""
import json, os, re, sys, copy, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
sys.path.insert(0, "."); import wf
from pm_common import example, url_of
SRC = "/home/user/Tablet/deliverables/Sohar_Bank.postman_collection.json"
col = json.load(open(SRC))
V = {v["key"]: v["value"] for v in col["variable"]}
now = datetime.now(timezone.utc); eff = now + timedelta(days=1); exp = eff.replace(year=eff.year + 1) - timedelta(days=1)
ymd = lambda d: d.strftime("%Y-%m-%d")
V.update(applyDate=ymd(now), effectiveDate=ymd(eff), expiry1y=ymd(exp) + "T23:59:59", cancelDate=ymd(eff + timedelta(days=30)),
         monthStart=now.strftime("%Y-%m-01"), monthEnd=ymd((now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)))
BASE = V["baseUrl"]; N = [int(time.time() * 1000)]
def sub(s): return re.sub(r"\{\{(\w+)\}\}", lambda m: str(V.get(m.group(1), m.group(0))), s)
def run(it):
    rq = it["request"]; url = sub(rq["url"]["raw"]); body = sub(rq["body"]["raw"]).encode() if rq.get("body") else None
    r = urllib.request.Request(url, data=body, method=rq["method"], headers={"Authorization": "Bearer " + wf.TOK, "Content-Type": "application/json"})
    try: resp = urllib.request.urlopen(r, timeout=300); st = resp.status; data = resp.read(); ct = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e: st = e.code; data = e.read(); ct = e.headers.get("Content-Type", "")
    if "pdf" in ct or data[:4] == b"%PDF": out = {"_pdf": True, "_bytes": len(data), "_contentType": ct}
    else:
        try: out = json.loads(data)
        except Exception: out = {"_raw": data[:200].decode("utf8", "replace")}
    return st, out
def save(it, st, out): it["response"] = [example(it["request"], st, out)]
def newapp(suffix=""): N[0] += 1; V["applicationNo"] = str(N[0]); return suffix
report = []
def flow(items, label):
    for it in items:
        nm = it["name"]
        if "Create Proposal (application)" in nm or "Get Plans" in nm: pass
        if nm.split(". ", 1)[1] in ("Get Plans",): newapp()
        st, out = run(it); save(it, st, out)
        n = nm.split(". ", 1)[1]
        if st == 200 and isinstance(out, dict):
            if n.startswith("Create Proposal (application)"): V["proposalNo"] = out.get("ProposalNo", "")
            if n.startswith("Create Proposal (to be rejected)"): V["rejectProposalNo"] = out.get("ProposalNo", "")
            if n.startswith("Issue"): V["policyNo"] = out.get("PolicyNo", "")
            if n.startswith("Cancel Check"): V["requestNo"] = out.get("RequestNo", "")
        report.append((label, nm, st)); print(label, nm, st, flush=True)
        if st != 200: print("   ", json.dumps(out)[:300])
for f in col["item"]:
    if f["name"] in ("0. Get Token",) : continue
    if f["name"] == "Common":
        flow(f["item"], "Common"); continue
    # per product: new application number for the flow
    N[0] += 1; V["applicationNo"] = str(N[0])
    # the reject proposal uses applicationNo + R: unique per product because applicationNo changes
    flow(f["item"], f["name"])
# ---- workflow / portal folder (HC001 data)
hc = next(f for f in col["item"] if f["name"] == "HC001")["item"]
def tmpl(n): return copy.deepcopy(next(i for i in hc if i["name"].split(". ", 1)[1].startswith(n)))
def mk(name, method, path, body, tests, desc=""):
    it = copy.deepcopy(hc[10]); it["name"] = name; rq = it["request"]; rq["method"] = method
    rq["url"] = url_of(path, None)
    if body is None: rq.pop("body", None)
    else: rq["body"] = {"mode": "raw", "raw": json.dumps(body, indent=4), "options": {"raw": {"language": "json"}}}
    if desc: rq["description"] = desc
    it["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}]; it["response"] = []
    return it
ok = ["pm.test('Status is 200', function () { pm.response.to.have.status(200); });"]
CH = "{{channelCode}}"
w = []
w.append(mk("1. Who am I (me)", "GET", "/up/me", None, ok, "Caller from the token with roles (Roles is absent when the user holds none). With RoleEnforcement N every signed-in user, machine users included, can call every API."))
w.append(mk("2. Proposal queue", "POST", "/up/worklist", {"ChannelCode": CH, "Type": "PROPOSAL", "Status": "PENDING", "PageNo": 1, "PageSize": 10}, ok))
w.append(mk("3. Cancellation queue", "POST", "/up/worklist", {"ChannelCode": CH, "Type": "CANCELLATION", "Status": "PENDING", "PageNo": 1, "PageSize": 10}, ok))
w.append(mk("4. My submissions", "POST", "/up/worklist", {"ChannelCode": CH, "Type": "MINE", "Status": "ALL", "PageNo": 1, "PageSize": 10}, ok))
w.append(mk("5. Dashboard - summary", "POST", "/up/dashboard", {"ChannelCode": CH, "Section": "SUMMARY", "Scope": "ALL"}, ok))
w.append(mk("6. Dashboard - commission (HC001)", "POST", "/up/dashboard", {"ChannelCode": CH, "Section": "COMMISSION", "ProductCode": "{{HC001_productCode}}", "Scope": "ALL"}, ok))
w.append(mk("7. Share quotation (Email + SMS)", "POST", "/up/share", {"ChannelCode": CH, "DocType": "QUOTATION", "Channel": "BOTH", "Email": "customer@example.com", "Mobile": "96899999999",
   "Details": {"InsuredName": "{{HC001_insuredName}}", "ProductName": "Hospital Cash Benefit", "PlanName": "Plan 1", "Premium": "100.000", "EffectiveDate": "{{effectiveDate}}"}}, ok))
c2 = tmpl("2. Create Proposal (application)") if False else None
for t_ in ("Create Proposal (application)", "Issue Policy", "Cancel Check"): pass
p = tmpl("Create Proposal (application)"); p["name"] = "8. Create Proposal (for the workflow)"; p["event"][0]["script"]["exec"] = [l.replace("'proposalNo'", "'wfProposalNo'") for l in p["event"][0]["script"]["exec"]]
p["request"]["body"]["raw"] = p["request"]["body"]["raw"].replace("{{applicationNo}}", "{{applicationNo}}W")
iss = tmpl("Issue Policy"); iss["name"] = "9. Issue Policy (for the workflow)"; iss["request"]["body"]["raw"] = iss["request"]["body"]["raw"].replace("{{proposalNo}}", "{{wfProposalNo}}")
iss["event"][0]["script"]["exec"] = [l.replace("'policyNo'", "'wfPolicyNo'") for l in iss["event"][0]["script"]["exec"]]
w += [p, iss]
w.append(mk("10. Share policy (Email)", "POST", "/up/share", {"ChannelCode": CH, "DocType": "POLICY", "Channel": "EMAIL", "PolicyNo": "{{wfPolicyNo}}"}, ok))
w.append(mk("11. Cancel Check (raise request)", "POST", "/up/cancel-check", {"PolicyNo": "{{wfPolicyNo}}", "CancellationDate": "{{cancelDate}}", "CancelReason": "Customer request", "ChannelCode": CH}, ok + ["pm.collectionVariables.set('wfRequestNo', pm.response.json().RequestNo);"]))
w.append(mk("12. Cancel Detail (pending request)", "POST", "/up/cancel-detail", {"ChannelCode": CH, "PolicyNo": "{{wfPolicyNo}}"}, ok))
w.append(mk("13. Cancel Approve (Decision REJECT)", "POST", "/up/cancel-approve", {"PolicyNo": "{{wfPolicyNo}}", "RequestNo": "{{wfRequestNo}}", "Decision": "REJECT", "ChannelCode": CH}, ok))
N[0] += 1; V["applicationNo"] = str(N[0])
for it in w:
    st, out = run(it); save(it, st, out)
    n = it["name"]
    if st == 200 and isinstance(out, dict):
        if n.startswith("8."): V["wfProposalNo"] = out.get("ProposalNo", "")
        if n.startswith("9."): V["wfPolicyNo"] = out.get("PolicyNo", "")
        if n.startswith("11."): V["wfRequestNo"] = out.get("RequestNo", "")
    report.append(("Workflow", n, st)); print("Workflow", n, st, flush=True)
    if st != 200: print("   ", json.dumps(out)[:300])
col["item"] = [i for i in col["item"] if i["name"] != "Workflow and portal"] + [{"name": "Workflow and portal", "item": w, "description": "Staff-portal APIs (maker / checker queues, dashboard, share, cancellation detail). Role checks are off (RoleEnforcement N): any signed-in user can call them."}]
for k in ("wfProposalNo", "wfPolicyNo", "wfRequestNo"):
    if not any(v["key"] == k for v in col["variable"]): col["variable"].append({"key": k, "value": ""})
col["info"]["description"] = col["info"]["description"].replace("plus common utility APIs.", "plus common utility APIs and the staff-portal APIs (me, worklist, dashboard, share, cancel-detail).") + "\n\nAccess: role checks are switched off (UP_ApiConfig RoleEnforcement = N). Any user or machine user that can obtain a platform token can call every API; no role rows are needed. Examples were re-run live on " + ymd(now) + " (MC tenant)."
json.dump(col, open("final/Sohar_Bank.postman_collection.json", "w"), indent=2, ensure_ascii=False)
json.dump(report, open("final/collection_run.json", "w"))
print("non-200:", [r for r in report if r[2] != 200])
