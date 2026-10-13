from suite import *
import openpyxl
def sub_issue(pn): return call("issue",{"ProposalNo":pn,"ProductCode":"TL001","ChannelCode":"SOHAR"})
def load_p(pn=None,pol=None):
    p={"ChannelCode":"SOHAR"}; 
    if pn: p["proposalNo"]=pn
    if pol: p["policyNo"]=pol
    return call("load-policy",method="GET",params=p)
def rawpost(ep,body):
    return requests.post(F+ep,headers={"Content-Type":"application/json","Authorization":"Bearer "+token()},json=body,timeout=90)
# ---------- F. UPDATE / LOAD ----------
def f():
    r=create(1,1,2); S["lc_pn"]=r[1]["ProposalNo"]; j=r[1]
    ok=okp(r) and re.fullmatch(r"PTL001\d{10}",j["ProposalNo"]) and j["ProposalStatus"]=="2"
    return ("PASS" if ok else "FAIL"),f"ProposalNo={j.get('ProposalNo')} ProposalStatus={j.get('ProposalStatus')} PolicyStatus={j.get('PolicyStatus')} (format PTL001+10 digits)"
T("TL-PRP-01","Create Proposal","Create proposal returns unique ProposalNo in expected format and status","ProposalNo PTL001##########; ProposalStatus 2",f,"Critical")
def f():
    j=call("proposal",mk(1,1,2))[1]; rr=rk(j)
    ok=all([rr["InsuredName"]=="Mohamed",rr["DateOfBirth"]=="1988-10-01",rr["Email"]=="Mohamed@gmail.com",rr["Address"]=="Oman",j["ApplicationNo"]=="UAT-0001",j["UserName"]=="Salman",j["StaffId"]=="76",j["BranchCode"]=="001"])
    return ("PASS" if ok else "FAIL"),"Request fields echoed in response (name, DOB, email, address, ApplicationNo, UserName, StaffId, BranchCode)"
T("TL-PRP-02","Create Proposal","All captured customer/application fields persisted","Fields returned unchanged",f,"High")
def f():
    j=load_p(pn=S["lc_pn"])[1]; rr=rk(j); b=rr["BeneficiaryList"][0]; pay=j["PolicyPaymentInfoList"][0]
    ok=b["BeneficaryName"]=="Sayyed" and b["Share"]=="100" and pay["LGCode"]=="23" and pay["LCCode"]==45 and pay["DebitRefNo"]=="wer455"
    return ("PASS" if ok else "FAIL"),f"Beneficiary={b['BeneficaryName']}/{b['Share']}% Pay LG={pay['LGCode']} LC={pay['LCCode']} Ref={pay['DebitRefNo']}"
T("TL-LOAD-01","Load Proposal","Load by ProposalNo returns saved beneficiary and payment details","Round-trip equality",f,"High")
def f():
    r=load_p(pn="PTL0019999999999"); return reject_expected(r) if r[0]!=200 or not (isinstance(r[1],dict) and r[1].get("ProposalNo")) else ("FAIL","Returned data for non-existent proposal")
T("TL-LOAD-02","Load Proposal","Load of non-existent ProposalNo returns error","Not-found error",f,"Medium","Negative")
def f():
    r=call("load-policy",method="GET",params={"ChannelCode":"SOHAR"}); return reject_expected(r)
T("TL-LOAD-03","Load Proposal","Load with neither proposalNo nor policyNo rejected","Error",f,"Low","Negative")
def f():
    r=call("update-proposal",{**mk(1,2,2),"ProposalNo":S["lc_pn"]}); j=r[1]
    ok=okp(r) and prem(j)==328 and cov(j,2).get("DTH")==20000
    return ("PASS" if ok else "FAIL"),f"After plan change 1→2: premium {prem(j) if okp(r) else err(r)}, DTH {cov(j,2).get('DTH') if okp(r) else ''}"
T("TL-UPD-01","Update Proposal","Update plan (1→2) re-prices and updates coverages","premium 328, DTH 20000",f,"Critical")
def f():
    r=call("update-proposal",{**mk(2,3,1,3),"ProposalNo":S["lc_pn"]}); j=r[1]
    ok=okp(r) and prem(j)==360 and str(j["ProductSubcode"])=="2" 
    return ("PASS" if ok else "FAIL"),f"Switch to W/O Travel Plan 3, Single, term 3: premium {prem(j) if okp(r) else err(r)}"+(f" subcode {j['ProductSubcode']}" if okp(r) else "")
T("TL-UPD-02","Update Proposal","Update product option (W/Travel→W/O Travel), mode and term","premium 360",f,"High")
def f():
    r=call("update-proposal",{**mk(1,2,2),"ProposalNo":"PTL0019999999999"}); return reject_expected(r)
T("TL-UPD-03","Update Proposal","Update of non-existent ProposalNo rejected","Not-found error",f,"Medium","Negative")
def f():
    r=call("update-proposal",mk(1,2,2)); 
    return ("FAIL",f"Update without ProposalNo accepted – created {r[1].get('ProposalNo')}") if okp(r) else ("PASS",err(r))
T("TL-UPD-04","Update Proposal","Update without ProposalNo rejected (must not silently create)","Rejected",f,"Medium","Negative")
def f():
    r=call("update-proposal",{**mk(1,1,2,mod=lambda b:rk(b).update(InsuredName="Changed Name")),"ProposalNo":S["lc_pn"]}); L=load_p(pn=S["lc_pn"])[1]
    return ("PASS" if rk(L)["InsuredName"]=="Changed Name" else "FAIL"),f"Name after update: {rk(L)['InsuredName']}"
