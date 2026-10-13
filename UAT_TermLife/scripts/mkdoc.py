import json,datetime,sys
from collections import Counter,OrderedDict
from docx import Document
from docx.shared import Pt,RGBColor,Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from manual import MANUAL
R=json.load(open("results.json")); D=json.load(open("defects.json")); C=json.load(open("clar.json"))
cnt=Counter(r["status"] for r in R); tot=len(R)
doc=Document()
for s in doc.sections: s.left_margin=s.right_margin=Cm(2); s.top_margin=s.bottom_margin=Cm(2)
st=doc.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(10.5)
def shade(cell,hexc):
    tcPr=cell._tc.get_or_add_tcPr(); sh=OxmlElement("w:shd"); sh.set(qn("w:val"),"clear"); sh.set(qn("w:color"),"auto"); sh.set(qn("w:fill"),hexc); tcPr.append(sh)
def table(rows,header,widths=None,colors=None):
    t=doc.add_table(rows=1,cols=len(header)); t.style="Table Grid"
    for i,h in enumerate(header):
        c=t.rows[0].cells[i]; c.text=""; p=c.paragraphs[0]; r=p.add_run(h); r.bold=True; r.font.color.rgb=RGBColor(255,255,255); r.font.size=Pt(9.5); shade(c,"1F3864")
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=""; r=cells[i].paragraphs[0].add_run(str(v)); r.font.size=Pt(9)
            if colors and i in colors and str(v) in colors[i]: shade(cells[i],colors[i][str(v)])
    if widths:
        for row in t.rows:
            for i,w in enumerate(widths): row.cells[i].width=Cm(w)
    return t
doc.add_heading("Term Life Insurance (TL001) – UAT Test Report",0)
p=doc.add_paragraph(); p.add_run("Environment: ").bold=True; p.add_run("uponlyuat-sandbox-in.insuremo.com (tenant uponlyuat, channel SOHAR)\n")
p.add_run("Execution date: ").bold=True; p.add_run(datetime.date.today().strftime("%d %b %Y")+"\n")
p.add_run("Product: ").bold=True; p.add_run("Term Life with Travel (ProductSubcode 1) and Term Life without Travel (ProductSubcode 2), Plans 1–5, Annual and Single premium\n")
p.add_run("Basis: ").bold=True; p.add_run("Additional Products Specs (AddlProducts_Specs.xlsx), UPONLY UAT Postman collection, Term Life application form and certificate formats")
doc.add_heading("1. Executive summary",1)
fails=cnt["FAIL"]
p=doc.add_paragraph(); r=p.add_run("Verdict: plans, premium and covers are CORRECT; 8 defects remain in generated outputs and cancellation. "); r.bold=True
p.add_run(f"{tot} API test cases were executed. Per the agreed position that the API performs no input validation (the Uponly UI does), validation-type cases are classed BY DESIGN ({cnt['BY DESIGN']}) and recorded as risks, not defects. Result: {cnt['PASS']} passed, {fails} failed, {cnt['OBSERVATION']} observations. {len(MANUAL)} UI/workflow cases are written but not executed.")
doc.add_paragraph("Plans, premium and covers: all 10 Annual and 10 Single premium/commission combinations (With/Without Travel x Plans 1-5) return the exact spec premium and 70% commission; coverages and sums insured match the spec (one spec typo flagged: Without-Travel Plan 1 Death 4,500 vs 7,500); the server overrides client-supplied premium and sum insured. Create, update, load, issue and load-policy work; application form and certificate PDFs populate correctly; cancellation refunds calculate correctly.")
doc.add_paragraph("Defects to fix (all relate to correctness of returned/printed details):")
for d in D: doc.add_paragraph(f"{d['id']} ({d['sev']}): {d['title']}",style="List Bullet")
p=doc.add_paragraph(); p.add_run("Risks accepted as by design (UI must enforce): ").bold=True; p.add_run("a rejected proposal can still be issued; issue works without LC/LG/payment details; mandatory fields, beneficiary share total, term limits, premium mode per product, age rules, ChannelCode and data formats are not checked by the API; invalid input returns HTTP 500. Please make sure the Uponly UI covers these.")
doc.add_heading("2. Results at a glance",1)
table([["PASS",cnt["PASS"],f"{100*cnt['PASS']/tot:.0f}%"],["BY DESIGN (no API validation)",cnt["BY DESIGN"],f"{100*cnt['BY DESIGN']/tot:.0f}%"],["FAIL",cnt["FAIL"],f"{100*cnt['FAIL']/tot:.0f}%"],["OBSERVATION",cnt["OBSERVATION"],f"{100*cnt['OBSERVATION']/tot:.0f}%"],["Total executed",tot,"100%"],["Not executed (UI / manual)",len(MANUAL),"–"]],["Status","Count","Share"],[6,3,3],{0:{"PASS":"C6EFCE","FAIL":"FFC7CE","OBSERVATION":"FFEB9C","BY DESIGN (no API validation)":"D9E1F2"}})
doc.add_paragraph()
mods=OrderedDict()
for r in R: mods.setdefault(r["module"],Counter())[r["status"]]+=1
table([[m,sum(c.values()),c["PASS"],c["FAIL"],c["OBSERVATION"],c["BY DESIGN"]] for m,c in mods.items()],["Module","Total","Pass","Fail","Obs.","By design"],[5,2,2,2,2,2.5])
doc.add_heading("3. Defects",1)
doc.add_paragraph("Full evidence (request/response summaries) is in the Excel workbook, sheets 'Test Cases & Results' and 'Defects'.")
table([[d["id"],d["sev"],d["title"],d["tests"]] for d in D],["ID","Severity","Defect","Test cases"],[1.6,1.8,9,4.6],{1:{"Critical":"FF9999","High":"FFC7CE","Medium":"FFEB9C","Low":"E2EFDA"}})
doc.add_paragraph()
for d in D[:3]:
    doc.add_heading(f"{d['id']} – {d['title']}",3)
    p=doc.add_paragraph(); p.add_run("Severity: ").bold=True; p.add_run(d["sev"]+"   "); p.add_run("Spec: ").bold=True; p.add_run(d["spec"])
    doc.add_paragraph(d["desc"]); p=doc.add_paragraph(); p.add_run("Recommendation: ").bold=True; p.add_run(d["rec"])
