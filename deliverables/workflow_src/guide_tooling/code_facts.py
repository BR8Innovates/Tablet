"""Facts extracted from the real source files, tables and scripts, so that the developer guide cannot drift from the code."""
import json, os, re, glob
B = os.environ["B"]; SRC = B + "/ic/src/dev/Tenant/UP_PRODUCTS_API"
tables = json.load(open(B + "/devdata/tables.json")); assets = json.load(open(B + "/devdata/assets.json"))
def read(p): return open(p, encoding="utf-8").read()
def files(kind): return sorted(glob.glob(f"{SRC}/{kind}/*/*.groovy"))
def header(text):
    m = re.match(r"\s*/\*\*(.*?)\*/", text, re.S)
    return re.sub(r"\s*\n\s*\*\s?", " ", m.group(1)).strip() if m else ""
METH = re.compile(r"^(?:(?:static|public|private)\s+)?([A-Za-z_][\w<>\[\], .?]*?)\s+(\w+)\(([^)]*)\)\s*\{\s*$")
def methods(text):
    lines = text.split("\n"); out = []
    for i, ln in enumerate(lines):
        m = METH.match(ln)
        if not m or ln.startswith((" ", "\t")) or m.group(2) in ("if", "for", "while", "switch", "catch", "try"): continue
        if m.group(1).strip() in ("return", "else", "new"): continue
        doc = ""
        j = i - 1
        while j >= 0 and lines[j].strip() == "": j -= 1
        if j >= 0 and lines[j].strip().endswith("*/"):
            k = j
            while k >= 0 and "/**" not in lines[k]: k -= 1
            doc = re.sub(r"\s*\*\s?", " ", " ".join(l.strip() for l in lines[k:j + 1]).replace("/**", "").replace("*/", "")).strip()
        elif j >= 0 and lines[j].strip().startswith("//"):
            doc = lines[j].strip().lstrip("/ ")
        out.append(dict(ret=m.group(1).strip(), name=m.group(2), params=m.group(3).strip(), doc=doc, line=i + 1))
    return out
def deps(text): return sorted(set(re.findall(r'getCommonService\("(\w+)"\)', text)))
def sdks(text): return sorted(set(m.split(".")[-1] for m in re.findall(r'getSDK\("([\w.]+)"\)', text)))
def tbls(text): return sorted(set(re.findall(r'(?:getRecords|filterRecords)\("([\w]+)"', text)))
def cfgkeys(text): return sorted(set(re.findall(r'cfg(?:Value)?\((?:[a-z]+,\s*)?"(\w+)"', text) + re.findall(r'configText\("(\w+)"', text)))
def info(kind):
    out = []
    for f in files(kind):
        n = os.path.basename(f)[:-7]; t = read(f); meta = next((a for a in assets if a["name"] == n and a["kind"] == kind), {})
        out.append(dict(name=n, kind=kind, file=os.path.relpath(f, B + "/ic"), lines=t.count("\n") + 1, header=header(t), methods=methods(t) if kind == "function" else [], deps=deps(t), sdks=sdks(t), tables=tbls(t), keys=cfgkeys(t),
                        path=meta.get("path"), method={1: "GET", 2: "POST"}.get(meta.get("method")), status=meta.get("status"), version=meta.get("version"), md5=meta.get("md5")))
    return out
def key_usage():
    use = {}
    allsrc = {os.path.basename(f)[:-7]: read(f) for f in files("api") + files("function")}
    for r in tables["UP_ApiConfig"]["records"]:
        k = r["Key"]; use[k] = sorted(n for n, t in allsrc.items() if re.search(r'"%s"' % re.escape(k), t))
    return use
def tool_docs():
    out = []
    for f in sorted(glob.glob(B + "/*.py")):
        t = read(f); m = re.match(r'(?:#!.*\n)?\s*"""(.*?)"""', t, re.S)
        if m: out.append((os.path.basename(f), re.sub(r"\s+", " ", m.group(1)).strip()[:230]))
    return out