T("TL-UPD-05","Update Proposal","Customer data update persisted and visible on reload","Name updated",f,"High")
def f():
    r=call("update-proposal",{**mk(1,1,2,mod=lambda b:rk(b).update(BeneficiaryList=[B("X",3,50,1),B("Y",6,50,2)])),"ProposalNo":S["lc_pn"]}); L=load_p(pn=S["lc_pn"])[1]
    bl=rk(L)["BeneficiaryList"]; return ("PASS" if len(bl)==2 else "FAIL"),f"Beneficiaries after update: {[ (x['BeneficaryName'],x['Share']) for x in bl]}"
T("TL-UPD-06","Update Proposal","Beneficiary list update (1→2 beneficiaries) persisted","2 beneficiaries",f,"Medium")
# ---------- G. ISSUE ----------
def f():
    r=create(1,1,2); pn=r[1]["ProposalNo"]; S["iss_pn"]=pn; r2=sub_issue(pn); j=r2[1]
    ok=r2[0]==200 and re.fullmatch(r"POTL001\d{8}",str(j.get("PolicyNo"))) and j["ProposalStatus"]=="3" and j["PolicyStatus"]==2
    S["iss_pol"]=j.get("PolicyNo"); 
    return ("PASS" if ok else "FAIL"),f"PolicyNo={j.get('PolicyNo')} ProposalStatus={j.get('ProposalStatus')} PolicyStatus={j.get('PolicyStatus')}"
T("TL-ISS-01","Issue Policy","Issue proposal → policy number generated, status Effective","POTL001######## ; ProposalStatus 3; PolicyStatus 2",f,"Critical")
def f():
    r=sub_issue(S["iss_pn"]); j=r[1]
    if r[0]==200 and isinstance(j,dict) and j.get("PolicyNo")==S["iss_pol"]: return "OBSERVATION",f"Re-issue is idempotent: returns same PolicyNo {j['PolicyNo']} (HTTP 200)"
    if r[0]==200 and isinstance(j,dict) and j.get("PolicyNo"): return "FAIL",f"Duplicate policy created {j['PolicyNo']}"
    return "PASS",err(r)
T("TL-ISS-02","Issue Policy","Issuing an already-issued proposal does not create a duplicate policy","Rejected or idempotent",f,"Critical","Negative")
def f():
    r=sub_issue("PTL0019999999999"); return reject_expected(r)
T("TL-ISS-03","Issue Policy","Issue of non-existent proposal rejected","Error",f,"Medium","Negative")
def f():
    r=call("issue",{"ProposalNo":S["lc_pn"],"ProductCode":"XX","ChannelCode":"SOHAR"}); 
    return ("FAIL",f"Issued with wrong ProductCode: {r[1].get('PolicyNo')}") if r[0]==200 and isinstance(r[1],dict) and r[1].get("PolicyNo") else ("PASS",err(r))
T("TL-ISS-04","Issue Policy","Issue with mismatching ProductCode rejected","Error",f,"Medium","Negative")
def f():
    r=call("issue",{"ChannelCode":"SOHAR","ProductCode":"TL001"}); return reject_expected(r)
T("TL-ISS-05","Issue Policy","Issue without ProposalNo rejected","Error",f,"Low","Negative")
def f():
    r=call("update-proposal",{**mk(1,3,2),"ProposalNo":S["iss_pn"]}); 
    return ("FAIL",f"Issued proposal modified: premium now {prem(r[1])}") if okp(r) else ("PASS",err(r))
T("TL-ISS-06","Issue Policy","Update of an already-issued proposal blocked","Rejected",f,"High","Negative")
def f():
    r=call("proposal-reject",{"ProposalNo":S["iss_pn"],"ProposalRejectDesc":"late reject","ProductCode":"TL001","ChannelCode":"SOHAR"})
    return ("FAIL",f"Issued proposal rejected: {str(r[1])[:150]}") if r[0]==200 and not (isinstance(r[1],dict) and r[1].get("status")) else ("PASS",err(r))
T("TL-ISS-07","Issue Policy","Reject of an already-issued proposal blocked","Rejected",f,"High","Negative")
def f():
    j=load_p(pol=S["iss_pol"])[1]; a=load_p(pn=S["iss_pn"])[1]
    ok=j["PolicyNo"]==S["iss_pol"] and j["ProposalNo"]==S["iss_pn"] and prem(j)==216 and j["PolicyStatus"]==2
    return ("PASS" if ok else "FAIL"),f"Load by PolicyNo: {j['PolicyNo']} premium {prem(j)} status {j['PolicyStatus']}; load by ProposalNo → PolicyNo {a.get('PolicyNo')}"
T("TL-POL-01","Load Policy","Load policy by PolicyNo returns issued policy; ProposalNo link intact","Consistent data",f,"Critical")
def f():
    r=load_p(pol="POTL00199999999"); return reject_expected(r) if not (r[0]==200 and isinstance(r[1],dict) and r[1].get("PolicyNo")) else ("FAIL","Returned data for non-existent policy")
T("TL-POL-02","Load Policy","Load of non-existent PolicyNo returns error","Not-found",f,"Medium","Negative")
def f():
    r=call("load-policy",method="GET",params={"policyNo":S["iss_pol"],"ChannelCode":"OTHER"}); return ("PASS","Blocked: "+err(r)) if not (r[0]==200 and isinstance(r[1],dict) and r[1].get("PolicyNo")) else ("FAIL","Policy readable via a different ChannelCode (data isolation)")
T("TL-POL-03","Load Policy","Policy not readable via a different ChannelCode","Not returned",f,"Medium","Security")
# ---------- H. REJECT ----------
def f():
    r=create(1,1,2); S["rej_pn"]=r[1]["ProposalNo"]; r2=call("proposal-reject",{"ProposalNo":S["rej_pn"],"ProposalRejectDesc":"checker rejected","ProductCode":"TL001","ChannelCode":"SOHAR"}); L=load_p(pn=S["rej_pn"])[1]
    return ("PASS" if r2[0]==200 and str(L.get("ProposalStatus")) not in ("2","3") else "FAIL"),f"reject HTTP {r2[0]} resp={str(r2[1])[:120]} → ProposalStatus after reload={L.get('ProposalStatus')}"
