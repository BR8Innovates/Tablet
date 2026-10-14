import json,copy,re,subprocess,time,requests,warnings,openpyxl
warnings.simplefilter("ignore")
from lib import *
items=json.load(open("items.json"))
R=[];S={}
PREM={1:[68,96,124,152,180],2:[55,81,109,137,165]}
COMM={1:[44.1,63.7,83.3,102.9,122.5],2:[35,53.2,72.8,92.4,112]}
def spec_cov(sub,p):
    base=12000+10000*(p-1) if sub==1 else 10000+10000*(p-1)
    d={"ACD":base,"PTD":base,"PPD":base,"HCB":20,"REX":1500}
    if sub==1: d["TTD"]=3000
    return d
def T(id,mod,title,exp,fn,prio="High"):
    try: st,act=fn()
    except Exception as e: st,act="BLOCKED","script error %r"%e
    R.append(dict(id=id,module=mod,title=title,priority=prio,expected=exp,status=st,actual=str(act)[:500])); print(id,st,str(act)[:120],flush=True)
tmpl=json.loads(items["Proposal API Copy"]["request"]["body"]["raw"])
def mk(sub=1,plan=1,mode=2,term=1,ch=True):
    b=copy.deepcopy(tmpl); b["ApplicationNo"]="PA-UAT-01"; b["EffectiveDate"]="2026-10-14"; b["ExpiryDate"]="2027-10-13T23:59:59"; b["ApplyDate"]="2026-10-14"
    b["PolicyLobList"][0]["PolicyRiskList"][0]["DateOfBirth"]="1988-10-01"; b["PolicyLobList"][0]["PolicyRiskList"][0]["Mobile"]="9989374444"
    b["PolicyPaymentInfoList"][0].update(DebitAccountNo="896236508",DebitRefNo="wer455",TransactionDate="2026-10-14")
    sc=spec_cov(sub,plan); b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]=dict(PolicyCoverageList=[{"ProductElementCode":k,"SumInsured":v} for k,v in sc.items()],PlanId=plan)
    b["PlanId"]=plan; b["ProductSubcode"]=str(sub); b["PremiumModeCode"]=str(mode); b["PolicyTerm"]=str(term)
    if ch: b["ChannelCode"]="SOHAR"
    return b
def covs(j,plan):
    for pl in j["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"]:
        if str(pl.get("PlanId"))==str(plan): return {c["ProductElementCode"]:c.get("SumInsured") for c in pl["PolicyCoverageList"]}
    return {}
def okp(r): return r[0]==200 and isinstance(r[1],dict) and r[1].get("ProposalNo")
def err(r): return f"HTTP {r[0]} {str((r[1].get('message') if isinstance(r[1],dict) else r[1]))[:200]}"
GP=json.loads(items["Get Plan API"]["request"]["body"]["raw"]); GP.update(ChannelCode="SOHAR",DiscountAmount=0,EffectiveDate="2026-10-14",ExpiryDate="2027-10-13T23:59:59",ApplyDate="2026-10-14")
for sub,nm in ((1,"With TTD"),(2,"Without TTD")):
    b=copy.deepcopy(GP); b["ProductSubcode"]=str(sub); r=call("get-plans",b); S[f"gp{sub}"]={str(p["PlanId"]):{c["ProductElementCode"]:c["SumInsured"] for c in p["PolicyCoverageList"]} for p in r[1]["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"] if p.get("PlanId")}
    def f(sub=sub): return ("PASS" if sorted(S[f"gp{sub}"])==list("12345") else "FAIL"),f"plans {sorted(S[f'gp{sub}'])}"
    T(f"PA-PLAN-0{sub}","Get Plans",f"Get Plans ({nm}) returns Plans 1-5","5 plans",f)
    for p in range(1,6):
        def f(sub=sub,p=p):
            got=S[f"gp{sub}"].get(str(p),{}); exp=spec_cov(sub,p); d=[f"{k}: spec {v} vs {got.get(k)}" for k,v in exp.items() if got.get(k)!=v]+[f"unexpected {k}" for k in got if k not in exp]
            return ("PASS" if not d else "FAIL"),"; ".join(d) or str(got)
        T(f"PA-PLAN-{sub}{p}","Get Plans",f"Covers & sums insured – {nm} Plan {p} per spec","per spec 'Coverages and Sum Assured'",f)
