#!/usr/bin/env python3
"""Runs every API live on the MC tenant with fixed literal values and records request + response of each case (samples.json)."""
import json, sys, os, re, time, copy, urllib.request, urllib.error, subprocess
from datetime import date, timedelta
B = "/tmp/claude-0/-home-user-Tablet/4e5f48e0-1baf-5a1d-9f0f-ce844ee516ee/scratchpad/uponly-build"
BASE = "https://portal-gw.insuremo.com/platform/api-orchestration-test/v1/flow"
TOK = json.loads(subprocess.run(["imo", "auth", "prepare", "--profile", "portal:uponly", "--json"], capture_output=True, text=True, cwd="/home/user/Tablet").stdout)["access_token"]
TODAY = date.today(); APPLY = TODAY.isoformat(); EFF = (TODAY + timedelta(days=1)); EFFS = EFF.isoformat()
def add_years(d, n): return d.replace(year=d.year + n) if not (d.month == 2 and d.day == 29) else d.replace(year=d.year + n, day=28)
def expiry(term): return (add_years(EFF, term) - timedelta(days=1)).isoformat() + "T23:59:59"
CANCEL_PRORATA = (EFF + timedelta(days=30)).isoformat(); CANCEL_FREELOOK = (EFF + timedelta(days=5)).isoformat()
SAL = {"Mr.": "1", "Mrs": "2", "Miss": "3"}
P = {"M1": ("Mr.", "1", "Mohamed Al Harthy", "1988-10-01", "1", "P1001001"), "M2": ("Mr.", "1", "Khalid Al Rawahi", "1985-03-22", "2", "P2002002"),
     "M3": ("Mr.", "1", "Salim Al Busaidi", "1979-07-15", "1", "P3003003"), "F1": ("Mrs", "2", "Fatma Al Lawati", "1991-01-30", "1", "P4004004"),
     "F2": ("Miss", "2", "Aisha Al Balushi", "1990-05-12", "1", "P5005005"), "M4": ("Mr.", "1", "Hamad Al Kindi", "1982-11-09", "1", "P6006006"),
     "M5": ("Mr.", "1", "Yousuf Al Siyabi", "1976-04-18", "1", "P7007007"), "F3": ("Mrs", "2", "Maryam Al Hinai", "1984-09-27", "1", "P8008008"),
     "M6": ("Mr.", "1", "Ahmed Al Amri", "1973-12-02", "1", "P9009009"), "F4": ("Miss", "2", "Noor Al Saadi", "1995-06-21", "2", "P1010101"),
     "F5": ("Mrs", "2", "Rashid Al Maamari", "1980-02-14", "1", "P1111111")}
VARIANTS = [("UPPA001", "1", "M1", "Personal Accident with TTD"), ("UPPA001", "2", "M2", "Personal Accident without TTD"), ("TL001", "1", "M3", "Term Life with Travel"),
            ("TL001", "2", "F1", "Term Life without Travel"), ("FP001", "1", "F2", "Female Protection"), ("HC001", "1", "M4", "Hospital Cash Benefit"),
            ("CI001", "1", "M5", "Critical Illness - 7 CI"), ("CI001", "2", "F3", "Critical Illness - 11 CI"), ("CI001", "3", "M6", "Critical Illness - 32 CI"),
            ("LP001", "1", "F4", "Life Protect"), ("DH001", "1", "F5", "Domestic Helper Insurance")]