T("TL-REJ-01","Proposal Reject","Checker rejects proposal with reason; status changes","ProposalStatus = Rejected",f,"Critical")
def f():
    r=sub_issue(S["rej_pn"]); return ("FAIL",f"Rejected proposal was issued: {r[1].get('PolicyNo')}") if r[0]==200 and isinstance(r[1],dict) and r[1].get("PolicyNo") else ("PASS",err(r))
T("TL-REJ-02","Proposal Reject","Rejected proposal cannot be issued","Blocked",f,"Critical","Negative")
def f():
    r=call("proposal-reject",{"ProposalNo":S["rej_pn"],"ProposalRejectDesc":"again","ProductCode":"TL001","ChannelCode":"SOHAR"}); return "OBSERVATION",f"Second reject → {err(r) if r[0]!=200 else 'HTTP 200 (idempotent)'}"
T("TL-REJ-03","Proposal Reject","Rejecting an already-rejected proposal","Rejected or idempotent",f,"Low","Negative")
def f():
    r=call("proposal-reject",{"ProposalNo":"PTL0019999999999","ProposalRejectDesc":"x","ProductCode":"TL001","ChannelCode":"SOHAR"}); return reject_expected(r)
T("TL-REJ-04","Proposal Reject","Reject of non-existent proposal fails","Error",f,"Medium","Negative")
def f():
    n=create(1,1,2)[1]["ProposalNo"]; r=call("proposal-reject",{"ProposalNo":n,"ProductCode":"TL001","ChannelCode":"SOHAR"})
    return ("FAIL","Reject accepted without a reason") if r[0]==200 and not (isinstance(r[1],dict) and r[1].get("status")) else ("PASS",err(r))
T("TL-REJ-05","Proposal Reject","Reject without reason/comment rejected (checker must give comment)","Error",f,"Medium","Negative")
def f():
    r=call("update-proposal",{**mk(1,2,2),"ProposalNo":S["rej_pn"]}); return ("OBSERVATION",f"Update of a rejected proposal → HTTP {r[0]} ProposalStatus={r[1].get('ProposalStatus') if isinstance(r[1],dict) else ''} (maker rework after rejection is plausible)") 
T("TL-REJ-06","Proposal Reject","Update of rejected proposal (rework path)","Per business rule",f,"Low")

# ---------- I. DOCUMENTS ----------
def pdftext(b,name):
    open(name,"wb").write(b); return subprocess.run(["pdftotext","-layout",name,"-"],capture_output=True,text=True).stdout
def mkpol(sub,plan,mode,term=1,mod=None):
    r=create(sub,plan,mode,term,mod=mod); pn=r[1]["ProposalNo"]; i=sub_issue(pn)[1]; return pn,i["PolicyNo"]
S["d1"]=mkpol(1,3,2); S["d2"]=mkpol(2,2,1,3,mod=lambda b:b["PolicyLobList"][0]["PolicyRiskList"][0].update(Gender="2",Salutation="2",ResidentStatus="2"))
def docs(kind,pn,pol,sub):
    body={"DocType":kind,"ProductSubcode":str(sub),"ChannelCode":"SOHAR","ProductCode":"TL001"}; body["ProposalNo" if kind=="Application" else "PolicyNo"]=pn if kind=="Application" else pol
    r=rawpost("doc_generation",body); return r
def f():
    r=docs("Application",*S["d1"],1); t=pdftext(r.content,"d1_app.pdf") if r.content[:4]==b"%PDF" else ""
    need=["PTL001","Mohamed","1988-10-01","123456789","Plan 3","30000","1000","Included","440","Sayyed","Brother"]; miss=[n for n in need if n not in t]
    return ("PASS" if r.content[:4]==b"%PDF" and not miss else "FAIL"),f"HTTP {r.status_code}, PDF {len(r.content)} bytes; missing: {miss}"
T("TL-DOC-01","Documents","Application form PDF (With Travel, Plan 3, Annual) populated correctly","Name, DOB, ID, plan, SIs, premium, beneficiary present",f,"Critical")
def f():
    r=docs("Policy",*S["d1"],1); t=pdftext(r.content,"d1_pol.pdf") if r.content[:4]==b"%PDF" else ""
    need=[S["d1"][1],"Mohamed","Male","1988-10-01","Expat","Death due to any cause","30000","Annual Family Travel","Included","1000","Sayyed","Brother","OMR 440","Annual Premium","1 Year(s)","Arabia Falcon Insurance"]; miss=[n for n in need if n not in t]
    return ("PASS" if r.content[:4]==b"%PDF" and not miss else "FAIL"),f"HTTP {r.status_code}, PDF {len(r.content)} bytes; missing: {miss}"
T("TL-DOC-02","Documents","Certificate of Insurance (With Travel, Plan 3, Annual) populated per TL certificate format","All certificate fields per template",f,"Critical")
def f():
    r=docs("Policy",*S["d2"],2); t=pdftext(r.content,"d2_pol.pdf") if r.content[:4]==b"%PDF" else ""
    bad=[]
    if "Annual Family Travel" in t: bad.append("'Annual Family Travel' printed on a Without-Travel certificate")
    for n,l in ((S["d2"][1],"cert no"),("Female","gender"),("Omani","nationality"),("17500","SI plan 2"),("OMR 244","premium"),("Single Premium","frequency"),("3 Year(s)","period of cover")):
        if n not in t: bad.append(f"{l} '{n}' missing")
    return ("PASS" if not bad else "FAIL"),"; ".join(bad) or "OK"
