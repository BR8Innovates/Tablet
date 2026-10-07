#!/usr/bin/env python3
"""Output Service HTML templates (bilingual) following the Life Protect application form and certificate PDFs."""
import base64, os, re, glob, json, docx
from docx.table import Table
B = os.environ["B"]; S = os.path.dirname(B); A = B + "/assets"; OUT = B + "/tpl2"; os.makedirs(OUT, exist_ok=True)
FORMS = S + "/lpforms/AppFormsAndCertificateFormats"
def b64(path, mime): return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()
LOGO = b64(A + "/logo_cert.png", "image/png"); BANNER = b64(A + "/footer_banner.png", "image/png"); STAMP = b64(A + "/stamp.png", "image/png")
AR = re.compile(r"[؀-ۿ]")
CSS_APP = """
@page{size:A4;margin:7mm 12mm 12mm 12mm;@bottom-right{content:"Page " counter(page) " of " counter(pages);font:11pt Arial,sans-serif}}
@page full{size:A4;margin:0 0 12mm 0;@bottom-right{content:"Page " counter(page) " of " counter(pages);font:11pt Arial,sans-serif;margin-right:12mm}}
*{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}body{margin:0;font-family:"Times New Roman",Times,serif;font-size:9pt;color:#000}
.hd{width:100%;border-collapse:collapse;margin-bottom:5mm}.hd td{border:0;padding:0;vertical-align:top}
.ttl{display:inline-block;border:1px solid #ccc;padding:2mm 3mm;font:bold 12pt "Segoe UI",Arial,sans-serif;color:#1f6a99;line-height:1.35;min-width:70mm}
.logo{text-align:right}.logo img{width:66mm}
table.g{width:100%;border-collapse:collapse;table-layout:fixed}
table.g td{border:1px solid #000;padding:1.1mm 1.8mm;vertical-align:top;font-size:9pt;line-height:1.25}
table.g td.c{text-align:center}.ar{direction:rtl;text-align:right;font:9.5pt "Segoe UI",Tahoma,Arial,sans-serif}
td.ar{direction:rtl;text-align:right;font:9.5pt "Segoe UI",Tahoma,Arial,sans-serif}
.bh td{background:#2f7ca3;color:#fff;font-weight:bold}.bh td.ar{font-weight:bold}
.h3{font:bold 10pt "Times New Roman",serif;margin:2mm 0 1mm}
.b{font-weight:bold}.gap{height:1.5mm}.g tr.addr td{height:9mm}
.foot img{width:100%;display:block;margin-top:0}
.pg{page:full;page-break-before:always;height:282mm;overflow:hidden;text-align:center}.pg img{height:282mm;max-width:100%}
.tp{page-break-before:always;font:8.5pt Arial,sans-serif}.tp td{vertical-align:top;border:1px solid #000;padding:1.6mm 2mm}
.tp td.ar{font-size:9pt}
"""
CSS_CERT = """
@page{size:A4;margin:10mm 12mm 12mm 12mm}
*{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}body{margin:0;font-family:Arial,Helvetica,sans-serif;font-size:9pt;color:#000}.b{font-weight:bold}
.hd{width:100%;border-collapse:collapse;margin-bottom:3mm}.hd td{border:0;padding:0;vertical-align:top}
.t1{font:bold 17pt "Times New Roman",Times,serif;line-height:1.25;padding-top:4mm}.t2{font:bold 11pt "Segoe UI",Arial,sans-serif;direction:rtl;text-align:right;margin-top:2mm}
.logo{text-align:right}.logo img{width:66mm}
table.g{width:100%;border-collapse:collapse;table-layout:fixed}
table.g td{border:1px solid #000;padding:1.3mm 1.6mm;vertical-align:top;font-size:9pt;height:5.8mm}
td.c{text-align:center}td.ar{direction:rtl;text-align:right;font:9pt "Segoe UI",Tahoma,Arial,sans-serif}
td.arb{direction:rtl;text-align:right;font:bold 10pt "Segoe UI",Tahoma,Arial,sans-serif}
.tm{font-family:"Times New Roman",Times,serif}.bar td{background:#000;color:#fff;font-weight:bold}
.sp{height:2.5mm}.sig{width:100%;border-collapse:collapse;margin-top:4mm}.sig td{border:0;font-size:9pt;vertical-align:top}
.sig .ar{font:bold 9pt "Segoe UI",Arial,sans-serif;text-align:center;direction:rtl}
"""
# ----------------------------------------------------------------------------------------- product specs
PRODUCTS = {
 "UPPA001": dict(en="Personal Accident Insurance", ar="شهادة التأمين – التأمين على الحوادث الشخصية", app="Personal Accident Insurance 06878.docx", cert_tc=("Personal Accident Insurance Policy", "تخضع هذه الشهادة لأحكام وشروط وثيقة التأمين على الحوادث الشخصية"), items=True, benef=True, holder=False, insured="Insured Person"),
 "TL001":   dict(en="Term Life Insurance", ar="شهادة التأمين – تأمين على الحياة لأجل محدد", app="Term Life Insurance 06878.docx", cert_tc=("Term Life Insurance Policy", "تخضع هذه الشهادة لأحكام وشروط وثيقة التأمين على الحياة لأجل محدد"), items=True, benef=True, holder=True, insured="Policyholder"),
 "FP001":   dict(en="Female Protection Plan Insurance", ar="خطة حماية المرأة – شهادة التأمين", app="Female Protecion Plan Application Form.docx", cert_tc=("Female Protection Plan Insurance Policy", "تخضع هذه الشهادة لأحكام وشروط وثيقة تأمين خطة حماية المرأة"), items=False, benef=False, holder=False, insured="Insured Person",
                 plan_en="Female Cancer Cover – {plan} / Second Medical Opinion", plan_ar="{plan} - سرطانات الإناث / الاستشارة الطبية الثانية", si_label=("Sum Insured", "مبلغ التغطية")),
 "HC001":   dict(en="Hospital Cash Insurance", ar="شهادة التأمين – تأمين منفعة الاستشفاء النقدي", app="Hospital Cash Benefit Application Form.docx", cert_tc=("Hospital Cash Insurance Policy", "تخضع هذه الشهادة لأحكام وشروط وثيقة الاستشفاء النقدي"), items=False, benef=False, holder=True, insured="Insured Person",
                 plan_en="Hospital Cash Benefit due to any cause per day limits subject to maximum of 90 days in a policy year", plan_ar="منفعة الاستشفاء النقدية - حدود يومية بحد أقصى 90 يومًا في السنة المتعلقة بالوثيقة", si_label=("Plan Opted", "البرنامج المختار")),
 "CI001":   dict(en="Critical Illness Insurance", ar="شهادة التأمين – التأمين على الأمراض الحرجة", app="Critical Illness Insurance Application Form 06878.docx", cert_tc=("Critical Illness Insurance Policy", "تخضع هذه الشهادة لشروط وأحكام وثيقة التأمين على الأمراض الحرجة"), items=False, benef=True, holder=False, insured="Insured Person",
                 plan_en="Critical Illness Cover – {plan} / Second Medical Opinion", plan_ar="{plan} – تغطية الأمراض الحرجة / الاستشارة الطبية الثانية", si_label=("Sum Insured", "البرنامج المختار")),
 "DH001":   dict(en="Domestic Helper Insurance", ar="شهادة التأمين - تأمين عامل المنزل", app="Domestic Helper Insurance Application Form.docx", cert_tc=("Domestic Helper Insurance Policy", "تخضع هذه الشهادة لشروط وأحكام وثيقة تأمين عامل المنزل"), items=True, benef=False, holder=True, insured="Domestic Helper"),
 "LP001":   dict(en="Life Protect", ar="", app=None, cert_tc=("", "تخضع هذه الشهادة لأحكام وشروط بوليصة التأمين على الحياة لأجل محدد"), items=True, benef=True, holder=False, insured="Policy Holder",
                 tc_en="Policy Detailed Terms and Conditions are available on the website of Sohar International Bank https://www.soharinternational.com/."),
}
# ------------------------------------------------------------------------------------------ application
def head(title1, title2, css):
    return f'<table class="hd"><tr><td><div class="ttl">{title1}<br>{title2}</div></td><td class="logo"><img src="{LOGO}"></td></tr></table>'
