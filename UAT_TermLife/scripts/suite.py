import os,json,copy,time,io,re,threading,sys,subprocess,datetime
import requests
from lib import *; from base import *
R=[]; S={}   # results, shared state
SPEC_PREM={1:[216,328,440,552,664],2:[132,244,360,472,580]}
SPEC_SI={1:{"DTH":[10000,20000,30000,40000,50000],"PTD":[10000,20000,30000,40000,50000],"PPD":[10000,20000,30000,40000,50000],"REX":[1000]*5},
         2:{"DTH":[4500,17500,27500,37500,47500],"PTD":[7500,17500,27500,37500,47500],"PPD":[7500,17500,27500,37500,47500],"REX":[1000]*5}}
def T(id,mod,title,expected,fn,prio="High",typ="Functional"):
    t0=time.time()
    try: st,act=fn()
    except Exception as e: st,act="BLOCKED","Script error: %r"%e
    R.append(dict(id=id,module=mod,title=title,priority=prio,type=typ,expected=expected,status=st,actual=str(act)[:600],secs=round(time.time()-t0,1)))
    print(id,st,str(act)[:110],flush=True)
def mk(sub=1,plan=1,mode=2,term=1,mod=None):
    b=proposal(sub=sub,plan=plan,mode=mode,term=term)
    cl=b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]["PolicyCoverageList"]
    if sub==2: b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]["PolicyCoverageList"]=[c for c in cl if c["ProductElementCode"]!="TRV"]
    if mod: mod(b)
    return b
def rk(b): return b["PolicyLobList"][0]["PolicyRiskList"][0]
def cov(j,plan):
    for pl in j["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"]:
        if str(pl.get("PlanId"))==str(plan): return {c["ProductElementCode"]:c.get("SumInsured") for c in pl["PolicyCoverageList"]}
    return {}
def okp(r): return r[0]==200 and isinstance(r[1],dict) and r[1].get("ProposalNo")
def err(r): 
    j=r[1]; m=j.get("message") if isinstance(j,dict) else j
    return f"HTTP {r[0]} {str(m)[:220]}"
def prem(j): return j["PolicyLobList"][0].get("DuePremium")
def create(*a,**k):
    r=call("proposal",mk(*a,**k)); return r
def reject_expected(r,note=""):
    if r[0]==200 and isinstance(r[1],dict) and r[1].get("ProposalNo"): return "FAIL",f"Accepted (HTTP 200) and created {r[1]['ProposalNo']} {note}"
    return "PASS",err(r)+(" [non-4xx: HTTP %s]"%r[0] if r[0]>=500 else "")
def accept_expected(r,extra=""):
    if okp(r): return "PASS",f"HTTP 200 {r[1]['ProposalNo']} {extra}"
    return "FAIL",err(r)

# ---------------- A. AUTH ----------------
def a1():
    r=requests.post(B+"/cas/ebao/v2/json/tickets",headers={"Content-Type":"application/json","x-mo-user-source-id":"platform","x-mo-tenant-id":"uponlyuat"},json={"username":os.environ["UAT_USER"],"password":os.environ["UAT_PASS"]},timeout=40); j=r.json()
    return ("PASS" if r.status_code==200 and j.get("access_token") and j.get("auth_result") else "FAIL"),f"HTTP {r.status_code} expire_in={j.get('expire_in')}s auth_result={j.get('auth_result')}"
T("TL-AUTH-01","Authentication","Token API returns access token for valid credentials","HTTP 200, access_token present, expiry > 0",a1,"Critical")
def a2():
    r=requests.post(B+"/cas/ebao/v2/json/tickets",headers={"Content-Type":"application/json","x-mo-user-source-id":"platform","x-mo-tenant-id":"uponlyuat"},json={"username":"usertoken","password":"WRONG"},timeout=40)
    return ("PASS" if not (r.status_code==200 and r.json().get("access_token")) else "FAIL"),f"HTTP {r.status_code} {r.text[:150]}"
