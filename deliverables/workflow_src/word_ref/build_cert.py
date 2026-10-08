import sys, re, copy, docx
sys.path.insert(0, "."); from dlib import *; from refdata import *
from docx.oxml.ns import qn
def replace_text(root, old, new):
    n = 0
    for p in root.iter(qn("w:p")):
        ts = [t for t in p.iter(qn("w:t"))]
        joined = "".join(t.text or "" for t in ts)
        if old in joined:
            new_joined = joined.replace(old, new); ts[0].text = new_joined; ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            for t in ts[1:]: t.text = ""
            n += 1
    return n
COMMON = [("commencement date", "EffectiveDate"), ("certificate no", None), ]
def sv_tag(field): return tag(f"{RISK}.{field}", field)
def build_cert(code, sub, out):
    pinfo = PRODUCT[code]; d = docx.Document(CERT_DIR + pinfo["cert"]); t = d.tables[0]
    cov = COV[(code, sub)]; idx = {c: i for i, c in enumerate(cov)}; show = SHOW.get((code, sub))
    rows = list(t.rows); ncol, wtot = grid_total(t)
    lp = code == "LP001"
    # ---- title for Life Protect (client base is Term Life)
    if lp:
        for old, new in (("Term Life Insurance", "Life Protect"), ("TERM LIFE INSURANCE", "LIFE PROTECT"), ("تأمين على الحياة لأجل محدد", "خطة حماية الحياة")):
            replace_text(d.element, old, new)
    mode_ar = tag("PolicyObject.PremiumModeCode_CodeDesc", "PremiumModeCode_CodeDesc")
    benef_hdr = None
    state = "top"
    for r in rows:
        lab = label(r); low = lab.lower(); T = tcs(r)
        if low.startswith("commencement date"): set_tc(T[1], tag("PolicyObject.EffectiveDate", "EffectiveDate"))
        elif low.startswith("certificate no"): set_tc(T[1], tag("PolicyObject.PolicyNo", "PolicyNo"))
        elif low.startswith("name of insured") or low.startswith("name of policy holder"): set_tc(T[1], sv_tag("InsuredName"))
        elif low == "gender": set_tc(T[1], sv_tag("Gender_CodeDesc"))
        elif low.startswith("date of birth"): set_tc(T[1], sv_tag("DateOfBirth"))
        elif low == "nationality": set_tc(T[1], sv_tag("ResidentStatus_CodeDesc"))
        elif low.startswith("correspondence"): set_tc(T[1], sv_tag("Address"))
        elif low.startswith("mobile"): set_tc(T[1], sv_tag("Mobile"))
        elif low.startswith("email"): set_tc(T[1], sv_tag("Email"))
        elif low.startswith("total premium"):
            set_tc(T[1], "OMR " + sv_tag("DuePremium")); set_tc(T[2], "ريال عُماني " + sv_tag("DuePremium"))
        elif low.startswith("payment frequency"): set_tc(T[1], mode_ar); set_tc(T[2], mode_ar)
        elif low.startswith("period of cover"):
            if lp: set_tc(T[1], tag("PolicyObject.PolicyTerm", "PolicyTerm") + " Month(s) from the Policy Commencement Date"); set_tc(T[2], "شهر / أشهر من تاريخ بدء سريان الوثيقة " + tag("PolicyObject.PolicyTerm", "PolicyTerm"))
            else: set_tc(T[1], tag("PolicyObject.PolicyTerm", "PolicyTerm") + " Year(s) from the Policy Commencement Date"); set_tc(T[2], "سنة / سنوات من تاريخ بدء سريان الوثيقة " + tag("PolicyObject.PolicyTerm", "PolicyTerm"))
        elif low.startswith("this certificate of insurance") and lp:
            set_tc(T[0], "Policy Detailed Terms and Conditions are available on the website of Sohar International Bank https://www.soharinternational.com/.")
            set_tc(T[1], "تخضع هذه الشهادة لأحكام وشروط بوليصة حماية الحياة")
        elif low.startswith("benefits") and not show and low == "benefits":   # FC / CI / HCB single "Benefits" row
            en = tc_text(T[1]); ar = tc_text(T[2]); pn = tag(f"{PLAN}.PlanName", "PlanName")
            if code == "CI001":
                cnt = CI_COUNT[sub]; en = re.sub(r"PLAN-\d+ \(\d+ CI\)", f"{pn} ({cnt})", en); ar = re.sub(r"PLAN-\d+ \(\d+ CI\)", f"{pn} ({cnt})", ar)
            elif code == "FP001": en = re.sub(r"PLAN-\d+", pn, en); ar = re.sub(r"PLAN-\d+", pn, ar)
            set_tc(T[1], en); set_tc(T[2], ar)
        elif low == "sum insured" and not show: set_tc(T[1], "OMR " + cov_tag(0))
        elif low == "plan opted": 
            v = tag(f"{PLAN}.PlanName", "PlanName") + " - " + sv_tag("DuePremium"); set_tc(T[1], v); set_tc(T[2], v)
    # ---- coverage table (PA / TL / LP / DH)
    if show:
        rows = list(t.rows)
        hi = next(i for i, r in enumerate(rows) if label(r).lower().startswith("benefit") and not label(r).lower().startswith("benefits and"))
        j = hi + 1; cov_rows = []
        while j < len(rows) and not label(rows[j]).lower().startswith(("beneficiary", "total premium")): cov_rows.append(rows[j]); j += 1
        by_len = {}
        for r in cov_rows: by_len.setdefault(len(tcs(r)), r)
        proto = by_len.get(2) or by_len.get(3) or by_len.get(4); kind = len(tcs(proto))
        admin = next((r for r in cov_rows if label(r).lower().startswith("administration")), None)
        proto_xml = copy.deepcopy(proto._tr); admin_xml = copy.deepcopy(admin._tr) if admin is not None else None
        for r in cov_rows: delete_row(r)
        anchor = rows[hi]._tr
        def si_txt(c):
            tg = cov_tag(idx[c])
            if code == "DH001":
                return {"DTH": "OMR " + tg, "AME": "Actuals up to a maximum of OMR " + tg + " in a policy year", "RHE": "Actuals up to OMR " + tg,
                        "REP": "OMR " + tg + " (including the one way economy air fare for the person accompanying mortal remains)"}[c]
            return "Included / مشمول" if c == "TRV" else tg
        for c in show:
            if c not in idx: continue
            en, ar = BT[(code, c)]; new = copy.deepcopy(proto_xml); anchor.addnext(new); anchor = new
            T = new.findall(qn("w:tc"))
            if kind == 4: set_tc(T[0], en); set_tc(T[2], ar); set_tc(T[3], si_txt(c))
            elif kind == 3: set_tc(T[0], en); set_tc(T[1], ar); set_tc(T[2], si_txt(c))
            else: set_tc(T[0], en, ar); set_tc(T[1], si_txt(c))
            if c == "RHE" and admin_xml is not None:
                a = copy.deepcopy(admin_xml); anchor.addnext(a); anchor = a; TT = a.findall(qn("w:tc")); set_tc(TT[-1], "Actuals up to OMR 500")
    # ---- beneficiary block
    if pinfo["cert_benef"] or lp:
        rows = list(t.rows)
        bi = next((i for i, r in enumerate(rows) if label(r).lower().startswith("beneficiary")), None)
        if bi is not None:
            sample = rows[bi + 2]; T = tcs(sample)
            set_tc(T[0], "<<BeneficiaryList[].BeneficaryName|BeneficaryName>>"); set_tc(T[1], "<<BeneficiaryList[].Share|Share>>"); set_tc(T[2], "<<BeneficiaryList[].RelationshipCode_CodeDesc|RelationshipCode_CodeDesc>>")
            a = copy.deepcopy(sample._tr); b = copy.deepcopy(sample._tr)
            sample._tr.addprevious(a); sample._tr.addnext(b)
            for el, txt in ((a, "<<Fragment_BeneficiaryList[]|BeneficiaryList[]>>"), (b, "<<EndFragment>>")):
                collapse_row(el, ncol, wtot); set_tc(el.findall(qn("w:tc"))[0], txt)
    for h in list(d.element.iter(qn('w:highlight'))): h.getparent().remove(h)
    d.save(out)
if __name__ == "__main__":
    build_cert(sys.argv[1], sys.argv[2], sys.argv[3])