doc.add_heading("4. Observations needing a decision",1)
obs=[r for r in R if r["status"]=="OBSERVATION"]
table([[r["id"],r["title"],r["actual"][:260]] for r in obs],["ID","Test","Finding"],[2,5.5,9.5])
doc.add_paragraph()
p=doc.add_paragraph(); p.add_run("Age rules (TL-UW-01…07, by design): ").bold=True; p.add_run("the back-end accepts ages 17, 65, 68, 70 and a future date of birth. The spec assigns age validation to the Uponly UI, so these are recorded as observations, but we recommend a back-end guard as well.")
doc.add_heading("5. Spec clarifications requested",1)
for i,(a,b) in enumerate(C,1):
    p=doc.add_paragraph(style="List Number"); p.add_run(a+": ").bold=True; p.add_run(b)
doc.add_heading("6. Scope, approach and limitations",1)
for t in ["API-level UAT executed with a scripted runner calling the Postman-collection endpoints (get-plans, proposal, update-proposal, load-policy, issue, proposal-reject, doc_generation, generate-feedfile, cancel-check, cancel-approve, list-master-table) with a fresh token from the Token API (tokens saved in the collection had expired).",
 "Test design: spec-based premium/coverage matrix (20 combinations), equivalence/boundary analysis (age, term, share, dates), negative and mandatory-field tests, lifecycle state-transition tests, document content checks (PDF text compared to the TL application form / certificate templates), feed-file column and value checks, cancellation calculations, security and concurrency checks.",
 "Not executed: Uponly UI behaviours, maker/checker roles, document upload, Production Report, e-mail consent/digital signature (24 cases are written in the workbook as 'Not executed'). PA, CI, HCB, DH, FP and Life Protect products were out of scope.",
 "Data created: the run created about 155 proposals and 19 policies in UAT (ApplicationNo UAT-0001, CIF 45678). Several policies were cancelled during testing. Please clean up if required.",
 "Test oracles were reviewed after the run: about 20 results were re-tested against fresh data and corrected (for example cancellation-date checks that were masked by a pending request, and a certificate-field comparison that was a data-type mismatch). Remaining PASS results that rely on an HTTP 500 error are counted as 'rejected' – the 500 itself is noted as a by-design risk.",
 "Security hygiene: the Postman collection contains a plaintext user name/password and bearer tokens. Rotate the credentials and keep them in environment variables, not in the shared collection. Credentials are not stored in the delivered scripts."]:
    doc.add_paragraph(t,style="List Bullet")
doc.add_heading("7. Exit recommendation",1)
doc.add_paragraph("Fix the defects above and re-run the failed cases (the runner re-executes the full suite in ~5 minutes) before UAT sign-off. Clarifications in section 5 should be answered first because the free-look defect (DEF-05) depends on them. UI test cases (TL-UI-01…24) must be executed on the Uponly front-end before final sign-off.")
doc.save(sys.argv[1]); print("ok")