for mode,mn in ((2,"Annual"),(1,"Single")):
  for sub,nm in ((1,"With TTD"),(2,"Without TTD")):
    for p in range(1,6):
        def f(sub=sub,p=p,mode=mode):
            r=call("proposal",mk(sub,p,mode))
            if not okp(r): return "FAIL",err(r)
            j=r[1]; lob=j["PolicyLobList"][0]; d=[]
            if lob.get("DuePremium")!=PREM[sub][p-1]: d.append(f"premium {lob.get('DuePremium')}≠{PREM[sub][p-1]}")
            if abs((lob.get("Commission") or 0)-COMM[sub][p-1])>0.011: d.append(f"commission {lob.get('Commission')}≠{COMM[sub][p-1]}")
            sc=spec_cov(sub,p); c=covs(j,p)
            for k,v in sc.items():
                if c.get(k)!=v: d.append(f"{k} {c.get(k)}≠{v}")
            extra=[k for k in c if k not in sc]
            if extra: d.append(f"unexpected covers {extra}")
            if j["SumInsured"]!=sum(sc.values()) and j["SumInsured"]!=sum(v for k,v in sc.items() if k in("ACD","PTD","PPD","TTD","REX")) : d.append(f"total SumInsured {j['SumInsured']} (selected plan benefits {sum(sc.values())}, PlanList entries {len(j['PolicyLobList'][0]['PolicyRiskList'][0]['PlanList'])})")
            S[f"p{mode}{sub}{p}"]=j["ProposalNo"]
            return ("PASS" if not d else "FAIL"),f"{j['ProposalNo']} prem={lob.get('DuePremium')} comm={lob.get('Commission')}"+("; "+"; ".join(d) if d else "")
        T(f"PA-PREM-{mn[0]}{sub}{p}","Premium & Covers",f"{mn} – {nm} Plan {p}: premium, commission, covers","premium %s commission %s"%(PREM[sub][p-1],COMM[sub][p-1]),f,"Critical")
def f():
    r=call("proposal",mk(1,1,2,ch=False)); return ("PASS" if okp(r) else "FAIL"),(r[1]["ProposalNo"]+" prem "+str(r[1]["PolicyLobList"][0]["DuePremium"]) if okp(r) else err(r))
T("PA-COL-01","Collection check","Proposal request without ChannelCode (as in collection) works","200",f,"Medium")
def f():
    b=json.loads(items["Proposal API"]["request"]["body"]["raw"]); r=call("proposal",b); return ("FAIL" if not okp(r) else "PASS"),"Collection 'Proposal API' as-is (ProductSubcode 2 = Without TTD but TTD cover sent): "+(err(r) if not okp(r) else "ok")
T("PA-COL-02","Collection check","Sample 'Proposal API' body (sub 2 + TTD cover) executes","200",f,"Medium")
def f():
    r=call("proposal",{**mk(2,1,2),"ProductSubcode":"2"}); return ("PASS" if okp(r) else "FAIL"),"Without TTD with correct 5 covers → "+(r[1]["ProposalNo"] if okp(r) else err(r))
T("PA-COL-03","Collection check","Without-TTD proposal with correct cover list works","200",f,"Medium")
# lifecycle
r=call("proposal",mk(1,1,2)); S["lc"]=r[1]["ProposalNo"]
def f():
    r=call("update-proposal",{**mk(1,3,2),"ProposalNo":S["lc"]}); j=r[1]
    ok=okp(r) and j["PolicyLobList"][0]["DuePremium"]==124 and covs(j,3).get("ACD")==32000
    return ("PASS" if ok else "FAIL"),f"Plan 1→3: premium {j['PolicyLobList'][0]['DuePremium'] if okp(r) else err(r)}, ACD {covs(j,3).get('ACD') if okp(r) else ''}"