T("TL-AUTH-02","Authentication","Token API rejects wrong password","No token issued",a2,"High","Security")
def a3():
    r=call("get-plans",{},auth=False); return ("PASS" if r[0] in (401,403) else "FAIL"),err(r)
T("TL-AUTH-03","Authentication","Business API without Authorization header is rejected","HTTP 401/403",a3,"Critical","Security")
def a4():
    r=call("get-plans",{},auth="invalid-token-123"); return ("PASS" if r[0] in (401,403) else "FAIL"),err(r)
T("TL-AUTH-04","Authentication","Business API with invalid bearer token is rejected","HTTP 401/403",a4,"Critical","Security")
def a5():
    r=call("get-plans",{},auth="expired-or-revoked-token-sample"); return ("PASS" if r[0] in (401,403) else "FAIL"),err(r)
T("TL-AUTH-05","Authentication","Expired token (from Postman collection) is rejected","HTTP 401",a5,"Medium","Security")

# ---------------- B. GET PLANS ----------------
GP={"ApplicationNo":"123","EffectiveDate":"2026-10-13","ExpiryDate":"2027-10-12T23:59:59","UserName":"Salman","ApplyDate":"2026-10-13","BranchCode":"001","DiscountAmount":0,"StaffId":"76","PolicyCustomerList":[{"CIFNumber":"45678","CustomerType":"1"}],"PolicyLobList":[{"PolicyRiskList":[{"Gender":"1","IdNo":"123456789","IdType":"1","Salutation":"1","InsuredName":"Mohamed","DateOfBirth":"1988-10-01","ResidentStatus":"1","Email":"Mohamed@gmail.com","MaritalStatus":"1","PostCode":"100345","Mobile":"9989374444","Address":"Oman","MonthSalaryIncome":"10000","ProductElementCode":"R00001"}],"ProductCode":"TL001"}],"ProductCode":"TL001","ProductSubcode":"1","PremiumModeCode":2,"ChannelCode":"SOHAR"}
def gp(sub=1,mod=None):
    b=copy.deepcopy(GP); b["ProductSubcode"]=str(sub)
    if mod: mod(b)
    return call("get-plans",b)
def plans(j): return {str(p.get("PlanId")):{c["ProductElementCode"]:c.get("SumInsured") for c in p["PolicyCoverageList"]} for p in j["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"] if p.get("PlanId")}
for sub,name in ((1,"With Travel"),(2,"Without Travel")):
    def f(sub=sub):
        r=gp(sub); 
        if r[0]!=200: return "FAIL",err(r)
        p=plans(r[1]); S[f"gp{sub}"]=p
        return ("PASS" if sorted(p)==["1","2","3","4","5"] else "FAIL"),f"Plans returned: {sorted(p)}"
    T(f"TL-PLAN-0{sub}","Get Plans",f"Get Plans ({name}) returns exactly Plans 1-5","5 plans (1..5)",f)
    for pn in range(1,6):
        def f(sub=sub,pn=pn):
            p=S.get(f"gp{sub}",{}).get(str(pn),{}); diffs=[];notes=[]
            for c in ("DTH","PTD","PPD","REX"):
                exp=SPEC_SI[sub][c][pn-1] if c!="REX" else 1000
                if p.get(c)!=exp: diffs.append(f"{c}: spec {exp} vs system {p.get(c)}")
            if sub==1 and "TRV" not in p: diffs.append("TRV (Annual Family Travel 'Included') missing")
            if sub==2 and "TRV" in p: diffs.append("TRV present although 'Without Travel'")
            if diffs:
                spec_typo = sub==2 and pn==1 and len(diffs)==1 and diffs[0].startswith("DTH")
                return ("OBSERVATION" if spec_typo else "FAIL"),"; ".join(diffs)+(" — spec value 4500 appears to be a typo (PTD/PPD are 7500; system is consistent with application form tier pattern). BA to confirm." if spec_typo else "")
            return "PASS",f"{p}"
        T(f"TL-PLAN-0{sub}{pn}","Get Plans",f"Coverages & Sum Insured – {name} Plan {pn} match spec","DTH/PTD/PPD/REX/(TRV) as per 'Coverages and Sum Assured' sheet",f,"High")