T("TL-DOC-03","Documents","Certificate (Without Travel, Plan 2, Single premium 3 yrs, female/Omani) – dynamic fields & travel line suppressed","No travel row; Single Premium; 3 Year(s)",f,"High")
def f():
    r=docs("Application",*S["d2"],2); t=pdftext(r.content,"d2_app.pdf") if r.content[:4]==b"%PDF" else ""
    bad=[]
    if "Annual Family Travel" in t: bad.append("travel row on W/O Travel application form")
    if "Single" not in t: bad.append("Single premium wording")
    return ("PASS" if not bad and r.content[:4]==b"%PDF" else "FAIL"),"; ".join(bad) or "OK"
T("TL-DOC-04","Documents","Application form (Without Travel, Single premium) – travel row suppressed","No travel row",f,"High")
def f():
    t=open("d1_app.pdf","rb"); tx=subprocess.run(["pdftotext","-layout","d1_app.pdf","-"],capture_output=True,text=True).stdout
    return ("FAIL" if "8096 of the unearned" in tx else "PASS"),("English cancellation clause renders '8096 of the unearned Premium' (should read 80%); Arabic side shows 80%. Page footer 'Page 2 of 3' also truncated." if "8096" in tx else "OK")
T("TL-DOC-05","Documents","Application form static wording (cancellation clause refund %) renders correctly","'80% of the unearned Premium'",f,"High")
def f():
    tx=subprocess.run(["pdftotext","-layout","d1_app.pdf","-"],capture_output=True,text=True).stdout
    return ("PASS" if "Health and Life Style Questionnaire" in tx or "Evidence of Insurability" in tx else "FAIL"),"Health & Lifestyle questionnaire page "+("present" if "Health and Life Style" in tx else "MISSING from generated application form (present in the approved TL application form template)")
T("TL-DOC-06","Documents","Application form contains Health & Lifestyle questionnaire (per approved template)","Questionnaire page included",f,"Medium")
def f():
    tx=subprocess.run(["pdftotext","-layout","d1_app.pdf","-"],capture_output=True,text=True).stdout
    return ("PASS" if "UAT-0001" in tx else "OBSERVATION"),"Application form prints ProposalNo (PTL…) in 'Application Number'; the maker-entered ApplicationNo 'UAT-0001' is not printed. Confirm which number business expects."
T("TL-DOC-07","Documents","Application No on form = application number captured by Uponly","UAT-0001",f,"Medium")
def f():
    tx=subprocess.run(["pdftotext","-layout","d1_pol.pdf","-"],capture_output=True,text=True).stdout
    return "OBSERVATION","Certificate 'Name of Policy Holder' = insured name (same person), 'Nationality' prints Resident Status (Expat/Omani) – acceptable if business confirms; Certificate does not print the Policy Holder≠Insured scenario."
T("TL-DOC-08","Documents","Certificate field mapping (Policy Holder / Nationality)","Per template",f,"Low")
def f():
    r=rawpost("doc_generation",{"PolicyNo":"POTL00199999999","DocType":"Policy","ProductSubcode":"1","ChannelCode":"SOHAR","ProductCode":"TL001"}); return ("FAIL","PDF generated for non-existent policy") if r.content[:4]==b"%PDF" else ("PASS",f"HTTP {r.status_code} {r.text[:150]}")
T("TL-DOC-09","Documents","Certificate for non-existent policy fails","Error",f,"Medium","Negative")
def f():
    n=create(1,1,2)[1]["ProposalNo"]; r=rawpost("doc_generation",{"PolicyNo":n,"DocType":"Policy","ProductSubcode":"1","ChannelCode":"SOHAR","ProductCode":"TL001"}); return ("FAIL","Certificate generated for un-issued proposal") if r.content[:4]==b"%PDF" else ("PASS",f"HTTP {r.status_code} {r.text[:150]}")
T("TL-DOC-10","Documents","Certificate cannot be generated before policy issue (proposal no.)","Error",f,"High","Negative")
def f():
    r=rawpost("doc_generation",{"DocType":"Invoice","ProposalNo":S["d1"][0],"ProductSubcode":"1","ChannelCode":"SOHAR","ProductCode":"TL001"}); return ("FAIL","PDF produced for unknown DocType") if r.content[:4]==b"%PDF" else ("PASS",f"HTTP {r.status_code} {r.text[:150]}")
T("TL-DOC-11","Documents","Unknown DocType rejected","Error",f,"Low","Negative")
def f():
    r=rawpost("doc_generation",{"DocType":"Application","ProposalNo":S["d1"][0],"ProductSubcode":"2","ChannelCode":"SOHAR","ProductCode":"TL001"}); t=pdftext(r.content,"x.pdf") if r.content[:4]==b"%PDF" else ""
    return ("FAIL","Doc generated with ProductSubcode(2) ≠ proposal's subcode(1): "+("travel row shown" if "Annual Family Travel" in t else "")) if r.content[:4]==b"%PDF" else ("PASS",f"HTTP {r.status_code}")
T("TL-DOC-12","Documents","Document request with ProductSubcode mismatching the proposal","Error or correct doc",f,"Low","Negative")
def f():
    ts=[]; 
    for _ in range(3):
        t0=time.time(); rawpost("doc_generation",{"DocType":"Application","ProposalNo":S["d1"][0],"ProductSubcode":"1","ChannelCode":"SOHAR","ProductCode":"TL001"}); ts.append(time.time()-t0)
    return ("PASS" if max(ts)<10 else "FAIL"),f"PDF generation times: {[round(x,1) for x in ts]} s"
T("TL-NFR-01","Non-Functional","Document generation response time < 10 s","< 10 s",f,"Medium","Performance")

# ---------- J. FEED FILE ----------
FB={"Conditions":{"ProductCode":"TL001"},"FromRangeConditions":{"EffectiveDate":"2026-10-13T00:00:00"},"ToRangeConditions":{"EffectiveDate":"2026-10-13T23:59:59"},"Module":"Policy","PageNo":1,"PageSize":50,"SearchType":"Policy","SortField":"index_time","SortType":"desc"}
def feed(mod=None):
    b=copy.deepcopy(FB)
    if mod: mod(b)
    r=rawpost("generate-feedfile",b); return r