T("PA-LC-01","Lifecycle","Update proposal: plan change re-prices (68→124) and updates covers","premium 124, ACD 32000",f,"Critical")
def f():
    r=call("update-proposal",{**mk(2,2,1,3),"ProposalNo":S["lc"]}); j=r[1]; ok=okp(r) and j["PolicyLobList"][0]["DuePremium"]==81 and str(j["ProductSubcode"])=="2" and "TTD" not in covs(j,2)
    return ("PASS" if ok else "FAIL"),f"With→Without TTD, Single, term 3: premium {j['PolicyLobList'][0]['DuePremium'] if okp(r) else err(r)}; covers {covs(j,2) if okp(r) else ''}"
T("PA-LC-02","Lifecycle","Update proposal: switch With→Without TTD removes TTD cover","premium 81, no TTD",f,"High")
def f():
    j=call("load-policy",method="GET",params={"proposalNo":S["lc"]})[1]; return ("PASS" if j.get("ProposalNo")==S["lc"] and j["PolicyLobList"][0]["DuePremium"]==81 else "FAIL"),f"load → {j.get('ProposalNo')} prem {j['PolicyLobList'][0]['DuePremium']}"
T("PA-LC-03","Lifecycle","Load proposal returns latest saved data","premium 81",f)
def f():
    r=call("issue",{"ProposalNo":S["lc"],"ProductCode":"PA001"}); j=r[1]; S["lc_pol"]=j.get("PolicyNo")
    ok=r[0]==200 and re.fullmatch(r"POPA001\d{8}",str(j.get("PolicyNo"))) and j["ProposalStatus"]=="3" and j["PolicyStatus"]==2
    return ("PASS" if ok else "FAIL"),f"{j.get('PolicyNo')} ProposalStatus {j.get('ProposalStatus')} PolicyStatus {j.get('PolicyStatus')}" if r[0]==200 else err(r)
T("PA-LC-04","Lifecycle","Issue policy (POPA001########, Effective)","PolicyStatus 2",f,"Critical")
def f():
    j=call("load-policy",method="GET",params={"policyNo":S["lc_pol"]})[1]; return ("PASS" if j.get("PolicyNo")==S["lc_pol"] and j["PolicyLobList"][0]["DuePremium"]==81 else "FAIL"),f"{j.get('PolicyNo')} prem {j['PolicyLobList'][0]['DuePremium']}"
T("PA-LC-05","Lifecycle","Load policy by PolicyNo","same data",f)
def f():
    pn=call("proposal",mk(1,2,2))[1]["ProposalNo"]; r=call("proposal-reject",{"ProposalNo":pn,"ProposalRejectDesc":"checker rejected","ProductCode":"PA001"}); st=call("load-policy",method="GET",params={"proposalNo":pn})[1]["ProposalStatus"]
    return ("PASS" if r[0]==200 and st=="4" else "FAIL"),f"reject {r[0]} {r[1]}; status after {st}"
T("PA-LC-06","Lifecycle","Proposal reject sets status Rejected (4)","status 4",f,"Critical")
def f():
    r=call("issue",{"ProposalNo":S["lc"],"ProductCode":"PA001"}); return "OBSERVATION",f"Re-issue of issued proposal → {err(r) if r[0]!=200 else 'HTTP 200 '+str(r[1].get('PolicyNo'))}"
T("PA-LC-07","Lifecycle","Re-issue of issued proposal","no duplicate policy",f,"Medium")
# docs
def raw(ep,b): return requests.post(F+ep,headers={"Content-Type":"application/json","Authorization":"Bearer "+token()},json=b,timeout=90)
def pdf(b,name):
    open(name,"wb").write(b); return subprocess.run(["pdftotext","-layout",name,"-"],capture_output=True,text=True).stdout