def row3(en, val, ar, extra=""):
    return f'<tr><td>{en}</td><td class="c">{val}</td><td class="ar">{ar}</td></tr>'
PERIOD_LP_EN = ("Period of Coverage: 30 days from the Premium Due Date /<br>Grace Period: A grace period of thirty (30) days will be granted for the payment of each Premium falling due after the first Premium, "
                "during which time the policy shall be continued in force, unless the policy has been cancelled in accordance with 'Cancellation'. The Insured Person shall be liable to the Company for the payment of the "
                "Premium for the period the policy continues in force. If loss occurs within the Grace Period, any Premium then due and unpaid will be deducted on settlement.")
PERIOD_LP_AR = ("فترة التغطية: 30 يومًا من تاريخ استحقاق القسط / 1 سنة<br>فترة الإمهال: تُمنح فترة سماح قدرها ثلاثون (30) يوم لدفع كل قسط يستحق بعد القسط الأول، وتظل الوثيقة سارية طوال تلك الفترة، "
                "ما لم يتم إلغاؤها وفقًا لبند \"الإلغاء\". يلتزم المؤمن عليه بأن يدفع إلى الشركة القسط المستحق عن الفترة التي تظل فيها الوثيقة سارية. وفي حالة وقوع خسارة خلال فترة الإمهال، يخصم أي قسط مستحق وغير مدفوع حينئذ عند التسوية.")