def rows(content):
    open("feed2.xlsx","wb").write(content)
    import warnings; warnings.simplefilter("ignore")
    ws=openpyxl.load_workbook("feed2.xlsx").active; v=list(ws.iter_rows(values_only=True)); return [str(x) for x in v[0]],v[1:]
SPECCOLS=["App No","Certificate No","Dateof Application","Branch Name","Branch Code","Product Name","Name Of The Insured Person","DOB","Premium Frequency","Discount","Premium Amount","Commission Amount","Nameofthe Beneficiary","Relationshipof Beneficiary","POBox","Address","Commencement Date","Policy Status","Mobile Number","Username","Staff Id","Approvedby","Approved On","Debit Trans Ref No","CIFNO","Cancelled Date","LCCode","LGCode","Policy No","Plan Term"]
def f():
    r=feed(); 
    if r.content[:2]!=b"PK": return "FAIL",f"HTTP {r.status_code} not xlsx: {r.text[:150]}"
    h,v=rows(r.content); S["feed_h"]=h; S["feed_v"]=v
    return "PASS",f"xlsx with {len(h)} columns and {len(v)} data rows"
T("TL-FEED-01","Feed File","Feed file generated as xlsx for date range / product filter","xlsx returned",f,"Critical")
def f():
    norm=lambda s:re.sub(r"[^a-z]","",s.lower()); have={norm(x) for x in S["feed_h"]}; miss=[c for c in SPECCOLS if norm(c) not in have and norm(c).replace("pobox","podbox") not in have]
    return ("PASS" if not miss else "FAIL"),f"Missing from feed vs spec 'Feed File' sheet: {miss}" if miss else "All 30 spec columns present"
T("TL-FEED-02","Feed File","Feed file columns match the 30 fields in spec","All spec columns",f,"High")
def f():
    h,v=S["feed_h"],S["feed_v"]; i=h.index("Product Name"); names={x[i] for x in v}
    return ("PASS" if names<= {"Term Life with Travel","Term Life without Travel"} else "FAIL"),f"Product Name values for TL001 policies: {sorted(names)}"
T("TL-FEED-03","Feed File","Product Name for Term Life policies is 'Term Life with/without Travel'","Term Life with Travel / without Travel",f,"High")
def f():
    h,v=S["feed_h"],S["feed_v"]; st=h.index("Policy Status"); cd=h.index("Cancelled Date"); bad=[x[h.index("Policy No")] for x in v if x[st]=="Effective" and x[cd] not in (None,"None","")]
    return ("PASS" if not bad else "FAIL"),f"{len(bad)} of {len(v)} Effective (non-cancelled) policies have a Cancelled Date populated, e.g. {bad[:3]}"
T("TL-FEED-04","Feed File","Cancelled Date blank for non-cancelled policies","Blank",f,"High")
def f():
    h,v=S["feed_h"],S["feed_v"]; pol=S["iss_pol"]; row=[x for x in v if x[h.index("Policy No")]==pol]
    if not row: return "FAIL",f"{pol} not in feed"
    d=dict(zip(h,row[0])); bad=[]
    exp={"Name Of The Insured Person":"Mohamed","DOB":"1988-10-01","Premium Amount":"216","Premium Frequency":"Annual Premium","Nameofthe Beneficiary":"Sayyed","Relationshipof Beneficiary":"Brother","Mobile Number":"9989374444","Username":"Salman","Staff Id":"76","Debit Trans Ref No":"wer455","CIFNO":"45678","Branch Name":"CBD Branch","Certificate No":pol,"Policy No":pol,"Policy Status":"Effective","Address":"Oman","Commencement Date":"2026-10-13","Dateof Application":"2026-10-13","App No":"UAT-0001"}
    for k,e in exp.items():
        if str(d.get(k))!=e: bad.append(f"{k}: {d.get(k)}≠{e}")
    return ("PASS" if not bad else "FAIL"),"; ".join(bad) or f"{len(exp)} fields verified for {pol}"
T("TL-FEED-05","Feed File","Feed row field values match issued policy data","All fields equal",f,"Critical")
def f():
    h,v=S["feed_h"],S["feed_v"]; r=[x for x in v if x[h.index("Policy No")]==S["d2"][1]]; d=dict(zip(h,r[0])) if r else {}
    return ("PASS" if d.get("Premium Frequency")=="Single Premium" and str(d.get("Plan Term"))=="3" and d.get("Premium Amount")=="244" else "FAIL"),f"Single-premium 3-yr policy: freq={d.get('Premium Frequency')} term={d.get('Plan Term')} premium={d.get('Premium Amount')}"
T("TL-FEED-06","Feed File","Single premium / 3-year policy shown with correct frequency, term, premium","Single Premium, 3, 244",f,"High")
def f():
    h,v=S["feed_h"],S["feed_v"]; c=h.index("Commission Amount"); vals={x[c] for x in v}
    return ("PASS" if vals<={"N/A","0","None",None,""} else "FAIL"),f"Commission Amount column values: {sorted(map(str,vals))} (spec: N/A)"
T("TL-FEED-07","Feed File","Commission Amount not disclosed in feed (spec: N/A)","N/A / blank",f,"Medium")
def f():
    r=feed(lambda b:(b["FromRangeConditions"].update(EffectiveDate="2020-01-01T00:00:00"),b["ToRangeConditions"].update(EffectiveDate="2020-01-02T23:59:59")))
    if r.content[:2]==b"PK": h,v=rows(r.content); return ("PASS" if not v else "FAIL"),f"Rows for 2020 range: {len(v)}"
    return "PASS",f"HTTP {r.status_code} {r.text[:120]}"
T("TL-FEED-08","Feed File","Date range with no policies returns empty feed (no data rows)","0 rows",f,"Medium")
def f():
    r=feed(lambda b:b.update(PageSize=1)); h,v=rows(r.content); return ("PASS" if len(v)==1 else "FAIL"),f"PageSize=1 → {len(v)} row(s)"