S["d1"]=call("proposal",mk(1,3,2))[1]["ProposalNo"]; S["d1p"]=call("issue",{"ProposalNo":S["d1"],"ProductCode":"PA001"})[1]["PolicyNo"]
S["d2"]=call("proposal",mk(2,2,1,4))[1]["ProposalNo"]; S["d2p"]=call("issue",{"ProposalNo":S["d2"],"ProductCode":"PA001"})[1]["PolicyNo"]
def f():
    r=raw("doc_generation",{"DocType":"Application","ProposalNo":S["d1"],"ProductSubcode":"1","ProductCode":"PA001","ChannelCode":"SOHAR"}); t=pdf(r.content,"d1a.pdf") if r.content[:4]==b"%PDF" else ""
    need=["Personal Accident","Mohamed","32000","TTD","124","Sayyed","Plan 3"]; miss=[n for n in need if n not in t]; return ("PASS" if t and not miss else "FAIL"),f"PDF {len(r.content)}B missing {miss}" if t else r.text[:200]
T("PA-DOC-01","Documents","Application form (With TTD, Plan 3, Annual) populated","name, plan, SIs, premium, beneficiary",f,"Critical")
def f():
    r=raw("doc_generation",{"DocType":"Policy","PolicyNo":S["d1p"],"ProductSubcode":"1","ProductCode":"PA001","ChannelCode":"SOHAR"}); t=pdf(r.content,"d1c.pdf") if r.content[:4]==b"%PDF" else ""
    need=[S["d1p"],"Mohamed","32000","3000","20","1500","124"]; miss=[n for n in need if n not in t]; return ("PASS" if t and not miss else "FAIL"),f"PDF {len(r.content)}B missing {miss}" if t else r.text[:200]
T("PA-DOC-02","Documents","Certificate (With TTD, Plan 3, Annual) populated","cert no, SIs incl TTD 3000, HCB 20, REX 1500, premium 124",f,"Critical")
def f():
    r=raw("doc_generation",{"DocType":"Policy","PolicyNo":S["d2p"],"ProductSubcode":"2","ProductCode":"PA001","ChannelCode":"SOHAR"}); t=pdf(r.content,"d2c.pdf") if r.content[:4]==b"%PDF" else ""
    bad=[]; 
    for n in (S["d2p"],"20000","OMR 81","Single"):
        if n not in t: bad.append(f"missing {n}")
    if re.search(r"Temporary Total|TTD",t): bad.append("TTD row printed on Without-TTD certificate")
    pt=[l.strip()[:100] for l in t.splitlines() if "Period of Cover" in l]
    return ("PASS" if t and not bad else "FAIL"),"; ".join(bad) or f"OK {pt}"
T("PA-DOC-03","Documents","Certificate (Without TTD, Plan 2, Single 4 yrs): no TTD row, Single, period","no TTD, Single Premium, 4 yrs",f,"High")
def f():
    r=raw("doc_generation",{"DocType":"Application","ProposalNo":S["d2"],"ProductSubcode":"2","ProductCode":"PA001","ChannelCode":"SOHAR"}); t=pdf(r.content,"d2a.pdf") if r.content[:4]==b"%PDF" else ""
    return ("PASS" if t and not re.search(r"Temporary Total|TTD",t) else "FAIL"),"Without-TTD application: "+("TTD row present" if re.search(r"Temporary Total|TTD",t) else "no TTD row")
T("PA-DOC-04","Documents","Application form (Without TTD) has no TTD row","no TTD",f)
def f():
    t=open("d1a.pdf","rb") and subprocess.run(["pdftotext","-layout","d1a.pdf","-"],capture_output=True,text=True).stdout
    return ("FAIL" if "8096" in t else "PASS"),("PA application form also prints '8096 of the unearned Premium'" if "8096" in t else "cancellation wording OK")