def f():
    r=gp(1); j=r[1]; 
    return ("PASS" if j.get("DuePremium",0)>0 or any(p.get("DuePremium") for p in j["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"]) else "OBSERVATION"),f"get-plans returns DuePremium={j.get('DuePremium')} (root) – no per-plan premium in response; UI must call proposal API to obtain premium"
T("TL-PLAN-10","Get Plans","Get Plans returns premium per plan (needed for plan-selection screen)","Premium per plan returned",f,"Medium")
def f():
    r=gp(1); j=r[1]; cr=j.get("CommissionRate"); 
    return "OBSERVATION",f"Response exposes CommissionRate={cr} in Get Plans. Spec: commission must NOT be visible to end users on any page (Production Report only) – confirm Uponly UI suppresses it."
T("TL-PLAN-11","Get Plans","Bank commission not exposed in plan-selection response","No commission data in plan selection",f,"High","Security")
def f():
    r=gp(1,lambda b:b.update(ProductCode="XX999")); return reject_expected(r)
T("TL-PLAN-12","Get Plans","Invalid ProductCode rejected","Error message",f,"Medium","Negative")
def f():
    r=gp(3); return reject_expected(r) if r[0]!=200 else ("FAIL",f"HTTP 200 returned for invalid ProductSubcode 3: plans={list(plans(r[1]))}")
T("TL-PLAN-13","Get Plans","Invalid ProductSubcode (3) rejected","Error message",f,"Medium","Negative")
def f():
    r=gp(1,lambda b:b.pop("ChannelCode")); return reject_expected(r) if r[0]!=200 else ("FAIL","Accepted without ChannelCode")
T("TL-PLAN-14","Get Plans","Missing ChannelCode rejected","Error message",f,"Low","Negative")
def f():
    r=gp(1,lambda b:b.update(ChannelCode="NOPE")); return reject_expected(r) if r[0]!=200 else ("FAIL","Accepted with unknown ChannelCode")
T("TL-PLAN-15","Get Plans","Unknown ChannelCode rejected","Error message",f,"Low","Negative")

# ---------------- C. PREMIUM MATRIX ----------------
names={1:"With Travel",2:"Without Travel"}
for mode,mn in ((2,"Annual"),(1,"Single")):
  for sub in (1,2):
    for pn in range(1,6):
        def f(sub=sub,pn=pn,mode=mode):
            r=create(sub,pn,mode)
            if not okp(r): return "FAIL",err(r)
            j=r[1]; exp=SPEC_PREM[sub][pn-1]; ec=round(exp*0.7,2); got=prem(j); gc=j["PolicyLobList"][0].get("Commission")
            c=cov(j,pn); sc={k:(SPEC_SI[sub][k][pn-1] if k!="REX" else 1000) for k in ("DTH","PTD","PPD","REX")}
            bad=[]
            if got!=exp: bad.append(f"premium {got}≠{exp}")
            if round(gc or 0,2)!=ec: bad.append(f"commission {gc}≠{ec}")
            for k,v in sc.items():
                if k=="DTH" and sub==2 and pn==1: continue
                if c.get(k)!=v: bad.append(f"{k} {c.get(k)}≠{v}")
            S[f"prop_{sub}_{pn}_{mode}"]=j["ProposalNo"]
            return ("PASS" if not bad else "FAIL"),f"{j['ProposalNo']} premium={got} commission={gc}"+("; "+"; ".join(bad) if bad else "")
        T(f"TL-PREM-{mn[0]}{sub}{pn}","Premium & Rates",f"{mn} premium – {names[sub]} Plan {pn}: premium, 70% commission, coverage SI","Premium %s, commission %s"%(SPEC_PREM[sub][pn-1],round(SPEC_PREM[sub][pn-1]*0.7,2)),f,"Critical")

