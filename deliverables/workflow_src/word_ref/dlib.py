import copy, re
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.table import _Cell
AR = re.compile(r"[؀-ۿ]")
RISK = "PolicyObject.PolicyLobList[0].PolicyRiskList[0]"
PLAN = RISK + ".PlanList[0]"
def tag(path, alias=None):
    alias = alias or re.sub(r"\[\d*\]", "", path).split(".")[-1]
    return f"<<{path}|{alias}>>"
def cov_tag(idx): return tag(f"{PLAN}.PolicyCoverageList[{idx}].SumInsured", "SumInsured")
def tc_text(tc): return "".join(t.text or "" for t in tc.iter(qn("w:t")))
def first_run_rpr(tc):
    for r in tc.iter(qn("w:r")):
        rp = r.find(qn("w:rPr"))
        if rp is not None: return copy.deepcopy(rp)
    return None
def _clean_rpr(rp, rtl):
    if rp is None: rp = OxmlElement("w:rPr")
    for e in rp.findall(qn("w:rtl")): rp.remove(e)
    if rtl:
        e = OxmlElement("w:rtl"); rp.append(e)
    return rp
def _mkrun(text, rpr, rtl=False):
    r = OxmlElement("w:r"); r.append(_clean_rpr(copy.deepcopy(rpr) if rpr is not None else None, rtl))
    parts = text.split("\t")
    for i, part in enumerate(parts):
        if i: r.append(OxmlElement("w:tab"))
        if part or len(parts) == 1:
            t = OxmlElement("w:t"); t.text = part; t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve"); r.append(t)
    return r
SCRIPT_SPLIT = re.compile(r"([\u0600-\u06FF][\u0600-\u06FF\s\.\-–/()ـ،:]*[\u0600-\u06FF)]|[\u0600-\u06FF])")
def set_bidi(p, on=True):
    ppr = p.find(qn("w:pPr"))
    if ppr is None: ppr = OxmlElement("w:pPr"); p.insert(0, ppr)
    for e in ppr.findall(qn("w:bidi")): ppr.remove(e)
    for e in ppr.findall(qn("w:jc")): ppr.remove(e)
    if on: ppr.append(OxmlElement("w:bidi"))
def set_tc(tc, *segments, rtl_last=False, bidi=None):
    """Replace the text of a table cell keeping the first paragraph and the formatting of its first run.
    segments: strings (joined by a tab); a segment with Arabic letters becomes a right-to-left run."""
    ps = tc.findall(qn("w:p"))
    for p in ps[1:]: tc.remove(p)
    p = ps[0]; rpr = first_run_rpr(tc)
    for ch in list(p):
        if ch.tag != qn("w:pPr"): p.remove(ch)
    ppr0 = p.find(qn("w:pPr"))
    if ppr0 is not None:
        for e in ppr0.findall(qn("w:numPr")): ppr0.remove(e)
    for i, seg in enumerate(segments):
        if i: 
            r = OxmlElement("w:r"); r.append(OxmlElement("w:tab")); p.append(r)
        for piece in re.split(r"(<<[^>]*>>)", seg):
            if not piece: continue
            if piece.startswith("<<"): p.append(_mkrun(piece, rpr, rtl=False)); continue
            for sub in SCRIPT_SPLIT.split(piece):
                if sub: p.append(_mkrun(sub, rpr, rtl=bool(AR.search(sub))))
    if bidi is not None: set_bidi(p, bidi)
def tcs(row): return row._tr.tc_lst
def label(row):
    t = tcs(row); return tc_text(t[0]).strip() if t else ""
def delete_row(row): row._tr.getparent().remove(row._tr)
def clone_row_after(row, new_after=None):
    new = copy.deepcopy(row._tr); (new_after or row._tr).addnext(new); return new
def collapse_row(tr, total_span, total_w):
    """Make a row a single cell spanning the table width (for <<Fragment...>> / <<EndFragment>> rows)."""
    tl = tr.findall(qn("w:tc"))
    for tc in tl[1:]: tr.remove(tc)
    tc = tl[0]; pr = tc.find(qn("w:tcPr"))
    gs = pr.find(qn("w:gridSpan"))
    if gs is None:
        gs = OxmlElement("w:gridSpan"); w = pr.find(qn("w:tcW")); (w.addnext(gs) if w is not None else pr.insert(0, gs))
    gs.set(qn("w:val"), str(total_span)); w = pr.find(qn("w:tcW"))
    if w is not None: w.set(qn("w:w"), str(total_w)); w.set(qn("w:type"), "dxa")
def grid_total(table):
    g = [int(x.get(qn("w:w"))) for x in table._tbl.tblGrid]; return len(g), sum(g)
def shape_cell(tc, span=None):
    pass