T("PA-DOC-05","Documents","Application form cancellation clause prints 80%","80%",f)
def f():
    r=raw("doc_generation",items["doc_generation PDF"] and {"DocType":"Application","ProposalNo":S["d1"],"ProductSubcode":"1"}); return "OBSERVATION","Collection sample 'doc_generation PDF' (no ProductCode/ChannelCode) → "+r.text[:160]
T("PA-COL-04","Collection check","'doc_generation PDF' sample body (no ProductCode) runs","PDF",f,"Medium")
def f():
    r=raw("application_doc_generation",{"proposalNo":S["d1"],"ProductSubcode":"1"}); return ("PASS" if r.content[:4]==b"%PDF" else "FAIL"),f"HTTP {r.status_code}, {'PDF' if r.content[:4]==b'%PDF' else r.text[:150]} (legacy endpoint)"
T("PA-COL-05","Collection check","'doc_generation PDF Copy' → application_doc_generation endpoint","PDF",f,"Low")
# feed
fb={"Conditions":{"ProductCode":"PA001"},"FromRangeConditions":{"EffectiveDate":"2026-10-14T00:00:00"},"ToRangeConditions":{"EffectiveDate":"2026-10-14T23:59:59"},"Module":"Policy","PageNo":1,"PageSize":50,"SearchType":"Policy","SortField":"index_time","SortType":"desc"}
fr=raw("generate-feedfile",fb); open("feed.xlsx","wb").write(fr.content); ws=openpyxl.load_workbook("feed.xlsx").active; v=list(ws.iter_rows(values_only=True)); H=[str(x) for x in v[0]]; RW=[dict(zip(H,map(str,x))) for x in v[1:]]; S["feed"]=(H,RW)
def f(): return ("PASS" if len(RW)>0 else "FAIL"),f"{len(H)} columns, {len(RW)} rows"
T("PA-FEED-01","Feed File","Feed generated for PA001","rows",f)
def f():
    n={r["Product Name"] for r in RW}; return ("PASS" if n<={"Personal Accident with TTD","Personal Accident without TTD"} else "FAIL"),f"Product names {sorted(n)}"
T("PA-FEED-02","Feed File","Product Name correct for PA","Personal Accident with/without TTD",f)
def f():
    r1=[r for r in RW if r["Policy No"]==S["d1p"]][0]; r2=[r for r in RW if r["Policy No"]==S["d2p"]][0]
    bad=[]
    if r1["Product Name"]!="Personal Accident with TTD": bad.append("p1 product "+r1["Product Name"])
    if r2["Product Name"]!="Personal Accident without TTD": bad.append("p2 product "+r2["Product Name"])
    if r1["Premium Amount"]!="124": bad.append("p1 premium "+r1["Premium Amount"])
    if r2["Premium Amount"]!="81" or r2["Premium Frequency"]!="Single Premium" or r2["Plan Term"]!="4": bad.append(f"p2 {r2['Premium Amount']}/{r2['Premium Frequency']}/{r2['Plan Term']}")
    return ("PASS" if not bad else "FAIL"),"; ".join(bad) or "premium/frequency/term/product OK for both"
T("PA-FEED-03","Feed File","Feed row values (premium, frequency, term, product) per policy","match",f,"High")
def f():
    bad=[r["Policy No"] for r in RW if r["Policy Status"]=="Effective" and r["Cancelled Date"] not in ("None","")]; return ("PASS" if not bad else "FAIL"),f"{len(bad)}/{len(RW)} Effective policies carry a Cancelled Date"
T("PA-FEED-04","Feed File","Cancelled Date blank for Effective policies","blank",f)
def f():
    miss=[c for c in ("Branch Code","LCCode","LGCode") if c not in H]; return ("PASS" if not miss else "FAIL"),f"missing {miss}"