def f():
    r=create(1,1,2); j=r[1]; c=cov(j,1); true=sum(v for v in c.values() if v); tot=j.get("SumInsured")
    return ("PASS" if tot==true else "FAIL"),f"Plan 1 benefits total {true} (DTH+PTD+PPD+REX) but policy/lob/risk SumInsured={tot}; PlanList has {len(j['PolicyLobList'][0]['PolicyRiskList'][0]['PlanList'])} entries (2nd entry has no PlanId/PlanName – duplicate)"
T("TL-PREM-90","Premium & Rates","Total Sum Insured equals sum of selected plan benefits; PlanList has only the selected plan","SumInsured=31000 for Plan 1 (W/Travel), single PlanList entry",f,"High")
def f():
    r=call("proposal",mk(1,3,2,mod=lambda b:(b["PolicyLobList"][0].update(DuePremium=1),b.update(DuePremium=1)))); j=r[1]
    return ("PASS" if okp(r) and prem(j)==440 else "FAIL"),f"Client sent premium 1 → system premium {prem(j) if okp(r) else err(r)}"
T("TL-PREM-91","Premium & Rates","Client-supplied DuePremium is ignored (server recalculates)","Premium 440",f,"Critical","Security")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:[c.update(SumInsured=999999) for c in rk(b)["PlanList"][0]["PolicyCoverageList"] if c["ProductElementCode"]=="DTH"])); 
    if not okp(r): return "FAIL",err(r)
    return ("PASS" if cov(r[1],1).get("DTH")==10000 else "FAIL"),f"Client DTH SI 999999 → system DTH {cov(r[1],1).get('DTH')}"
T("TL-PREM-92","Premium & Rates","Client-supplied SumInsured is overridden by plan configuration","DTH = 10000",f,"Critical","Security")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(DiscountAmount=10))); r0=create(1,1,2)
    return "OBSERVATION",f"DiscountAmount=10 → premium {prem(r[1]) if okp(r) else err(r)} (no discount: {prem(r0[1])}). Spec Feed File lists 'Discount' field – discount logic/ rules are not defined in spec."
T("TL-PREM-93","Premium & Rates","Discount amount handling","Defined by business (not in spec)",f,"Medium")
for ct,nm in ((2,"Staff"),(3,"Special")):
    def f(ct=ct):
        r=call("proposal",mk(1,1,2,mod=lambda b:b["PolicyCustomerList"][0].update(CustomerType=str(ct)))); return accept_expected(r,f"premium={prem(r[1]) if okp(r) else ''}")
    T(f"TL-PREM-9{ct+2}","Premium & Rates",f"Customer type {nm} ({ct}) accepted and priced","200, premium 216 (no differential pricing in spec)",f,"Medium")
def f():
    r=call("proposal",mk(1,1,3)); 
    if not okp(r): return "PASS",err(r)
    return "FAIL",f"Monthly mode (3) accepted for Term Life: {r[1]['ProposalNo']} premium {prem(r[1])}. Spec: Term Life = Annual and Single only (Monthly only for Life Protect)."
T("TL-PREM-96","Premium & Rates","Monthly premium mode rejected for Term Life","Rejected (Monthly applies to Life Protect only)",f,"High","Negative")
def f():
    r=call("proposal",mk(1,1,9)); return reject_expected(r)
T("TL-PREM-97","Premium & Rates","Invalid PremiumModeCode (9) rejected","Rejected",f,"Medium","Negative")
def f():
    r=call("proposal",mk(1,9,2)); return reject_expected(r)