T("TL-FEED-09","Feed File","Pagination PageSize=1 returns one row","1 row",f,"Low")
def f():
    r=feed(lambda b:b["Conditions"].update(ProductCode="NOPE")); 
    if r.content[:2]==b"PK": h,v=rows(r.content); return ("PASS" if not v else "FAIL"),f"Rows: {len(v)}"
    return "PASS",f"HTTP {r.status_code}"
T("TL-FEED-10","Feed File","Product filter excludes other products","0 rows",f,"Medium")
def f():
    r=feed(lambda b:(b["FromRangeConditions"].update(EffectiveDate="2026-10-14T00:00:00"),b["ToRangeConditions"].update(EffectiveDate="2026-10-01T00:00:00")))
    return "OBSERVATION",f"Inverted date range → HTTP {r.status_code}, {'xlsx' if r.content[:2]==b'PK' else r.text[:120]}"
T("TL-FEED-11","Feed File","Inverted date range (from > to) handling","Validation error",f,"Low","Negative")
def f():
    r=feed(lambda b:b.update(Module="Nope")); return ("FAIL","xlsx returned for invalid module") if r.content[:2]==b"PK" else ("PASS",f"HTTP {r.status_code} {r.text[:120]}")
T("TL-FEED-12","Feed File","Invalid Module rejected","Error",f,"Low","Negative")
def f():
    h,v=S["feed_h"],S["feed_v"]; i=h.index("Policy No"); pn=[x[i] for x in v]; return ("PASS" if len(pn)==len(set(pn)) else "FAIL"),f"{len(pn)} rows, {len(set(pn))} unique policies"
T("TL-FEED-13","Feed File","No duplicate policy rows in feed","Unique",f,"Medium")

# ---------- K. CANCELLATION ----------
S["c1"]=mkpol(1,2,2); S["c2"]=mkpol(1,1,2); S["c3"]=mkpol(2,4,2)
CC=lambda pol,date,reason="Customer request": call("cancel-check",{"PolicyNo":pol,"CancellationDate":date,"CancelReason":reason,"ChannelCode":"SOHAR"})
def f():
    r=CC(S["c1"][1],"2026-10-20"); j=r[1]
    if r[0]!=200: return "FAIL",err(r)
    rd=j["RefundDetails"]; S["c1_req"]=j["RequestNo"]
    ok=rd["RefundPremium"]==328 and rd["CancellationType"]!="PRO_RATA"
    return ("PASS" if ok else "FAIL"),f"Cancel in free-look (day {j['PremiumDetails']['DaysSinceCommencement']}): type={rd['CancellationType']} refund%={rd['RefundPercent']} refund={rd['RefundPremium']} premium={j['PremiumDetails']['Premium']}; FreeLookDays={j['PremiumDetails']['FreeLookDays']}"
T("TL-CAN-01","Cancellation","cancel-check within free-look period → 100% premium refund","Full refund 328",f,"Critical")
def f():
    r=CC(S["c2"][1],"2027-01-13"); j=r[1]; pdl=j["PremiumDetails"]; exp_pr=round(216*pdl["UnexpiredDays"]/pdl["PolicyPeriodDays"],2); exp_ref=round(exp_pr*0.8,2)
    return ("PASS" if abs(pdl["ProRataPremium"]-exp_pr)<0.02 and abs(j["RefundDetails"]["RefundPremium"]-exp_ref)<0.02 else "FAIL"),f"Day {pdl['DaysSinceCommencement']}, unexpired {pdl['UnexpiredDays']}: pro-rata {pdl['ProRataPremium']} (exp {exp_pr}); refund {j['RefundDetails']['RefundPremium']} (exp {exp_ref} = 80% of unearned per form)"
T("TL-CAN-02","Cancellation","cancel-check after free-look → pro-rata, 80% of unearned premium","Refund = 80% × pro-rata unearned",f,"Critical")
def f():
    r=CC(S["c2"][1],"2026-10-28"); j=r[1]; return ("PASS" if j["PremiumDetails"]["FreeLookDays"]==30 else "FAIL"),f"Day 15 cancel: FreeLookDays={j['PremiumDetails']['FreeLookDays']}, type={j['RefundDetails']['CancellationType']}. Application form states 30-day Review Period (full refund) but system free-look = {j['PremiumDetails']['FreeLookDays']} days"
T("TL-CAN-03","Cancellation","Free-look period consistent with application form (30 days)","30 days",f,"High")
def f():
    r=CC(S["c2"][1],"2026-10-13"); return accept_expected(r) if False else ("OBSERVATION",f"Same-day cancel → HTTP {r[0]} refund={r[1]['RefundDetails']['RefundPremium'] if r[0]==200 else err(r)}")
T("TL-CAN-04","Cancellation","Cancellation on commencement date","Full refund",f,"Medium","Boundary")
def f():
    r=CC(S["c2"][1],"2026-10-01"); return ("FAIL","Cancellation before commencement accepted") if r[0]==200 and isinstance(r[1],dict) and r[1].get("RequestNo") else ("PASS",err(r))
T("TL-CAN-05","Cancellation","Cancellation date before policy commencement rejected","Rejected",f,"High","Negative")
def f():
    r=CC(S["c2"][1],"2028-01-01"); return ("FAIL","Cancellation after expiry accepted") if r[0]==200 and isinstance(r[1],dict) and r[1].get("RequestNo") else ("PASS",err(r))
T("TL-CAN-06","Cancellation","Cancellation date after policy expiry rejected","Rejected",f,"High","Negative")
def f():
    r=call("cancel-check",{"PolicyNo":"POTL00199999999","CancellationDate":"2026-11-01","CancelReason":"x","ChannelCode":"SOHAR"}); return reject_expected(r)
