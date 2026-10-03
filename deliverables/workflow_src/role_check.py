#!/usr/bin/env python3
"""Role / maker-checker / notification checks on the live MC tenant. One account holds all three roles in UP_UserRole, so roles are switched by
(de)activating UP_UserRole rows and the self-approval rule by UP_ApiConfig AllowSelfApproval. Restores the table / keys at the end.
Writes workflow/role_results.json."""
import json, os, sys, subprocess, time, copy
sys.path.insert(0, "."); import wf
from datetime import datetime, timedelta, timezone
UR = "1188710773"
def imo(a): return subprocess.run(["imo"] + a + ["--profile", "portal:uponly"], capture_output=True, text=True, cwd="/home/user/Tablet")
def role_rows():
    r = json.loads(imo(["config", "datatable", "record-list", "--id", UR, "--json"]).stdout); return r if isinstance(r, list) else r.get("Records", [])
def set_roles(active):
    for r in role_rows():
        want = "Y" if r["Role"] in active else "N"
        if r["IsActive"] != want:
            r = dict(r); r["IsActive"] = want; json.dump(r, open("/tmp/urow.json", "w")); imo(["config", "datatable", "record-save", "--file", "/tmp/urow.json", "--confirm"])
def cfg(**kw): subprocess.run(["python3", "setcfg.py"] + [x for k, v in kw.items() for x in (k, v)], capture_output=True, text=True)
R = []
def check(name, cond, extra=""):
    R.append({"check": name, "ok": bool(cond), "extra": str(extra)[:300]}); print(("PASS " if cond else "FAIL ") + name, "|", str(extra)[:160], flush=True)
NOW = datetime.now(timezone.utc); EFF = NOW + timedelta(days=1)
V = {"applyDate": NOW.strftime("%Y-%m-%d"), "effectiveDate": EFF.strftime("%Y-%m-%d"), "expiry1y": (EFF.replace(year=EFF.year + 1) - timedelta(days=1)).strftime("%Y-%m-%d") + "T23:59:59", "channelCode": "SOHAR", "orgCode": "1"}
def proposal():
    s = json.dumps(json.load(open("samples/ref/HC001_1_P1/02_proposal.json"))["request"]["body"])
    V["applicationNo"] = str(int(time.time() * 1000))
    for k, v in V.items(): s = s.replace("{{%s}}" % k, v)
    return json.loads(s)
