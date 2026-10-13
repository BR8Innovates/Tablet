import json,copy,subprocess,requests
from lib import *; from base import *
V={}
def mk(sub=1,plan=1,mode=2,term=1,mod=None):
    b=proposal(sub=sub,plan=plan,mode=mode,term=term)
    if sub==2: b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]["PolicyCoverageList"]=[c for c in b["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]["PolicyCoverageList"] if c["ProductElementCode"]!="TRV"]
    if mod: mod(b)
    return b
def cr(*a,**k): return call("proposal",mk(*a,**k))[1]
def iss(pn): return call("issue",{"ProposalNo":pn,"ProductCode":"TL001","ChannelCode":"SOHAR"})
def ld(**k): return call("load-policy",method="GET",params={"ChannelCode":"SOHAR",**k})
# PLAN-13
b=copy.deepcopy(__import__("json").loads(json.dumps(mk()))); 
GP={"ApplicationNo":"123","EffectiveDate":"2026-10-13","ExpiryDate":"2027-10-12T23:59:59","UserName":"Salman","ApplyDate":"2026-10-13","BranchCode":"001","DiscountAmount":0,"StaffId":"76","PolicyCustomerList":[{"CIFNumber":"45678","CustomerType":"1"}],"PolicyLobList":[{"PolicyRiskList":[{"Gender":"1","IdNo":"123456789","IdType":"1","Salutation":"1","InsuredName":"Mohamed","DateOfBirth":"1988-10-01","ResidentStatus":"1","Email":"Mohamed@gmail.com","MaritalStatus":"1","PostCode":"100345","Mobile":"9989374444","Address":"Oman","MonthSalaryIncome":"10000","ProductElementCode":"R00001"}],"ProductCode":"TL001"}],"ProductCode":"TL001","ProductSubcode":"3","PremiumModeCode":2,"ChannelCode":"SOHAR"}
s,j,t=call("get-plans",GP); V["plan13"]=(s,str(j)[:200] if not isinstance(j,dict) else {"keys":list(j)[:6],"planlist":len(j["PolicyLobList"][0]["PolicyRiskList"][0].get("PlanList",[])) if j.get("PolicyLobList") else None,"msg":j.get("message")})
# LOAD 02/03
V["load02"]=ld(proposalNo="PTL0019999999999")[:2]; V["load02"]=(V["load02"][0],str(V["load02"][1])[:200])
s,j,t=call("load-policy",method="GET",params={"ChannelCode":"SOHAR"}); V["load03"]=(s,str(j)[:200])
# REJ-02 reproduce
pn=cr()["ProposalNo"]; r1=call("proposal-reject",{"ProposalNo":pn,"ProposalRejectDesc":"checker rejected","ProductCode":"TL001","ChannelCode":"SOHAR"})
st1=ld(proposalNo=pn)[1]["ProposalStatus"]; r2=iss(pn); j2=r2[1]
V["rej02"]=dict(reject=(r1[0],r1[1]),status_after_reject=st1,issue_http=r2[0],policy=j2.get("PolicyNo"),proposal_status_after_issue=j2.get("ProposalStatus"),policy_status=j2.get("PolicyStatus"))
# REJ-05 no reason
pn=cr()["ProposalNo"]; r=call("proposal-reject",{"ProposalNo":pn,"ProductCode":"TL001","ChannelCode":"SOHAR"}); V["rej05"]=(r[0],r[1],ld(proposalNo=pn)[1]["ProposalStatus"])
# DOC 09/10/12
def raw(b): return requests.post(F+"doc_generation",headers={"Content-Type":"application/json","Authorization":"Bearer "+token()},json=b,timeout=90)
r=raw({"PolicyNo":"POTL00199999999","DocType":"Policy","ProductSubcode":"1","ChannelCode":"SOHAR","ProductCode":"TL001"}); open("v_d9.pdf","wb").write(r.content)
V["doc09"]=subprocess.run(["pdftotext","-layout","v_d9.pdf","-"],capture_output=True,text=True).stdout[:900]
pn=cr()["ProposalNo"]; r=raw({"PolicyNo":pn,"DocType":"Policy","ProductSubcode":"1","ChannelCode":"SOHAR","ProductCode":"TL001"}); open("v_d10.pdf","wb").write(r.content)
V["doc10"]=subprocess.run(["pdftotext","-layout","v_d10.pdf","-"],capture_output=True,text=True).stdout[:1200]
r=raw({"DocType":"Application","ProposalNo":pn,"ProductSubcode":"2","ChannelCode":"SOHAR","ProductCode":"TL001"}); open("v_d12.pdf","wb").write(r.content)
t=subprocess.run(["pdftotext","-layout","v_d12.pdf","-"],capture_output=True,text=True).stdout; V["doc12"]="Annual Family Travel" in t, ("Plan 1" in t), [l.strip() for l in t.splitlines() if "Death" in l][:2]
# CANCEL sequence on fresh policy
pn=cr(1,1,2)["ProposalNo"]; pol=iss(pn)[1]["PolicyNo"]
def cc(d,reason="Customer request"):
    r=call("cancel-check",{"PolicyNo":pol,"CancellationDate":d,"CancelReason":reason,"ChannelCode":"SOHAR"}); j=r[1]
    if r[0]!=200: return (r[0],str(j)[:160])
    return (r[0],j["RequestNo"],j["RequestStatus"],j["PremiumDetails"]["DaysSinceCommencement"],j["RefundDetails"]["CancellationType"],j["RefundDetails"]["RefundPremium"],j.get("CarrierName"))
V["can_seq"]=[("before-commence 2026-10-01",)+cc("2026-10-01"),("after-expiry 2028-01-01",)+cc("2028-01-01"),("same-day 2026-10-13",)+cc("2026-10-13"),("day7 2026-10-20",)+cc("2026-10-20"),("day92 2027-01-13",)+cc("2027-01-13"),("day0 again",)+cc("2026-10-13")]
# carrier name in other APIs
V["carrier_in_load"]=[k for k in ld(policyNo=pol)[1] if "arrier" in k]
# VAL-20 PO box 10 chars
for lbl,val in (("PO Box 123",1),("P.O.B 1234",1),("12345678901",1)):
    r=call("proposal",mk(1,1,2,mod=lambda b,v=lbl if val else None: b["PolicyLobList"][0]["PolicyRiskList"][0].update(PostCode=lbl)))
    V["pobox_"+lbl]=(r[0],r[1].get("ProposalNo") if r[0]==200 else str(r[1])[:120])
# SEC-01 benign specials
r=call("proposal",mk(1,1,2,mod=lambda b:b["PolicyLobList"][0]["PolicyRiskList"][0].update(InsuredName="O'Brien \"Test\" & Sons <b>")))
if r[0]==200:
    L=ld(proposalNo=r[1]["ProposalNo"])[1]; V["sec01"]=(200,L["PolicyLobList"][0]["PolicyRiskList"][0]["InsuredName"])
else: V["sec01"]=(r[0],str(r[1])[:150])
# LOAD-01 oracle
L=ld(proposalNo=pn)[1]; pay=L["PolicyPaymentInfoList"][0]; V["load01"]=(pay["LGCode"],pay["LCCode"],pay["DebitRefNo"],L["PolicyLobList"][0]["PolicyRiskList"][0]["BeneficiaryList"][0]["Share"])
# plain http
try:
    r=requests.get("http://uponlyuat-sandbox-in.insuremo.com/",timeout=15,allow_redirects=False); V["http"]=(r.status_code,r.headers.get("Location"))
except Exception as e: V["http"]=str(e)[:100]
json.dump(V,open("verify.json","w"),indent=1,default=str,ensure_ascii=False); print(json.dumps(V,indent=1,default=str,ensure_ascii=False))