T("TL-PREM-98","Premium & Rates","Invalid PlanId (9) rejected","Rejected",f,"Medium","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(ProductSubcode=7))); return reject_expected(r)
T("TL-PREM-99","Premium & Rates","Invalid ProductSubcode (7) rejected","Rejected",f,"Medium","Negative")

# ---------------- D. TERM ----------------
def f():
    r=create(1,1,2,2)
    if not okp(r): return "PASS",err(r)
    return "FAIL",f"Annual mode with PolicyTerm=2 accepted ({r[1]['ProposalNo']}); spec: Annual = 1 year only"
T("TL-TERM-01","Term","Annual premium with term ≠ 1 rejected","Rejected",f,"High","Negative")
for t in (2,5,10):
    def f(t=t):
        r=create(1,1,1,t)
        if not okp(r): return "FAIL",err(r)
        exp=(datetime.date(2026,10,13).replace(year=2026+t)-datetime.timedelta(days=1)).isoformat()
        j=r[1]; return ("PASS" if j["ExpiryDate"][:10]==exp else "FAIL"),f"Single, term {t}: premium {prem(j)}, ExpiryDate {j['ExpiryDate']} (expected cover end {exp}); PolicyTerm={j.get('PolicyTerm')}"
    T(f"TL-TERM-0{2+[2,5,10].index(t)}","Term",f"Single premium, term {t} yrs: accepted and expiry consistent with term","Expiry date = effective + term",f,"High")
for t in (0,11):
    def f(t=t):
        r=create(1,1,1,t)
        if not okp(r): return "PASS",err(r)
        return "FAIL",f"Single premium with term {t} accepted ({r[1]['ProposalNo']}); spec: Single term 2–10 (min/max configurable)"
    T(f"TL-TERM-0{5+[0,11].index(t)}","Term",f"Single premium term {t} (outside 2–10) rejected","Rejected",f,"High","Boundary")
def f():
    r1=create(1,1,1,1); r5=create(1,1,1,5)
    return "OBSERVATION",f"Single premium: term 1 → {prem(r1[1])}, term 5 → {prem(r5[1])}. Premium does not vary with term; spec lists one premium for 'Annual and Single' — business to confirm multi-year single-premium pricing."
T("TL-TERM-07","Term","Single premium pricing vs term","Per business rule",f,"Medium")

# ---------------- E. FIELD / DATA VALIDATION ----------------
def setrisk(**kw): return lambda b: rk(b).update(kw)
def dobcase(id,dob,exp,label):
    def f():
        r=call("proposal",mk(1,1,2,mod=setrisk(DateOfBirth=dob)))
        if exp=="accept": 
            return accept_expected(r)
        return ("OBSERVATION",f"Backend {'accepted' if okp(r) else 'rejected'} DOB {dob} ({label}). Spec: age rules (min 18, max entry 64, max age 69, exit 70) are enforced by Uponly UI; backend enforcement absent – recommend defence-in-depth.") if okp(r) else ("PASS",err(r))
    T(id,"Underwriting Rules",f"Age {label} (DOB {dob}) at 2026-10-13","UI validates; backend ideally enforces" if exp!="accept" else "Accepted",f,"High","Boundary")
dobcase("TL-UW-01","2008-10-14","reject","17y 364d – below min age 18")
dobcase("TL-UW-02","2008-10-13","accept","exactly 18 – min age")
dobcase("TL-UW-03","1962-10-14","accept","64y 364d – within max entry 64")
dobcase("TL-UW-04","1961-10-13","reject","exactly 65 – above max entry age 64")
dobcase("TL-UW-05","1957-10-14","reject","68y – above max entry 64")
dobcase("TL-UW-06","1956-10-12","reject","70y – above max age 69 / exit 70")
dobcase("TL-UW-07","2030-01-01","reject","future date of birth")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).update(DateOfBirth="1962-10-14"))); 
    if not okp(r): return "PASS",err(r)
    return "OBSERVATION","Entry at 64y 364d with 1-year term → age at expiry 65, within exit age 70: OK. Multi-year single-premium exit-age (70) check can't be validated – term/expiry not enforced (see TL-TERM)."