ALL = ["MAKER", "PROPOSAL_CHECKER", "CANCELLATION_CHECKER"]
try:
    set_roles(ALL); cfg(RoleEnforcement="Y", AllowSelfApproval="N")
    st, me, _ = wf.call("GET", "/up/me"); check("me returns three roles", st == 200 and sorted(me.get("Roles", [])) == sorted(ALL), me.get("Roles"))
    # maker submits
    st, p, _ = wf.call("POST", "/up/proposal", proposal()); pno = p.get("ProposalNo")
    check("maker submits proposal", st == 200 and pno, pno)
    n = p.get("Notifications", []); check("SUBMITTED alert to the Proposal Checker (dry run)", any(x["Event"] == "SUBMITTED" and x["Status"] == "DRYRUN" and x["Channel"] == "EMAIL" for x in n), n)
    st, q, _ = wf.call("POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "PROPOSAL", "Status": "PENDING", "ProductCode": "HC001", "PageSize": 5})
    check("proposal appears in the checker queue", st == 200 and any(r["ProposalNo"] == pno for r in q.get("Records", [])), [r["ProposalNo"] for r in q.get("Records", [])])
    st, m, _ = wf.call("POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "MINE", "Status": "PENDING", "PageSize": 5})
    mine = [r for r in m.get("Records", []) if r["ProposalNo"] == pno]
    check("proposal appears in 'my submissions' with the maker id", st == 200 and mine and mine[0]["MakerId"] == me["UserId"], mine and mine[0].get("Maker"))
    # maker-checker rule
    st, j, _ = wf.call("POST", "/up/issue", {"ProposalNo": pno, "ProductCode": "HC001", "ChannelCode": "SOHAR"}); check("self-approval refused (issue) = 403 UP-403", st == 403 and j.get("code") == "UP-403", j.get("message"))
    st, j, _ = wf.call("POST", "/up/proposal-reject", {"ProposalNo": pno, "ProposalRejectDesc": "self test", "ProductCode": "HC001", "ChannelCode": "SOHAR"}); check("self-rejection refused = 403", st == 403 and j.get("code") == "UP-403", j.get("message"))
    # role switch: maker only cannot issue
    set_roles(["MAKER"]); st, j, _ = wf.call("POST", "/up/issue", {"ProposalNo": pno, "ProductCode": "HC001", "ChannelCode": "SOHAR"}); check("maker-only user cannot issue = 403", st == 403 and j.get("code") == "UP-403", j.get("message"))
    st, j, _ = wf.call("POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "PROPOSAL", "PageSize": 1}); check("maker-only user cannot read the checker queue = 403", st == 403, st)
    st, j, _ = wf.call("POST", "/up/cancel-approve", {"PolicyNo": "POHC00100000068", "RequestNo": "X-001", "Decision": "APPROVE", "ChannelCode": "SOHAR"}); check("maker-only user cannot approve a cancellation = 403", st == 403, st)
    st, j, _ = wf.call("POST", "/up/update-proposal", dict(proposal(), ProposalNo=pno)); check("maker can update own proposal", st == 200, j.get("message") or j.get("ProposalNo"))
    set_roles(["PROPOSAL_CHECKER"]); st, j, _ = wf.call("POST", "/up/proposal", proposal()); check("checker-only user cannot create a proposal = 403", st == 403, st)
    st, j, _ = wf.call("POST", "/up/cancel-check", {"PolicyNo": "POHC00100000068", "CancellationDate": V["effectiveDate"], "CancelReason": "role test", "ChannelCode": "SOHAR"}); check("checker-only user cannot raise a cancellation = 403", st == 403, st)
    set_roles([]); st, j, _ = wf.call("GET", "/up/load-policy?policyNo=POHC00100000068&ChannelCode=SOHAR"); check("user without a role cannot read a policy = 403", st == 403, st)
    st, j, _ = wf.call("POST", "/up/dashboard", {"ChannelCode": "SOHAR", "Section": "SUMMARY"}); check("user without a role cannot open the dashboard = 403", st == 403, st)
    st, me2, _ = wf.call("GET", "/up/me"); check("/up/me still answers for a user without roles (Roles empty or absent)", st == 200 and not me2.get("Roles"), me2.get("Roles"))
    # approve with self-approval allowed (single test account)
    set_roles(ALL); cfg(AllowSelfApproval="Y")
    st, j, _ = wf.call("POST", "/up/issue", {"ProposalNo": pno, "ProductCode": "HC001", "ChannelCode": "SOHAR"}); pol = j.get("PolicyNo")
    check("checker issues the policy", st == 200 and pol, pol or j.get("message"))
    n = j.get("Notifications", []); ev = {(x["Recipient"], x["Channel"]): x["Status"] for x in n}
    check("ISSUED alerts to the maker and the customer (dry run)", ev.get(("MAKER", "EMAIL")) == "DRYRUN" and ev.get(("CUSTOMER", "EMAIL")) == "DRYRUN", ev)
    # reject path
    st, p2, _ = wf.call("POST", "/up/proposal", proposal()); p2no = p2.get("ProposalNo")
    st, j, _ = wf.call("POST", "/up/proposal-reject", {"ProposalNo": p2no, "ProposalRejectDesc": "premium mismatch", "ProductCode": "HC001", "ChannelCode": "SOHAR"})
    check("checker rejects with a reason", st == 200 and j.get("status") == "SUCCESS", j.get("message"))
    check("REJECTED alert to the maker", any(x["Event"] == "PROPOSAL_REJECTED" and x["Recipient"] == "MAKER" and x["Status"] == "DRYRUN" for x in j.get("Notifications", [])), j.get("Notifications"))
    st, j, _ = wf.call("POST", "/up/proposal-reject", {"ProposalNo": p2no, "ProposalRejectDesc": "", "ProductCode": "HC001", "ChannelCode": "SOHAR"}); check("reject without a reason = 400", st == 400, j.get("errors"))
    # cancellation
    cd = (EFF + timedelta(days=20)).strftime("%Y-%m-%d")
    st, c, _ = wf.call("POST", "/up/cancel-check", {"PolicyNo": pol, "CancellationDate": V["effectiveDate"], "CancelReason": "customer request", "ChannelCode": "SOHAR"}); rq = c.get("RequestNo")
    check("maker raises the cancellation request", st == 200 and rq and c.get("RequestStatus") == "PENDING", rq or c.get("message"))
    check("CANCEL_REQUESTED alert to the Cancellation Checker", any(x["Event"] == "CANCEL_REQUESTED" and x["Status"] == "DRYRUN" for x in c.get("Notifications", [])), c.get("Notifications"))
    st, d, _ = wf.call("POST", "/up/cancel-detail", {"PolicyNo": pol, "ChannelCode": "SOHAR"})
    check("cancel-detail shows requester, reason and refund", st == 200 and d.get("RequestNo") == rq and d.get("CancelReason") == "customer request" and d.get("RefundDetails", {}).get("RefundPremium") is not None, {k: d.get(k) for k in ("RequestedBy", "CanDecide")})
    st, q, _ = wf.call("POST", "/up/worklist", {"ChannelCode": "SOHAR", "Type": "CANCELLATION", "Status": "PENDING", "ProductCode": "HC001", "PageSize": 20})
    check("request appears in the cancellation queue", st == 200 and any(r.get("RequestNo") == rq for r in q.get("Records", [])), q.get("Total"))
    cfg(AllowSelfApproval="N"); st, j, _ = wf.call("POST", "/up/cancel-approve", {"PolicyNo": pol, "RequestNo": rq, "Decision": "APPROVE", "ChannelCode": "SOHAR"}); check("requester cannot approve own cancellation = 403", st == 403 and j.get("code") == "UP-403", j.get("message"))
    st, d, _ = wf.call("POST", "/up/cancel-detail", {"PolicyNo": pol, "ChannelCode": "SOHAR"}); check("cancel-detail says CanDecide = N for the requester", d.get("CanDecide") == "N", d.get("CanDecide"))
    cfg(AllowSelfApproval="Y"); st, j, _ = wf.call("POST", "/up/cancel-approve", {"PolicyNo": pol, "RequestNo": rq, "Decision": "APPROVE", "ChannelCode": "SOHAR"})
    check("Cancellation Checker approves", st == 200 and j.get("RequestStatus") == "APPROVED" and j.get("PolicyStatus", {}).get("Description") == "Cancelled", j.get("message") or j.get("RequestStatus"))
    ev = {(x["Event"], x["Recipient"], x["Channel"]): x["Status"] for x in j.get("Notifications", [])}
    check("CANCEL_APPROVED alerts to the maker and the customer", ev.get(("CANCEL_APPROVED", "MAKER", "EMAIL")) == "DRYRUN" and ev.get(("CANCEL_APPROVED", "CUSTOMER", "EMAIL")) == "DRYRUN" and ev.get(("CANCEL_APPROVED", "CUSTOMER", "SMS")) == "DRYRUN", ev)
    # not the owner (legacy proposal stamped with another id)
    st, j, _ = wf.call("POST", "/up/update-proposal", dict(proposal(), ProposalNo="PHC0010000000234")); check("a maker cannot change another maker's proposal = 403", st == 403 and j.get("code") == "UP-403", j.get("message"))
    # share + dashboard
    st, j, _ = wf.call("POST", "/up/share", {"ChannelCode": "SOHAR", "DocType": "POLICY", "Channel": "BOTH", "PolicyNo": pol, "Mobile": "96891234567"}); ev = {x["Channel"]: x["Status"] for x in j.get("Notifications", [])}
    check("share policy by email and SMS (dry run)", st == 200 and ev.get("EMAIL") == "DRYRUN" and ev.get("SMS") == "DRYRUN", ev)
    st, j, _ = wf.call("POST", "/up/share", {"ChannelCode": "SOHAR", "DocType": "POLICY", "Channel": "EMAIL", "PolicyNo": pol, "Email": "not-an-email"}); check("share with a bad email = 400", st == 400, j.get("errors"))
    st, j, _ = wf.call("POST", "/up/dashboard", {"ChannelCode": "SOHAR", "Section": "SUMMARY", "Scope": "MINE"}); check("dashboard summary (mine) answers", st == 200 and "Proposals" in j, j.get("Proposals"))
    st, j, _ = wf.call("POST", "/up/dashboard", {"ChannelCode": "SOHAR", "Section": "SUMMARY", "FromDate": "2020-01-01", "ToDate": "2026-10-03"}); check("dashboard window over DashboardMaxDays = 400", st == 400, j.get("message"))
    # enforcement off = old behaviour
    set_roles([]); cfg(RoleEnforcement="N")
    st, j, _ = wf.call("GET", "/up/load-policy?policyNo=" + pol + "&ChannelCode=SOHAR"); check("RoleEnforcement=N keeps the old open behaviour", st == 200, st)
finally:
    set_roles(ALL); cfg(RoleEnforcement="Y", AllowSelfApproval="Y")
os.makedirs("workflow", exist_ok=True); json.dump(R, open("workflow/role_results.json", "w"), indent=1)
print(sum(r["ok"] for r in R), "of", len(R), "passed")
