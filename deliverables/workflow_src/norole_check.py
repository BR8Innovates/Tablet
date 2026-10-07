import json,sys,subprocess
sys.path.insert(0,"."); import wf
exec(open("role_check.py").read().split("R = []")[0].split("sys.path.insert(0, \".\"); import wf")[1])
gp=json.load(open("samples/ref/HC001_1_P1/01_get-plans.json"))["request"]["body"]
try:
    set_roles([]); cfg(RoleEnforcement="Y")
    print("enforcement Y, no roles:", wf.call("POST","/up/get-plans",gp)[:1], wf.call("GET","/up/me")[1].get("Roles"))
    cfg(RoleEnforcement="N")
    for p,m,b in [("/up/get-plans","POST",gp),("/up/me","GET",None),("/up/worklist","POST",{"ChannelCode":"SOHAR","Type":"PROPOSAL","Status":"PENDING","PageSize":2}),("/up/dashboard","POST",{"ChannelCode":"SOHAR","Section":"SUMMARY"})]:
        r=wf.call(m,p,b); print("enforcement N, no roles:",p,r[0])
finally:
    set_roles(["MAKER","PROPOSAL_CHECKER","CANCELLATION_CHECKER"]); cfg(RoleEnforcement="N")