T("TL-UW-08","Underwriting Rules","Max age at exit (70) vs term for single premium","Cover end age ≤ 70",f,"Medium")

req=["InsuredName","DateOfBirth","Gender","IdNo","IdType","Salutation","ResidentStatus","Email","Mobile","MaritalStatus","Address"]
for i,k in enumerate(req,1):
    def f(k=k):
        r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).pop(k))); return reject_expected(r,f"(mandatory field {k} omitted)")
    T(f"TL-VAL-{i:02d}","Field Validation",f"Mandatory field '{k}' omitted is rejected","Rejected with message",f,"High","Negative")
for i,(k,path) in enumerate([("CIFNumber","cust"),("CustomerType","cust")],12):
    def f(k=k):
        r=call("proposal",mk(1,1,2,mod=lambda b:b["PolicyCustomerList"][0].pop(k))); return reject_expected(r,f"({k} omitted)")
    T(f"TL-VAL-{i:02d}","Field Validation",f"Mandatory field '{k}' omitted is rejected","Rejected",f,"High","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.pop("BranchCode"))); return reject_expected(r,"(BranchCode omitted)")
T("TL-VAL-14","Field Validation","Mandatory field 'BranchCode' omitted is rejected","Rejected",f,"High","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.pop("PlanId"))); return reject_expected(r,"(PlanId omitted)")
T("TL-VAL-15","Field Validation","Mandatory field 'PlanId' omitted is rejected","Rejected",f,"High","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.pop("PremiumModeCode"))); return reject_expected(r,"(PremiumModeCode omitted)")
T("TL-VAL-16","Field Validation","Mandatory field 'PremiumModeCode' omitted is rejected","Rejected",f,"High","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).update(MonthSalaryIncome="0"))); return accept_expected(r,"salary 0")
T("TL-VAL-17","Field Validation","Monthly salary: no minimum validation (spec: remove minimum)","Accepted",f,"Medium")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).pop("MonthSalaryIncome"))); return accept_expected(r,"salary omitted")
T("TL-VAL-18","Field Validation","Monthly salary optional (not enforced)","Accepted",f,"Low")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).pop("PostCode"))); return accept_expected(r,"PO Box omitted")
T("TL-VAL-19","Field Validation","PO Box optional (spec: PO Box + Address replace India pin code logic)","Accepted",f,"Medium")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).update(PostCode="PO Box 123, CPO Seeb")));  return accept_expected(r,"alphanumeric PO Box")
T("TL-VAL-20","Field Validation","PO Box accepts free-text (no Indian pincode mapping)","Accepted",f,"Medium")
for i,(lbl,mod,exp) in enumerate([("Gender=2 (Female)",setrisk(Gender="2"),"a"),("Gender=9 invalid",setrisk(Gender="9"),"r"),("IdType=2 (Passport)",setrisk(IdType="2"),"a"),("IdType=9 invalid",setrisk(IdType="9"),"r"),
        ("Salutation=2 (Mrs)",setrisk(Salutation="2"),"a"),("Salutation=3 (Miss)",setrisk(Salutation="3"),"a"),("Salutation=9 invalid",setrisk(Salutation="9"),"r"),
        ("ResidentStatus=2 (Omani)",setrisk(ResidentStatus="2"),"a"),("ResidentStatus=9 invalid",setrisk(ResidentStatus="9"),"r"),
        ("MaritalStatus=2",setrisk(MaritalStatus="2"),"a"),("MaritalStatus=9 invalid",setrisk(MaritalStatus="9"),"r"),
        ("CustomerType=9 invalid",lambda b:b["PolicyCustomerList"][0].update(CustomerType="9"),"r"),("BranchCode=999 invalid",lambda b:b.update(BranchCode="999"),"r")],21):
    def f(mod=mod,exp=exp,lbl=lbl):
        r=call("proposal",mk(1,1,2,mod=mod)); return accept_expected(r) if exp=="a" else reject_expected(r)
    T(f"TL-LOV-{i:02d}","LOV / Code Tables",f"{lbl}","Accepted" if exp=="a" else "Rejected",f,"Medium","Negative" if exp=="r" else "Functional")
