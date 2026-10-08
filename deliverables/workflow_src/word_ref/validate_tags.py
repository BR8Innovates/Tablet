import docx, re, glob, os, sys, json
sys.path.insert(0, "."); from refdata import OBJ
from docx.oxml.ns import qn
def texts(path):
    d = docx.Document(path); out = []
    for p in d.element.iter(qn("w:p")):
        out.append("".join(t.text or "" for t in p.iter(qn("w:t"))))
    return "\n".join(out)
def resolve(obj, path):
    cur = obj
    for part in path.split("."):
        m = re.match(r"^(\w+)(?:\[(\d*)\])?$", part)
        if not m: return None, f"bad segment {part}"
        k, i = m.group(1), m.group(2)
        if not isinstance(cur, dict) or k not in cur: return None, f"missing {k}"
        cur = cur[k]
        if i not in (None, ""):
            if not isinstance(cur, list) or int(i) >= len(cur): return None, f"index {k}[{i}] out of range"
            cur = cur[int(i)]
    return cur, None
tot = bad = 0
for f in sorted(glob.glob(sys.argv[1] + "/*.docx")):
    code = os.path.basename(f).split("_")[1]; obj = {"PolicyObject": OBJ[code]}
    tx = texts(f); tags = re.findall(r"<<([^<>|]+)\|([^<>]*)>>", tx); issues = []
    ncov = len(obj["PolicyObject"]["PolicyLobList"][0]["PolicyRiskList"][0]["PlanList"][0]["PolicyCoverageList"])
    for path, alias in tags:
        tot += 1
        if path.startswith("BeneficiaryList[]"):
            v, err = resolve(obj["PolicyObject"]["PolicyLobList"][0]["PolicyRiskList"][0], path.replace("BeneficiaryList[]", "BeneficiaryList[0]"))
        elif path.startswith("PolicyObject"): v, err = resolve(obj, path)
        else: v, err = None, "unknown root"
        if err or v in (None, "", {}, []): issues.append((path, err or "empty")); bad += 1
    print(("OK   " if not issues else "FAIL ") + os.path.basename(f), "tags", len(tags), issues[:3])
print("total tags", tot, "unresolved", bad)
