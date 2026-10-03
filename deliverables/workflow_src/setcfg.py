#!/usr/bin/env python3
"""usage: setcfg.py Key Value [Key Value ...]  - changes UP_ApiConfig values (record-save) and prints the old values."""
import sys, json, subprocess
CFG = "1188575596"
def imo(a): return subprocess.run(["imo"] + a + ["--profile", "portal:uponly"], capture_output=True, text=True, cwd="/home/user/Tablet")
rows = json.loads(imo(["config", "datatable", "record-list", "--id", CFG, "--json"]).stdout)
rows = rows if isinstance(rows, list) else rows.get("ElementsInCurrentPage", rows.get("Records", []))
by = {r["Key"]: r for r in rows}
a = sys.argv[1:]
for k, v in zip(a[::2], a[1::2]):
    r = dict(by[k]); old = r["Value"]; r["Value"] = v
    json.dump(r, open("/tmp/cfgrow.json", "w"))
    out = imo(["config", "datatable", "record-save", "--file", "/tmp/cfgrow.json", "--confirm"])
    print(k, old, "->", v, "ok" if "@pk" in out.stdout else out.stdout[:150] + out.stderr[:150])