def docx_terms(fn):
    """Bilingual (english, arabic) paragraphs from the long text rows of the application docx."""
    d = docx.Document(f"{FORMS}/ApplicationFormsForNewSystem/{fn}"); out = []; seen = set()
    for t in d.tables:
        for r in t.rows:
            cells = []; tcs = []
            for c in r.cells:
                if c._tc in tcs: continue
                tcs.append(c._tc); cells.append(c.text.strip())
            en = max((c for c in cells if not AR.search(c)), key=len, default=""); ar = max((c for c in cells if AR.search(c)), key=len, default="")
            if len(en) > 70 and len(ar) > 40 and en not in seen and "Sum Insured Plan Opted" not in en and not en.startswith("I would like to apply") and not en.lower().startswith("period of coverage"):
                seen.add(en); out.append((en.replace("8096", "80%"), ar.replace("\n", " ")))
    return out
def application(code, p):
    monthly = code == "LP001"
    title2 = "Application Form" + (" - {{ModeEn}}" if code == "LP001" else "")
    h = [f"<!doctype html><html><head><meta charset='utf-8'><title>{p['en']} Application</title><style>{CSS_APP}</style></head><body>", head(p["en"], title2, CSS_APP)]
    insured = p["insured"]
    h.append('<table class="g"><colgroup><col style="width:33%"><col style="width:34%"><col style="width:33%"></colgroup>')
    cust_label = f"Customer Name<br>({insured})"
    rows = [("Application No", "{{ApplicationNo}}", "رقم نموذج الطلب"), ("Application Date", "{{ApplicationDate}}", "تاريخ نموذج الطلب"),
            (cust_label, "{{Salutation}} {{InsuredName}}", "اسم العميل / (المؤمن عليه)"), ("Date Of Birth", "{{DateOfBirth}}", "تاريخ الميلاد"),
            ("Resident Status", "{{ResidentStatus}}", "وضع المقيم"), ("Passport / ID Number", "{{IdNo}}", "رقم جواز السفر / الهوية"),
            ("Address", "{{Address}}", "العنوان"), ("Country", "{{ResidentStatus}}", "البلد"), ("PO Box", "{{PoBox}}", "ص.ب"),
            ("Monthly Income", "{{MonthlyIncome}}", "الدخل الشهري"), ("Marital Status", "{{MaritalStatus}}", "الحالة الاجتماعية"),
            ("Mobile Phone Number", "{{Mobile}}", "رقم الهاتف المتحرك"), ("Email Address", "{{Email}}", "البريد الإلكتروني")]
    h += [row3(*r) for r in rows]; h.append("</table>")
    if p["benef"]:
        h.append('<div class="h3">Beneficiary Details</div><table class="g"><colgroup><col style="width:41%"><col style="width:29%"><col style="width:30%"></colgroup>')
        h.append('<tr class="bh"><td>Name <span style="float:right" class="ar">الاسم</span></td><td>Share % (total to equal 100%)<br><span class="ar" style="display:block">نسبة المساهمة (بمجموع يساوي 100%)</span></td><td>Relationship to the Insured Person<br><span class="ar" style="display:block">صلته بالشخص المصاب</span></td></tr>')
        h.append('{{#each Beneficiaries}}<tr><td class="b">{{Name}}</td><td class="c">{{Share}}</td><td class="c">{{Relationship}}</td></tr>{{/each}}</table>')
    h.append('<div class="gap"></div><table class="g"><colgroup><col style="width:52%"><col style="width:48%"></colgroup><tr><td>{{ProductName}}</td><td>{{PlanName}}</td></tr></table><div class="gap"></div>')
    h.append('<table class="g"><colgroup><col style="width:52%"><col style="width:22%"><col style="width:26%"></colgroup><tr><td class="b">Benefit Name</td><td class="b">Sum Insured (OMR)</td><td class="ar b" style="font-size:10pt">مبلغ التغطية (بالريال العُماني)</td></tr>')
    h.append('{{#each Coverages}}<tr><td>{{Description}}</td><td>{{SumInsured}}</td><td class="ar">{{DescriptionAr}}</td></tr>{{/each}}</table>')
    pay_ar = "أرغب في التقدم بطلب ودفع القسط الفردي/الشهري/القسط للمبلغ لإجمالي الموضح أدناه لشراء هذا النوع من التامين" if monthly else "أرغب في تقديم نموذج الطلب وسداد القسط الواحد / الشهري / السنوي للمبلغ الإجمالي المذكور أدناه لشراء هذا البرنامج"
    h.append('<table class="g"><colgroup><col style="width:56%"><col style="width:44%"></colgroup><tr><td><div class="b">Payment Details</div><div style="margin-top:3mm">I would like to apply and pay the <b>{{FrequencyEn}}</b> for the total amount shown below for the purchase of this plan</div></td>'
             f'<td class="ar"><div class="b" style="font-size:10pt">تفاصيل الدفع</div><div style="margin-top:2mm">{pay_ar}</div></td></tr></table>')
    h.append('<table class="g"><colgroup><col style="width:34%"><col style="width:23%"><col style="width:43%"></colgroup><tr><td>Premium (OMR)</td><td class="c">{{Premium}}</td><td class="ar">القسط (ريال عُماني)</td></tr></table>')
    if monthly:
        per_en, per_ar = PERIOD_LP_EN, PERIOD_LP_AR
    else:
        per_en = "Period of Coverage: {{PeriodEn}}"; per_ar = "فترة التغطية: {{PeriodAr}}"
    h.append(f'<table class="g"><colgroup><col style="width:56%"><col style="width:44%"></colgroup><tr><td>{per_en}</td><td class="ar" style="font-size:8.5pt">{per_ar}</td></tr></table>')
    h.append('<table class="g"><colgroup><col style="width:34%"><col style="width:23%"><col style="width:43%"></colgroup><tr><td>Customer Signature</td><td>&nbsp;</td><td class="ar">توقيع العميل</td></tr></table>')
    h.append(f'<div class="foot"><img src="{BANNER}"></div>')
    if code == "LP001":
        h.append(f'<div class="pg"><img src="{b64(A + "/lp_page2.jpg", "image/jpeg")}"></div><div class="pg"><img src="{b64(A + "/lp_page3s.jpg", "image/jpeg")}"></div>')
    else:
        terms = docx_terms(p["app"])
        h.append('<div class="tp"><div class="h3" style="font-family:Arial">Declarations and Terms / الإقرارات والشروط</div><table class="g"><colgroup><col style="width:50%"><col style="width:50%"></colgroup>')
        for en, ar in terms:
            h.append(f'<tr><td>{en}</td><td class="ar">{ar}</td></tr>')
        h.append('</table><div style="margin-top:8mm">Customer Signature / توقيع العميل : ______________________ &nbsp;&nbsp; Date / التاريخ : ____________</div>')
        h.append(f'<div class="foot" style="margin-top:6mm"><img src="{BANNER}"></div></div>')
    h.append("</body></html>")
    return "\n".join(h)