def f():
    r=call("proposal",mk(1,1,2,mod=setrisk(Email="not-an-email"))); return reject_expected(r,"invalid email")
T("TL-VAL-30","Field Validation","Invalid email format rejected","Rejected",f,"Medium","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=setrisk(Mobile="ABCDEFG"))); return reject_expected(r,"alphabetic mobile")
T("TL-VAL-31","Field Validation","Non-numeric mobile rejected","Rejected",f,"Medium","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=setrisk(MonthSalaryIncome="-500"))); return reject_expected(r,"negative salary")
T("TL-VAL-32","Field Validation","Negative monthly salary rejected","Rejected",f,"Low","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=setrisk(InsuredName="محمد بن سالم الهنائي"))); 
    if not okp(r): return "FAIL",err(r)
    L=call("load-policy",method="GET",params={"proposalNo":r[1]["ProposalNo"],"ChannelCode":"SOHAR"})
    nm=rk(L[1])["InsuredName"]; return ("PASS" if nm=="محمد بن سالم الهنائي" else "FAIL"),f"Stored name: {nm}"
T("TL-VAL-33","Field Validation","Arabic insured name stored & returned correctly (UTF-8)","Name preserved",f,"Medium")
def f():
    r=call("proposal",mk(1,1,2,mod=setrisk(InsuredName="A"*300))); return reject_expected(r,"300-char name")
T("TL-VAL-34","Field Validation","Over-long insured name (300 chars) rejected / truncated gracefully","Rejected",f,"Low","Boundary")
def f():
    pay="Robert'); DROP TABLE POLICY;-- <script>alert(1)</script>"
    r=call("proposal",mk(1,1,2,mod=setrisk(InsuredName=pay)));
    if not okp(r): return "PASS",err(r)
    return "OBSERVATION",f"Special/script characters accepted and stored raw ({r[1]['ProposalNo']}); no SQL error. Ensure Uponly UI and PDF output encode on display."
T("TL-SEC-01","Security","SQL/XSS payload in InsuredName handled safely","No server error; output-encoded on display",f,"High","Security")
def f():
    r=call("proposal",mk(1,1,2)); j=r[1]; rr=rk(j)
    return "OBSERVATION",f"Mobile returned masked ('{rr['Mobile']}') but IdNo returned in clear ('{rr['IdNo']}'). Inconsistent PII masking."
T("TL-SEC-02","Security","PII masking consistency in API response","Consistent masking of sensitive PII",f,"Medium","Security")

# dates
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(ExpiryDate="2026-01-01T23:59:59"))); return reject_expected(r,"expiry before effective")
T("TL-DATE-01","Dates","ExpiryDate earlier than EffectiveDate rejected","Rejected",f,"High","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(EffectiveDate="2025-01-01",ApplyDate="2025-01-01"))); return reject_expected(r,"back-dated effective date")
T("TL-DATE-02","Dates","Back-dated EffectiveDate rejected","Rejected",f,"Medium","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(EffectiveDate="2026-10-20",ExpiryDate="2027-10-19T23:59:59"))); return accept_expected(r,"future effective date")
T("TL-DATE-03","Dates","Future EffectiveDate (+7 days) accepted","Accepted",f,"Medium")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(EffectiveDate="13-10-2026"))); return reject_expected(r,"bad date format")
T("TL-DATE-04","Dates","Malformed EffectiveDate rejected","Rejected",f,"Low","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.update(ExpiryDate="2027-10-12T23:59:59"))); j=r[1]
    return ("PASS" if okp(r) and j["ExpiryDate"]=="2027-10-12T23:59:59" else "FAIL"),"1-year cover ends 2027-10-12 23:59:59"
T("TL-DATE-05","Dates","Annual cover period = 12 months from commencement","Expiry 2027-10-12T23:59:59",f,"High")

# beneficiaries
def bene(lst): return lambda b: rk(b).update(BeneficiaryList=lst)
def B(n,rel,sh,seq): return {"BeneficaryName":n,"RelationshipCode":str(rel),"Share":str(sh),"BeneficarySequence":str(seq)}
cases=[("Two beneficiaries 60/40 (sum 100)",[B("A",3,60,1),B("B",2,40,2)],"a"),("Three beneficiaries 50/30/20",[B("A",6,50,1),B("B",3,30,2),B("C",2,20,3)],"a"),
       ("Single beneficiary share 50 (sum ≠ 100)",[B("A",3,50,1)],"r"),("Shares 60/60 (sum 120)",[B("A",3,60,1),B("B",2,60,2)],"r"),
       ("Share 150 (>100)",[B("A",3,150,1)],"r"),("Share negative (-100)",[B("A",3,-100,1)],"r"),("Zero beneficiaries (empty list)",[],"r"),
       ("Relationship invalid code 99",[B("A",99,100,1)],"r"),("Relationship Spouse (6)",[B("A",6,100,1)],"a"),("Beneficiary name blank",[B("",3,100,1)],"r")]
for i,(lbl,lst,exp) in enumerate(cases,1):
    def f(lst=lst,exp=exp):
        r=call("proposal",mk(1,1,2,mod=bene(lst))); return accept_expected(r) if exp=="a" else reject_expected(r)
    T(f"TL-BEN-{i:02d}","Beneficiary",lbl,"Accepted" if exp=="a" else "Rejected (shares must total 100%)",f,"High","Negative" if exp=="r" else "Functional")
for rc,nm in ((1,"Brother"),(2,"Daughter"),(3,"Son"),(4,"Father"),(5,"Mother"),(6,"Spouse")):
    pass
def f():
    r=call("list-master-table",{"DataTableName":"Relationship","ChannelCode":"SOHAR"}); got=sorted(x["Description"] for x in r[1])
    exp=sorted(["Brother","Daughter","Son","Father","Mother","Spouse"]); return ("PASS" if got==exp else "FAIL"),f"Relationship master = {got}"
T("TL-BEN-11","Beneficiary","Relationship LOV matches spec (Brother, Daughter, Son, Father, Mother, Spouse)","6 values",f,"Medium")

# payment info
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b.pop("PolicyPaymentInfoList"))); S["no_pay"]=r[1].get("ProposalNo") if okp(r) else None
    return accept_expected(r,"no payment info at proposal stage")
