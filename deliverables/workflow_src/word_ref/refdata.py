"""Per-variant data for the Output Service Word templates (verified against live MC policy objects, see ref_policy_objects.json)."""
import json, os
S = "/tmp/claude-0/-home-user-Tablet/4e5f48e0-1baf-5a1d-9f0f-ce844ee516ee/scratchpad"
B = S + "/uponly-build"
FORMS = S + "/lpforms/AppFormsAndCertificateFormats"
CERT_DIR = FORMS + "/CertificateFormatsForNewSystem/"
APP_DIR = FORMS + "/ApplicationFormsForNewSystem/"
REF_POL = S + "/ref_render/pol.docx"; REF_APP = S + "/ref_render/app.docx"
OBJ = json.load(open(B + "/ref_policy_objects.json"))
BT = {}   # (product, coverage code) -> (name en, name ar)
for x in json.load(open(B + "/tables/r_UP_BenefitText_0.json")).get("Records", []) if isinstance(json.load(open(B + "/tables/r_UP_BenefitText_0.json")), dict) else json.load(open(B + "/tables/r_UP_BenefitText_0.json")):
    BT[(x["ProductCode"], x["BenefitCode"])] = (x["NameEn"], x["NameAr"])
# coverage order on the platform per variant (verified on issued policies of every plan)
COV = {("UPPA001", "1"): ["REX", "ACD", "PTD", "PPD", "TTD", "HCB"], ("UPPA001", "2"): ["ACD", "PTD", "PPD", "HCB", "REX"],
       ("TL001", "1"): ["DTH", "PTD", "PPD", "TRV", "REX"], ("TL001", "2"): ["DTH", "PTD", "PPD", "REX"],
       ("FP001", "1"): ["FCC"], ("HC001", "1"): ["HCB"], ("CI001", "1"): ["CIB"], ("CI001", "2"): ["CIB"], ("CI001", "3"): ["CIB"],
       ("LP001", "1"): ["DTH", "PTD", "PPD"], ("DH001", "1"): ["DTH", "AME", "RHE", "REP"]}
SHOW = {("UPPA001", "1"): ["ACD", "PTD", "PPD", "TTD", "HCB", "REX"], ("UPPA001", "2"): ["ACD", "PTD", "PPD", "HCB", "REX"],
        ("TL001", "1"): ["DTH", "PTD", "PPD", "TRV", "REX"], ("TL001", "2"): ["DTH", "PTD", "PPD", "REX"],
        ("LP001", "1"): ["DTH", "PTD", "PPD"], ("DH001", "1"): ["DTH", "AME", "RHE", "REP"]}   # coverage rows printed (in this order)
PRODUCT = {
 "UPPA001": dict(cert="PA Certificate (3)-revised 10.07.2025.docx", app="Personal Accident Insurance 06878.docx", en="Personal Accident Insurance", ar="تأمين الحوادث الشخصية", insured="Insured Person", app_benef=True, cert_benef=True),
 "TL001": dict(cert="TL Certificate (3)-revised 10.07.2025.docx", app="Term Life Insurance 06878.docx", en="Term Life Insurance", ar="تأمين على الحياة لأجل محدد", insured="Policyholder", app_benef=True, cert_benef=True),
 "FP001": dict(cert="FC Certificate (3)-revised 10.07.2025.docx", app="Female Protecion Plan Application Form.docx", en="Female Protection Plan", ar="خطة حماية المرأة", insured="Insured Person", app_benef=False, cert_benef=False),
 "HC001": dict(cert="Certificate HCB.docx", app="Hospital Cash Benefit Application Form.docx", en="Hospital Cash Insurance", ar="تأمين منفعة الاستشفاء النقدي", insured="Insured Person", app_benef=False, cert_benef=False),
 "CI001": dict(cert="CI Certificate (3)-revised 10.07.2025.docx", app="Critical Illness Insurance Application Form 06878.docx", en="Critical Illness Insurance", ar="التأمين على الأمراض الحرجة", insured="Insured Person", app_benef=True, cert_benef=False),
 "DH001": dict(cert="DH Certificate (3)-revised 10.07.2025.docx", app="Domestic Helper Insurance Application Form.docx", en="Domestic Helper Insurance", ar="تأمين عامل المنزل", insured="Domestic Helper", app_benef=False, cert_benef=False),
 "LP001": dict(cert="TL Certificate (3)-revised 10.07.2025.docx", app=None, en="Life Protect", ar="خطة حماية الحياة", insured="Policy Holder", app_benef=True, cert_benef=True),
}
CI_COUNT = {"1": "7 CI", "2": "11 CI", "3": "32 CI"}
VARIANTS = [(c, s) for c, s in COV]
def variant_name(code, sub): return f"{code}_{sub}"