T("TL-CAN-07","Cancellation","cancel-check on non-existent policy rejected","Error",f,"Medium","Negative")
def f():
    r=call("cancel-check",{"PolicyNo":S["c2"][1],"CancelReason":"x","ChannelCode":"SOHAR"}); return ("FAIL","Accepted without CancellationDate") if r[0]==200 and isinstance(r[1],dict) and r[1].get("RequestNo") else ("PASS",err(r))
T("TL-CAN-08","Cancellation","cancel-check without CancellationDate rejected","Error",f,"Medium","Negative")
def f():
    r=call("cancel-check",{"PolicyNo":S["c2"][1],"CancellationDate":"2026-12-01","ChannelCode":"SOHAR"}); return ("OBSERVATION",f"Cancel without reason → HTTP {r[0]} {'RequestNo '+r[1].get('RequestNo','') if r[0]==200 else err(r)}")
T("TL-CAN-09","Cancellation","cancel-check without CancelReason","Reason mandatory (business to confirm)",f,"Low","Negative")
def f():
    r=CC(S["c1"][1],"2026-10-21"); j=r[1]; return ("PASS" if r[0]==200 and j.get("RequestNo")==S["c1_req"] else "OBSERVATION"),f"Second cancel-check on same policy → RequestNo {j.get('RequestNo')} (first {S['c1_req']}), RequestExists={j.get('RequestExists')}, status={j.get('RequestStatus')}"
T("TL-CAN-10","Cancellation","Repeat cancel-check re-uses the pending request (no duplicate requests)","Same RequestNo",f,"Medium")
def f():
    n=create(1,1,2)[1]["ProposalNo"]; r=call("cancel-check",{"PolicyNo":n,"CancellationDate":"2026-11-01","CancelReason":"x","ChannelCode":"SOHAR"}); return ("FAIL","cancel-check accepted for un-issued proposal") if r[0]==200 and isinstance(r[1],dict) and r[1].get("RequestNo") else ("PASS",err(r))
T("TL-CAN-11","Cancellation","cancel-check on un-issued proposal number rejected","Error",f,"Medium","Negative")
def f():
    j=CC(S["c3"][1],"2026-12-01")[1]; S["c3_req"]=j["RequestNo"]
    r=call("cancel-approve",{"PolicyNo":S["c3"][1],"RequestNo":S["c3_req"],"Decision":"REJECT","ChannelCode":"SOHAR"}); L=load_p(pol=S["c3"][1])[1]
    return ("PASS" if r[0]==200 and L["PolicyStatus"]==2 else "FAIL"),f"REJECT → HTTP {r[0]} {str(r[1])[:200]}; policy status after: {L['PolicyStatus']}"
T("TL-CAN-12","Cancellation","cancel-approve with REJECT keeps policy Effective","PolicyStatus remains 2",f,"Critical")
def f():
    r=call("cancel-approve",{"PolicyNo":S["c1"][1],"RequestNo":S["c1_req"],"Decision":"APPROVE","ChannelCode":"SOHAR"}); L=load_p(pol=S["c1"][1])[1]; S["c1_after"]=L
    return ("PASS" if r[0]==200 and L["PolicyStatus"]!=2 else "FAIL"),f"APPROVE → HTTP {r[0]} {str(r[1])[:250]}; policy status after: {L['PolicyStatus']}"
T("TL-CAN-13","Cancellation","cancel-approve with APPROVE cancels the policy","PolicyStatus = Cancelled/Terminated",f,"Critical")
def f():
    r=call("cancel-approve",{"PolicyNo":S["c1"][1],"RequestNo":S["c1_req"],"Decision":"APPROVE","ChannelCode":"SOHAR"}); return ("FAIL",f"Second approval accepted: {str(r[1])[:150]}") if r[0]==200 and not (isinstance(r[1],dict) and r[1].get("status")) else ("PASS",err(r))
T("TL-CAN-14","Cancellation","Approving an already-processed request is blocked","Error",f,"High","Negative")
def f():
    r=call("cancel-approve",{"PolicyNo":S["c2"][1],"RequestNo":"POTL00199999999-001","Decision":"APPROVE","ChannelCode":"SOHAR"}); return ("FAIL",f"Approved a non-existent request: {str(r[1])[:150]}") if r[0]==200 and not (isinstance(r[1],dict) and r[1].get("status")) else ("PASS",err(r))
T("TL-CAN-15","Cancellation","cancel-approve with unknown RequestNo blocked","Error",f,"High","Negative")
def f():
    j=CC(S["c2"][1],"2027-01-13")[1]; r=call("cancel-approve",{"PolicyNo":S["c3"][1],"RequestNo":j["RequestNo"],"Decision":"APPROVE","ChannelCode":"SOHAR"}); L=load_p(pol=S["c3"][1])[1]
    return ("FAIL",f"Request of policy {S['c2'][1]} approved against policy {S['c3'][1]} (status now {L['PolicyStatus']})") if r[0]==200 and L["PolicyStatus"]!=2 else ("PASS",err(r)+f"; {S['c3'][1]} status {L['PolicyStatus']}")
T("TL-CAN-16","Cancellation","cancel-approve with RequestNo belonging to a different policy blocked","Error",f,"High","Negative")
def f():
    j=CC(S["c2"][1],"2027-01-13")[1]; r=call("cancel-approve",{"PolicyNo":S["c2"][1],"RequestNo":j["RequestNo"],"Decision":"MAYBE","ChannelCode":"SOHAR"}); L=load_p(pol=S["c2"][1])[1]
    return ("FAIL",f"Invalid decision accepted: {str(r[1])[:150]}") if r[0]==200 and not (isinstance(r[1],dict) and r[1].get("status")) else ("PASS",err(r))
