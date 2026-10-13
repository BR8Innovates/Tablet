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
fails=cnt["FAIL"]; 
p=doc.add_paragraph(); r=p.add_run("Verdict: NOT READY for production sign-off. "); r.bold=True; r.font.color.rgb=RGBColor(0xC0,0,0)
p.add_run(f"{tot} automated API test cases were executed against the InsureMO UAT back-end: {cnt['PASS']} passed, {fails} failed and {cnt['OBSERVATION']} are observations that need a business or UI decision. The failures roll up into 18 defects, of which 2 are Critical and 5 High. A further {len(MANUAL)} Uponly UI / workflow cases are written but could not be executed (no UI access).")
doc.add_paragraph("What works well: the core pricing engine matches the spec – all 10 Annual and 10 Single premium/commission combinations (2 options × 5 plans each) return the exact spec premium and 70% commission; sum insured per plan/coverage matches the spec (one spec typo flagged); the server ignores client-tampered premium and sum insured; create → update → load → issue → load policy works; application form and certificate PDFs populate correctly (dynamic travel row, Single/Annual wording, Arabic names, term); cancellation free-look, pro-rata and 80% refund calculations are correct, and cancel-approve / reject behave correctly with proper 4xx errors.")
doc.add_paragraph("What blocks go-live:")
for t in ["A rejected proposal can still be issued as an Effective policy (DEF-01).","A policy can be issued without LC/LG codes or payment details (DEF-02).","Total sum insured is double-counted due to a duplicate empty PlanList entry (DEF-03).","The feed file labels Term Life policies as 'Personal Accident…' and fills Cancelled Date on live policies (DEF-04, DEF-05).","The back-end enforces almost no mandatory-field, beneficiary-share, term or data-format validation – everything relies on the Uponly UI (DEF-06, 07, 09, 10)."]:
    doc.add_paragraph(t,style="List Bullet")
doc.add_heading("2. Results at a glance",1)
table([["PASS",cnt["PASS"],f"{100*cnt['PASS']/tot:.0f}%"],["FAIL",cnt["FAIL"],f"{100*cnt['FAIL']/tot:.0f}%"],["OBSERVATION",cnt["OBSERVATION"],f"{100*cnt['OBSERVATION']/tot:.0f}%"],["Total executed",tot,"100%"],["Not executed (UI / manual)",len(MANUAL),"–"]],["Status","Count","Share"],[6,3,3],{0:{"PASS":"C6EFCE","FAIL":"FFC7CE","OBSERVATION":"FFEB9C"}})
doc.add_paragraph()
mods=OrderedDict()
for r in R: mods.setdefault(r["module"],Counter())[r["status"]]+=1
table([[m,sum(c.values()),c["PASS"],c["FAIL"],c["OBSERVATION"]] for m,c in mods.items()],["Module","Total","Pass","Fail","Obs."],[6,2,2,2,2])
doc.add_heading("3. Defects",1)
doc.add_paragraph("Full evidence (request/response summaries) is in the Excel workbook, sheets 'Test Cases & Results' and 'Defects'.")
table([[d["id"],d["sev"],d["title"],d["tests"]] for d in D],["ID","Severity","Defect","Test cases"],[1.6,1.8,9,4.6],{1:{"Critical":"FF9999","High":"FFC7CE","Medium":"FFEB9C","Low":"E2EFDA"}})
doc.add_paragraph()
for d in D[:7]:
    doc.add_heading(f"{d['id']} – {d['title']}",3)
    p=doc.add_paragraph(); p.add_run("Severity: ").bold=True; p.add_run(d["sev"]+"   "); p.add_run("Spec: ").bold=True; p.add_run(d["spec"])
    doc.add_paragraph(d["desc"]); p=doc.add_paragraph(); p.add_run("Recommendation: ").bold=True; p.add_run(d["rec"])
doc.add_heading("4. Observations needing a decision",1)
obs=[r for r in R if r["status"]=="OBSERVATION"]
table([[r["id"],r["title"],r["actual"][:260]] for r in obs],["ID","Test","Finding"],[2,5.5,9.5])
doc.add_paragraph()
p=doc.add_paragraph(); p.add_run("Age rules (TL-UW-01…07): ").bold=True; p.add_run("the back-end accepts ages 17, 65, 68, 70 and a future date of birth. The spec assigns age validation to the Uponly UI, so these are recorded as observations, but we recommend a back-end guard as well.")
doc.add_heading("5. Spec clarifications requested",1)
for i,(a,b) in enumerate(C,1):
    p=doc.add_paragraph(style="List Number"); p.add_run(a+": ").bold=True; p.add_run(b)
doc.add_heading("6. Scope, approach and limitations",1)
for t in ["API-level UAT executed with a scripted runner calling the Postman-collection endpoints (get-plans, proposal, update-proposal, load-policy, issue, proposal-reject, doc_generation, generate-feedfile, cancel-check, cancel-approve, list-master-table) with a fresh token from the Token API (tokens saved in the collection had expired).",
 "Test design: spec-based premium/coverage matrix (20 combinations), equivalence/boundary analysis (age, term, share, dates), negative and mandatory-field tests, lifecycle state-transition tests, document content checks (PDF text compared to the TL application form / certificate templates), feed-file column and value checks, cancellation calculations, security and concurrency checks.",
 "Not executed: Uponly UI behaviours, maker/checker roles, document upload, Production Report, e-mail consent/digital signature (24 cases are written in the workbook as 'Not executed'). PA, CI, HCB, DH, FP and Life Protect products were out of scope.",
 "Data created: the run created about 155 proposals and 19 policies in UAT (ApplicationNo UAT-0001, CIF 45678). Several policies were cancelled during testing. Please clean up if required.",
 "Test oracles were reviewed after the run: about 20 results were re-tested against fresh data and corrected (for example cancellation-date checks that were masked by a pending request, and a certificate-field comparison that was a data-type mismatch). Remaining PASS results that rely on an HTTP 500 error are counted as 'rejected' – the 500 itself is logged as DEF-16.",
 "Security hygiene: the Postman collection contains a plaintext user name/password and bearer tokens. Rotate the credentials and keep them in environment variables, not in the shared collection. Credentials are not stored in the delivered scripts."]:
    doc.add_paragraph(t,style="List Bullet")
doc.add_heading("7. Exit recommendation",1)
doc.add_paragraph("Fix DEF-01 to DEF-07 and re-run the failed cases (the runner re-executes the full suite in ~5 minutes) before UAT sign-off. DEF-08 to DEF-18 can be scheduled with business agreement; clarifications in section 5 should be answered first because DEF-09 and DEF-12 depend on them. UI test cases (TL-UI-01…24) must be executed on the Uponly front-end before final sign-off.")
doc.save(sys.argv[1]); print("ok")