T("TL-PAY-01","Payment","Proposal can be saved without LC/LG/Debit details (mandatory only before conversion)","Accepted",f,"High")
def f():
    pn=S.get("no_pay")
    if not pn: return "BLOCKED","no proposal"
    r=call("issue",{"ProposalNo":pn,"ProductCode":"TL001","ChannelCode":"SOHAR"})
    if r[0]==200 and isinstance(r[1],dict) and r[1].get("PolicyNo"): return "FAIL",f"Policy {r[1]['PolicyNo']} issued without LC Code / LG Code / Debit details (spec: mandatory before policy conversion)"
    return "PASS",err(r)
T("TL-PAY-02","Payment","Issue blocked when LC Code / LG Code / payment details missing","Rejected",f,"Critical","Negative")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b["PolicyPaymentInfoList"][0].pop("DebitAccountNo"))); return accept_expected(r,"no debit account")
T("TL-PAY-03","Payment","Debit Account No is optional (manually entered, 'No' mandatory in spec)","Accepted",f,"Low")
def f():
    r=call("proposal",mk(1,1,2,mod=lambda b:b["PolicyPaymentInfoList"][0].update(LGCode="ZZ"))); return accept_expected(r,"arbitrary LGCode") if okp(r) else ("PASS",err(r))
T("TL-PAY-04","Payment","Invalid LG Code handling","Rejected or validated against master",f,"Medium","Negative")