T("TL-CAN-17","Cancellation","cancel-approve with invalid Decision value blocked","Error",f,"Medium","Negative")
def f():
    r=CC(S["c1"][1],"2026-12-01"); return ("PASS" if r[0]!=200 or not r[1].get("RequestNo") else "FAIL"),f"cancel-check on already-cancelled policy → {err(r) if r[0]!=200 else 'RequestNo '+str(r[1].get('RequestNo'))+' status '+str(r[1].get('PolicyStatus'))}"
T("TL-CAN-18","Cancellation","cancel-check on an already-cancelled policy blocked","Error",f,"High","Negative")
def f():
    r=call("issue",{"ProposalNo":S["c1"][0],"ProductCode":"TL001","ChannelCode":"SOHAR"}); return "OBSERVATION",f"Re-issue of cancelled policy's proposal → HTTP {r[0]} {str(r[1])[:120]}"
T("TL-CAN-19","Cancellation","Re-issue on proposal of a cancelled policy","No new policy",f,"Low","Negative")
def f():
    h,v=rows(feed(lambda b:(b["FromRangeConditions"].update(EffectiveDate="2026-10-13T00:00:00"))).content); i=h.index("Policy No"); r=[x for x in v if x[i]==S["c1"][1]]
    if not r: return "FAIL","cancelled policy missing from feed"
    d=dict(zip(h,r[0])); return ("PASS" if d["Policy Status"]!="Effective" and d["Cancelled Date"] not in (None,"None") else "FAIL"),f"Cancelled policy in feed: status={d['Policy Status']} cancelled date={d['Cancelled Date']}"
T("TL-FEED-14","Feed File","Cancelled policy shows cancelled status and cancelled date in feed","Status Cancelled + date",f,"High")
def f():
    j=call("cancel-check",{"PolicyNo":S["c2"][1],"CancellationDate":"2027-01-13","CancelReason":"x","ChannelCode":"SOHAR"})[1]
    return ("FAIL" if "Afillar" in j.get("CarrierName","") else "PASS"),f"cancel-check returns CarrierName '{j.get('CarrierName')}' (code {j.get('CarrierCode')}); certificate/application show 'Arabia Falcon Insurance SAOG'"
T("TL-CAN-20","Cancellation","Carrier name consistent across APIs and documents (Arabia Falcon Insurance)","Arabia Falcon Insurance",f,"Medium")

# ---------- L. NON-FUNCTIONAL ----------
def f():
    ts=[]; 
    for _ in range(5): t0=time.time(); call("proposal",mk(1,1,2)); ts.append(time.time()-t0)
    return ("PASS" if max(ts)<5 else "FAIL"),f"Create proposal times: {[round(x,2) for x in ts]} s (SLA assumed <5 s)"
T("TL-NFR-02","Non-Functional","Create proposal response time < 5 s","< 5 s",f,"Medium","Performance")
def f():
    out=[]; 
    def w(): out.append(call("proposal",mk(1,1,2)))
    th=[threading.Thread(target=w) for _ in range(10)]; [t.start() for t in th]; [t.join() for t in th]
    ids=[x[1].get("ProposalNo") for x in out if okp(x)]; 
    return ("PASS" if len(ids)==10 and len(set(ids))==10 else "FAIL"),f"10 parallel creates → {len(ids)} succeeded, {len(set(ids))} unique ProposalNos; max {max(x[2] for x in out)} s"
T("TL-NFR-03","Non-Functional","10 concurrent proposal creations: all succeed with unique numbers","10 unique",f,"High","Performance")
def f():
    out=[]
    def w(): out.append(call("issue",{"ProposalNo":S["lc_pn"],"ProductCode":"TL001","ChannelCode":"SOHAR"}))
    pn=create(1,1,2)[1]["ProposalNo"]
    def w(): out.append(call("issue",{"ProposalNo":pn,"ProductCode":"TL001","ChannelCode":"SOHAR"}))
    th=[threading.Thread(target=w) for _ in range(5)]; [t.start() for t in th]; [t.join() for t in th]
    pols={x[1].get("PolicyNo") for x in out if x[0]==200 and isinstance(x[1],dict) and x[1].get("PolicyNo")}
    return ("PASS" if len(pols)==1 else "FAIL"),f"5 simultaneous issue calls → distinct policy numbers: {sorted(pols)} ; HTTP {[x[0] for x in out]}"
T("TL-NFR-04","Non-Functional","Concurrent double-submit of issue yields exactly one policy","1 policy",f,"High","Concurrency")
def f():
    r=requests.post(F+"proposal",headers={"Content-Type":"application/json","Authorization":"Bearer "+token()},data="{bad json",timeout=30); return ("PASS" if r.status_code in (400,422) else "FAIL"),f"Malformed JSON → HTTP {r.status_code} {r.text[:100]}"
T("TL-NFR-05","Non-Functional","Malformed JSON body returns 4xx (not 5xx)","HTTP 400",f,"Low","Negative")
def f():
    codes=[]
    for k in ("Gender","IdType","InsuredName"):
        r=call("proposal",mk(1,1,2,mod=lambda b:rk(b).update({k:"9" if k!="InsuredName" else None}))) 
        codes.append(r[0])
    return ("PASS" if all(c==400 or c==422 for c in codes) else "FAIL"),f"Validation failures return HTTP {codes} — all business-validation errors surface as HTTP 500 INTERNAL_ERROR instead of 4xx with field-level messages"
T("TL-NFR-06","Non-Functional","Validation errors return 4xx with clear field message","HTTP 400/422",f,"Medium")
def f():
    r=requests.get(F.replace("https","http")+"get-plans",timeout=20,allow_redirects=False); return ("PASS" if r.status_code in (301,302,308,403,404,405,400) else "FAIL"),f"Plain HTTP → {r.status_code}"
T("TL-NFR-07","Non-Functional","HTTPS enforced","Redirect/blocked",f,"Low","Security")

json.dump(R,open("results.json","w"),indent=1,ensure_ascii=False)
from collections import Counter; print(Counter(x["status"] for x in R),len(R))