CASES = []
def http(method, path, body=None, token=TOK, raw_body=None):
    url = BASE + path; data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json"}
    if token: h["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try: resp = urllib.request.urlopen(r, timeout=300); return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e: return e.code, e.headers.get("Content-Type", ""), e.read()
def record(folder, name, route, method, path, body, status, ctype, data, note="", raw_body=None):
    if "pdf" in ctype or data[:4] == b"%PDF": resp = {"_note": f"PDF document ({len(data)} bytes), returned as binary with Content-Type {ctype}", "_binary": True}
    else:
        try: resp = json.loads(data)
        except Exception: resp = {"_raw": data[:300].decode("utf8", "replace")}
    CASES.append(dict(folder=folder, name=name, route=route, method=method, path=path, body=body if raw_body is None else None, raw_body=(raw_body.decode() if raw_body is not None else None), status=status, ctype=ctype, response=resp, note=note))
    print(f"{folder} | {name}: {status}", flush=True); return status, resp
def call(folder, name, route, method, path, body=None, note="", token=TOK, raw_body=None, keep=True):
    st, ct, data = http(method, path, body, token, raw_body)
    if keep: return record(folder, name, route, method, path, body, st, ct, data, note, raw_body)
    try: return st, json.loads(data)
    except Exception: return st, {}
def lit(s, m):
    for k, v in m.items(): s = s.replace("{{" + k + "}}", str(v))
    return s
def person(body, who, appno, term):
    sal, gen, name, dob, res, idno = P[who]
    def walk(o):
        if isinstance(o, dict):
            for k in list(o):
                v = o[k]
                if k == "InsuredName": o[k] = name
                elif k == "DateOfBirth": o[k] = dob
                elif k == "Gender": o[k] = gen
                elif k == "Salutation": o[k] = SAL[sal]
                elif k == "IdNo": o[k] = idno
                elif k == "ResidentStatus": o[k] = res
                elif k == "Email": o[k] = name.split()[0].lower() + "@example.com"
                elif k == "Mobile": o[k] = "9681234" + idno[-4:]
                elif k == "Address": o[k] = "Muscat, Oman"
                elif k == "PostCode": o[k] = "100"
                elif k == "MonthSalaryIncome": o[k] = "1200"
                elif k == "UserName": o[k] = "maker01"
                elif k == "CIFNumber": o[k] = "10" + idno[-4:]
                elif k == "StaffId": o[k] = "76"
                elif k == "BeneficaryName": o[k] = "Sayyed Al Harthy"
                elif k == "DebitAccountNo": o[k] = "89623" + idno[-4:]
                elif k == "DebitRefNo": o[k] = "REF" + idno[-5:]
                elif k == "DiscountAmount": o[k] = 0
                elif k == "ApplicationNo": o[k] = appno
                elif k == "ExpiryDate": o[k] = expiry(int(term))
                elif k == "EffectiveDate": o[k] = EFFS
                elif k == "ApplyDate": o[k] = APPLY
                elif k == "TransactionDate": o[k] = APPLY
                else: walk(v)
        elif isinstance(o, list):
            for x in o: walk(x)
    walk(body); return body
def template(code, sub, step):
    d = f"{B}/samples/ref/{code}_{sub}_P1"; return json.load(open(f"{d}/{step}.json"))["request"]
def flow(idx, code, sub, who, label):
    folder = f"{code}-{sub} {label}"; n = f"{idx:02d}"; app = f"APP{TODAY.strftime('%y%m%d')}{idx:02d}01"; appr = f"APP{TODAY.strftime('%y%m%d')}{idx:02d}02"
    appc = f"APP{TODAY.strftime('%y%m%d')}{idx:02d}03"
    m = {"channelCode": "SOHAR", "orgCode": "1", "applyDate": APPLY, "effectiveDate": EFFS}
    def mk(step, app_no, **extra):
        rq = template(code, sub, step); b = json.loads(lit(json.dumps(rq.get("body")), {**m, **extra})) if rq.get("body") is not None else None
        term = (template(code, sub, "02_proposal")["body"] or {}).get("PolicyTerm", "1")
        if b is not None and "PolicyLobList" in b or (b is not None and "ApplicationNo" in b): b = person(b, who, app_no, term)
        return rq, b
    term = template(code, sub, "02_proposal")["body"]["PolicyTerm"]
    rq, b = mk("01_get-plans", app); call(folder, "1. Get Plans", "get-plans", "POST", "/up/get-plans", b)
    rq, b = mk("02_proposal", app); st, r = call(folder, "2. Create Proposal (application)", "proposal", "POST", "/up/proposal", b)
    pno = r.get("ProposalNo")
    if not pno: print("!! no proposal", code, sub, r); return
    rq, b = mk("03_update-proposal", app, proposalNo=pno); b["ProposalNo"] = pno; call(folder, "3. Update Proposal (enrolment)", "update-proposal", "POST", "/up/update-proposal", b)
    call(folder, "4. Load Proposal", "load-policy", "GET", f"/up/load-policy?proposalNo={pno}&ChannelCode=SOHAR")
    call(folder, "5. Share Proposal by Email", "share", "POST", "/up/share", {"ChannelCode": "SOHAR", "DocType": "PROPOSAL", "Channel": "EMAIL", "ProposalNo": pno, "ProductCode": code, "ProductSubcode": sub, "Email": "customer@example.com"})
    st, r = call(folder, "6. Issue Policy", "issue", "POST", "/up/issue", {"ProposalNo": pno, "ProductCode": code, "ChannelCode": "SOHAR"})
    pol = r.get("PolicyNo")
    if not pol: print("!! no policy", code, sub, r); return
    call(folder, "7. Load Policy", "load-policy", "GET", f"/up/load-policy?policyNo={pol}&ChannelCode=SOHAR")
    call(folder, "8. Policy Certificate PDF", "doc_generation", "POST", "/up/doc_generation", {"DocType": "Policy", "PolicyNo": pol, "ProductSubcode": sub, "ChannelCode": "SOHAR"})
    call(folder, "9. Application Form PDF (doc_generation)", "doc_generation", "POST", "/up/doc_generation", {"DocType": "Application", "ProposalNo": pno, "ProductSubcode": sub, "ChannelCode": "SOHAR"})
    call(folder, "10. Application Form PDF (application_doc_generation)", "application_doc_generation", "POST", "/up/application_doc_generation", {"proposalNo": pno, "ProductSubcode": sub, "ChannelCode": "SOHAR"})
    call(folder, "11. Share Policy by Email and SMS", "share", "POST", "/up/share", {"ChannelCode": "SOHAR", "DocType": "POLICY", "Channel": "BOTH", "PolicyNo": pol, "Email": "customer@example.com", "Mobile": "96899999999"})
    rq, b = mk("07_proposal-for-reject", appr); st, r = call(folder, "12. Create Proposal (to be rejected)", "proposal", "POST", "/up/proposal", b)
    rno = r.get("ProposalNo")
    if rno: call(folder, "13. Reject Proposal", "proposal-reject", "POST", "/up/proposal-reject", {"ProposalNo": rno, "ProposalRejectDesc": "Customer did not provide the required documents", "ProductCode": code, "ChannelCode": "SOHAR"})
    st, r = call(folder, "14. Cancel Check (raise cancellation, pro-rata)", "cancel-check", "POST", "/up/cancel-check", {"PolicyNo": pol, "CancellationDate": CANCEL_PRORATA, "CancelReason": "Customer request", "ChannelCode": "SOHAR"})
    req = r.get("RequestNo")
    call(folder, "15. Cancel Detail (pending request)", "cancel-detail", "POST", "/up/cancel-detail", {"ChannelCode": "SOHAR", "PolicyNo": pol})
    if req: call(folder, "16. Cancel Approve (Decision APPROVE)", "cancel-approve", "POST", "/up/cancel-approve", {"PolicyNo": pol, "RequestNo": req, "Decision": "APPROVE", "ChannelCode": "SOHAR"})
    call(folder, "17. Load Policy (after cancellation)", "load-policy", "GET", f"/up/load-policy?policyNo={pol}&ChannelCode=SOHAR")
    # second policy: cancellation inside the free-look period, rejected by the checker
    rq, b = mk("02_proposal", appc); st, r = call(folder, "x", "proposal", "POST", "/up/proposal", b, keep=False); p2 = r.get("ProposalNo")
    if p2:
        rq, b = mk("03_update-proposal", appc, proposalNo=p2); b["ProposalNo"] = p2; call(folder, "x", "update-proposal", "POST", "/up/update-proposal", b, keep=False)
        st, r = call(folder, "x", "issue", "POST", "/up/issue", {"ProposalNo": p2, "ProductCode": code, "ChannelCode": "SOHAR"}, keep=False); pol2 = r.get("PolicyNo")
        if pol2:
            st, r = call(folder, "18. Cancel Check (free-look period, 100% refund)", "cancel-check", "POST", "/up/cancel-check", {"PolicyNo": pol2, "CancellationDate": CANCEL_FREELOOK, "CancelReason": "Customer changed their mind", "ChannelCode": "SOHAR"})
            if r.get("RequestNo"): call(folder, "19. Cancel Approve (Decision REJECT - policy stays in force)", "cancel-approve", "POST", "/up/cancel-approve", {"PolicyNo": pol2, "RequestNo": r["RequestNo"], "Decision": "REJECT", "ChannelCode": "SOHAR"})
    return dict(pol=pol, pno=pno, cancelled=pol)
def main():
    which = sys.argv[1:] 
    ctx = {}
    for i, (code, sub, who, label) in enumerate(VARIANTS, 1):
        if which and f"{code}-{sub}" not in which: continue
        try: ctx[f"{code}-{sub}"] = flow(i, code, sub, who, label)
        except Exception as e: print("ERR", code, sub, repr(e), flush=True)
        json.dump(CASES, open("samples_part.json", "w"), ensure_ascii=False)
    json.dump(dict(cases=CASES, ctx=ctx, today=APPLY), open("samples_variants.json", "w"), ensure_ascii=False, indent=1)
if __name__ == "__main__": main()