T("PA-FEED-05","Feed File","Feed has Branch Code, LCCode, LGCode","present",f,"Low")
# cancel
def cc(pol,d): return call("cancel-check",{"PolicyNo":pol,"CancellationDate":d,"CancelReason":"Customer request","ChannelCode":"SOHAR"})
pn=call("proposal",mk(2,1,2))[1]["ProposalNo"]; cp=call("issue",{"ProposalNo":pn,"ProductCode":"PA001"})[1]["PolicyNo"]
def f():
    r=cc(cp,"2026-10-20"); j=r[1]; rd=j.get("RefundDetails",{}); return ("PASS" if r[0]==200 and rd.get("RefundPremium")==55 else "FAIL"),f"free-look refund {rd.get('RefundPremium')} type {rd.get('CancellationType')} FreeLookDays {j.get('PremiumDetails',{}).get('FreeLookDays')} carrier {j.get('CarrierName')}" if r[0]==200 else err(r)
T("PA-CAN-01","Cancellation","Cancel-check within free-look → 100% (55)","55",f,"Critical")
pn2=call("proposal",mk(1,2,2))[1]["ProposalNo"]; cp2=call("issue",{"ProposalNo":pn2,"ProductCode":"PA001"})[1]["PolicyNo"]
def f():
    j=cc(cp2,"2027-01-13")[1]; p=j["PremiumDetails"]; e=round(96*p["UnexpiredDays"]/p["PolicyPeriodDays"],2); ok=abs(p["ProRataPremium"]-e)<.02 and abs(j["RefundDetails"]["RefundPremium"]-round(e*.8,2))<.02
    return ("PASS" if ok else "FAIL"),f"day {p['DaysSinceCommencement']} prorata {p['ProRataPremium']} (exp {e}) refund {j['RefundDetails']['RefundPremium']} (exp {round(e*.8,2)})"
T("PA-CAN-02","Cancellation","Pro-rata, 80% of unearned (premium 96)","correct",f,"Critical")
def f():
    j=cc(cp2,"2026-10-20")[1]; return ("PASS" if j["PremiumDetails"]["DaysSinceCommencement"]==6 else "FAIL"),f"second cancel-check (date 2026-10-20) → day {j['PremiumDetails']['DaysSinceCommencement']}, {j['RefundDetails']['CancellationType']} (stale pending request?)"
T("PA-CAN-03","Cancellation","Repeat cancel-check recalculates for new date","day 6, FREE_LOOK",f,"Medium")
def f():
    j=cc(cp2,"2026-10-20")[1]; return ("PASS" if "Falcon" in j.get("CarrierName","") else "FAIL"),f"CarrierName {j.get('CarrierName')}"
T("PA-CAN-04","Cancellation","Carrier name Arabia Falcon","Arabia Falcon",f,"Medium")
def f():
    rq=cc(cp2,"2027-01-13")[1]["RequestNo"]; r=call("cancel-approve",{"PolicyNo":cp2,"RequestNo":rq,"Decision":"APPROVE","ChannelCode":"SOHAR"}); st=call("load-policy",method="GET",params={"policyNo":cp2})[1]["PolicyStatus"]
    return ("PASS" if r[0]==200 and st!=2 else "FAIL"),f"approve {r[0]}; policy status {st}"
T("PA-CAN-05","Cancellation","Cancel-approve cancels policy","status ≠ 2",f,"Critical")
# other host
def f():
    r=requests.post("https://sandbox-in-gw.insuremo.com/foundation/1.0/print/template",headers={"Authorization":"Bearer "+token(),"Content-Type":"application/json"},json={"policyNo":"POPA00100000002","outputFormat":"PDF","templateName":"PA_without_TTD_ApplicationForm_SCHEDULE_EN","version":"0","documentCode":"POLICY"},timeout=60)
    return "OBSERVATION",f"print/template (foundation gateway, separate host/token) with our UAT token → HTTP {r.status_code} {r.text[:120]}"
T("PA-COL-06","Collection check","print/template (foundation gateway)","PDF",f,"Low")
json.dump(R,open("pa_results.json","w"),indent=1,ensure_ascii=False)
from collections import Counter; print(Counter(x["status"] for x in R),len(R))