# ------------------------------------------------------------------------------------------ certificate
def certificate(code, p):
    h = [f"<!doctype html><html><head><meta charset='utf-8'><title>{p['en']} Certificate</title><style>{CSS_CERT}</style></head><body>"]
    h.append(f'<table class="hd"><tr><td><div class="t1">Certificate Of Insurance<br>{p["en"]}</div>' + (f'<div class="t2">{p["ar"]}</div>' if p["ar"] else "") + f'</td><td class="logo"><img src="{LOGO}"></td></tr></table>')
    col = '<colgroup><col style="width:29%"><col style="width:45%"><col style="width:26%"></colgroup>'
    r3 = lambda a, v, ar, vh="": f'<tr><td>{a}</td><td class="c">{v}</td><td class="ar">{ar}</td></tr>'
    h.append('<table class="g">' + col)
    h.append(r3("Commencement Date", "{{CommencementDate}}", "تاريخ بدء السريان")); h.append(r3("Certificate No", "{{PolicyNo}}", "رقم الشهادة"))
    h.append(r3("Name of Insured Person", "{{Salutation}} {{InsuredName}}", "اسم المؤمن عليه")); h.append(r3("Gender", "{{Gender}}", "الجنس"))
    h.append(r3("Date of Birth", "{{DateOfBirth}}", "تاريخ الميلاد")); h.append(r3("Nationality", "{{ResidentStatus}}", "الجنسية"))
    if p["holder"]: h.append(r3("Name of Policy Holder", "{{PolicyHolderName}}", "اسم حامل الوثيقة"))
    h.append('<tr><td style="height:11mm">Correspondence Address</td><td class="c">{{Address}}</td><td class="ar">عنوان المراسلات</td></tr>')
    h.append(r3("Mobile Phone number", "{{Mobile}}", "رقم الهاتف النقال"))
    h.append('<tr><td style="height:8mm">Email address</td><td class="c">{{Email}}</td><td class="ar">عنوان البريد الإلكتروني</td></tr></table><div class="sp"></div>')
    if p["items"]:
        h.append('<table class="g"><colgroup><col style="width:40%"><col style="width:20%"><col style="width:40%"></colgroup><tr><td class="tm" style="text-align:center;font-weight:bold" colspan="2">{{ProductName}}</td><td class="tm b">{{PlanName}}</td></tr></table>')
        h.append('<table class="g"><colgroup><col style="width:46%"><col style="width:20%"><col style="width:34%"></colgroup><tr><td class="tm b">Benefit</td><td class="tm b">Sum Insured (OMR)</td><td class="arb">مبلغ التغطية (بالريال العُماني)</td></tr>')
        h.append('{{#each Coverages}}<tr><td class="tm">{{Description}}</td><td class="tm">{{SumInsured}}</td><td class="ar">{{DescriptionAr}}</td></tr>{{/each}}</table>')
    else:
        pen = p["plan_en"].replace("{plan}", "{{PlanLabel}}"); par = p["plan_ar"].replace("{plan}", "{{PlanLabel}}")
        h.append('<table class="g">' + col)
        h.append(f'<tr><td>Benefits</td><td class="c">{pen}<div class="ar" style="text-align:center;margin-top:1mm">{par}</div></td><td class="arb">المنافع</td></tr>')
        sil, sia = p["si_label"]
        val = "{{PlanLabel}} - {{Premium}}" if code == "HC001" else "OMR {{FirstSumInsured}}"
        h.append(f'<tr><td>{sil}</td><td class="c">{val}</td><td class="arb">{sia}</td></tr></table>')
    h.append('<div class="sp"></div>')
    if p["benef"]:
        h.append('<table class="g"><tr class="bar"><td>Beneficiary</td><td class="ar" style="color:#fff;font-weight:bold">المستفيد</td></tr></table>')
        h.append('<table class="g"><colgroup><col style="width:30%"><col style="width:19%"><col style="width:51%"></colgroup><tr><td>Name</td><td>Share <b class="ar" style="float:right">الحصة</b></td><td>Relationship to Insured Person <b class="ar" style="float:right">صلته بالمؤمن عليه</b></td></tr>')
        h.append('{{#each Beneficiaries}}<tr><td>{{Name}}</td><td class="c">{{Share}}</td><td class="c">{{Relationship}}</td></tr>{{/each}}</table><div class="sp"></div>')
    h.append('<table class="g"><colgroup><col style="width:29%"><col style="width:33%"><col style="width:38%"></colgroup>')
    h.append('<tr><td>Total Premium Amount</td><td>{{PremiumTextEn}}</td><td class="ar">إجمالي مبلغ القسط <span style="float:left">{{PremiumTextAr}}</span></td></tr>')
    h.append('<tr><td>Payment Frequency</td><td>{{FrequencyEn}}</td><td class="ar">طريقة السداد <span style="float:left">{{FrequencyAr}}</span></td></tr>')
    h.append('<tr><td>Period of Cover</td><td>{{PeriodEn}}</td><td class="ar">فترة التغطية <div style="font-size:8.5pt;margin-top:1mm">{{PeriodAr}}</div></td></tr>')
    tc_en = p.get("tc_en") or f"This Certificate of Insurance is subject to the terms and conditions of {p['cert_tc'][0]}."
    h.append(f'<tr><td colspan="2">{tc_en}</td><td class="ar">{p["cert_tc"][1]}</td></tr></table>')
    h.append(f'<table class="sig"><tr><td style="width:55%">For Arabia Falcon Insurance SAOG,</td><td class="ar" style="width:45%;text-align:right">(شركة التأمين العربية فالكون ش.م.ع.ع)</td></tr>'
             f'<tr><td colspan="2" style="height:24mm"><img src="{STAMP}" style="width:32mm;margin-top:2mm"></td></tr>'
             '<tr><td><b>(Authorized Signatory)</b></td><td class="ar" style="text-align:right">(المفوض بالتوقيع)</td></tr></table></body></html>')
    return "\n".join(h)
if __name__ == "__main__":
    for code, p in PRODUCTS.items():
        open(f"{OUT}/UP_{code}_APPLICATION_EN.html", "w").write(application(code, p))
        open(f"{OUT}/UP_{code}_POLICY_EN.html", "w").write(certificate(code, p))
        print(code, os.path.getsize(f"{OUT}/UP_{code}_APPLICATION_EN.html"), os.path.getsize(f"{OUT}/UP_{code}_POLICY_EN.html"))
