#!/usr/bin/env python3
"""Rebuilds devdata/assets.json (server metadata saved by the last push of every asset) and devdata/tables.json (v1.1 data plus the rows written by workflow_setup*.py)
without calling the platform, so the developer guide can be regenerated offline."""
import json, glob, os
B = os.environ["B"]
assets = []
for kind in ("api", "function"):
    for f in sorted(glob.glob(f"{B}/ic/.metadata/icomposer/{kind}/*.metadata.json")):
        d = json.load(open(f))["profiles"].get("portal:uponly")
        if not d: continue
        x = d["data"]; name = x["Name"]
        src = f"{B}/ic/src/dev/Tenant/UP_PRODUCTS_API/{kind}/{name}/{name}.groovy"
        if not os.path.exists(src): continue
        assets.append(dict(kind=kind, name=name, path=x.get("Path"), method=x.get("RequestMethod"), status=x.get("Status"), version=x.get("Version"), md5=x.get("Md5Value"), id=x.get("Id"), group=x.get("GroupId"), module=x.get("ModuleId"), lines=open(src).read().count("\n") + 1))
json.dump(assets, open(f"{B}/devdata/assets.json", "w"), indent=1)
t = json.load(open(f"{B}/devdata/tables_v11.json"))
def rows(*tags):
    out = []
    for tag in tags:
        for f in sorted(glob.glob(f"{B}/tables/r_{tag}_*.json")): out += json.load(open(f))
    return out
t["UP_ApiConfig"]["records"] += rows("wfcfg", "wfcfg2", "wfcfg3", "wfcfg4")
t["UP_FieldRule"]["records"] += rows("wfrule", "wfrule2")
for name, tag, tid in (("UP_UserRole", "userrole", 1188710773), ("UP_NotifyTemplate", "notifytpl", 1188710781)):
    d = json.load(open(f"{B}/tables/def_{name}.json"))
    fields = [[n, f["DataType"], f.get("IsPrimaryKey")] for n, f in sorted(d["Fields"].items(), key=lambda kv: kv[1]["Sequence"])]
    fields.insert(0, ["Id", -4, None]) if False else None
    t[name] = {"id": tid, "fields": fields, "rows": 0, "group": 127, "records": rows(tag)}
# values changed afterwards with setcfg.py (final state of the MC tenant)
final = {"RoleEnforcement": "Y", "AllowSelfApproval": "Y"}
for r in t["UP_ApiConfig"]["records"]:
    if r["Key"] in final: r["Value"] = final[r["Key"]]
for n, d in t.items(): d["rows"] = len(d["records"])
json.dump(t, open(f"{B}/devdata/tables.json", "w"), indent=1)
print({k: v["rows"] for k, v in t.items()}); print(len(assets), "assets", [a["name"] for a in assets if a["status"] == 0])
