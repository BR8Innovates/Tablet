import json,requests,copy,time,os
B="https://uponlyuat-sandbox-in.insuremo.com"
F=B+"/api/uponlyuat/api-orchestration/v1/flow/"
_tok={}
def token():
    if 't' not in _tok or time.time()-_tok['at']>6000:
        r=requests.post(B+"/cas/ebao/v2/json/tickets",headers={"Content-Type":"application/json","x-mo-user-source-id":"platform","x-mo-tenant-id":"uponlyuat"},json={"username":os.environ["UAT_USER"],"password":os.environ["UAT_PASS"]},timeout=40)
        _tok['t']=r.json()['access_token']; _tok['at']=time.time()
    return _tok['t']
def call(ep,body=None,method="POST",params=None,auth=True):
    h={"Content-Type":"application/json"}
    if auth: h["Authorization"]="Bearer "+(token() if auth is True else auth)
    t=time.time()
    try:
        r=requests.request(method,F+ep,headers=h,json=body if method=="POST" else None,params=params,timeout=90)
        try: j=r.json()
        except Exception: j=r.text[:500]
        return r.status_code,j,round(time.time()-t,2)
    except Exception as e:
        return 0,str(e),round(time.time()-t,2)

def summ(j):
    if not isinstance(j,dict): return {"raw":str(j)[:300]}
    o={}
    for k in ("ProposalNo","PolicyNo","ProposalStatus","PolicyStatus","DuePremium","GrossPremium","Commission","AutoUwResultCode","IsPremiumCalcSuccess","PremiumModeCode","ProductSubcode","PolicyTerm","SumInsured","ExpiryDate","EffectiveDate","status","message","code","error","errors","Message","msg","err_code","err_msg"):
        if k in j: o[k]=j[k]
    try:
        o["Lob.DuePremium"]=j["PolicyLobList"][0].get("DuePremium"); o["Lob.Commission"]=j["PolicyLobList"][0].get("Commission")
    except Exception: pass
    if not o: o={k:str(v)[:150] for k,v in list(j.items())[:8]}
    return o
