import json,subprocess,urllib.request,time,sys,os
F="https://portal-gw.insuremo.com/platform/api-orchestration-test/v1/flow"
def tok(): return json.loads(subprocess.run(["imo","auth","prepare","--profile","portal:uponly","--json"],capture_output=True,text=True).stdout)["access_token"]
TOK=tok()
def call(m,p,b=None,raw=False):
    t=time.time()
    r=urllib.request.Request(F+p,data=json.dumps(b).encode() if b is not None else None,method=m,headers={"Authorization":"Bearer "+TOK,"Content-Type":"application/json"})
    try: resp=urllib.request.urlopen(r,timeout=240); st=resp.status; data=resp.read()
    except urllib.error.HTTPError as e: st=e.code; data=e.read()
    try: j=json.loads(data)
    except Exception: j={"_raw":data[:100]}
    return st,j,round(time.time()-t,1)
def show(label,res,keys=None,n=600):
    st,j,t=res; s=json.dumps(j if keys is None else {k:j.get(k) for k in keys})
    print(f"{label}: {st} {t}s {s[:n]}")
if __name__=="__main__":
    show("me",call("GET","/up/me"))
    show("worklist PROPOSAL",call("POST","/up/worklist",{"ChannelCode":"SOHAR","Type":"PROPOSAL","Status":"PENDING","PageSize":3}),n=1500)
    show("worklist CANCEL",call("POST","/up/worklist",{"ChannelCode":"SOHAR","Type":"CANCELLATION","PageSize":3}),n=1200)
    show("worklist MINE",call("POST","/up/worklist",{"ChannelCode":"SOHAR","Type":"MINE","Status":"ALL","PageSize":3}),n=800)
