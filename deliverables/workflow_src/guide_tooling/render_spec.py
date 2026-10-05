#!/usr/bin/env python3
"""Renders the specification content to PDF (HTML + Chromium, TOC page numbers from a first pass) and DOCX (python-docx), in the layout of the InsureMO reference specification."""
import os, re, sys, html, subprocess, json
import importlib
sc = importlib.import_module(os.environ.get('SPEC_CONTENT', 'spec_content'))
B = os.environ["B"]; OUT = B + "/final2"; WORK = B + "/specwork"; os.makedirs(WORK, exist_ok=True)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TITLE = os.environ.get("DOC_TITLE", "Afillar Standard API Specification"); SUB = os.environ.get("DOC_SUB", "Insurance Integration"); TAG = os.environ.get("DOC_TAG", "A Standard Orchestration Layer for Channel Partners")
VERSION = os.environ.get("DOC_VERSION", "Version 1.1"); DATE = os.environ.get("DOC_DATE", "02-Oct-2026"); PREP = os.environ.get("DOC_PREP", "Prepared for the Afillar Channel Integration Program")
OUTNAME = os.environ.get("DOC_OUT", "Afillar_Insurance_API_Specification_v1.1")
NAVY = "#1F3864"; BLUE = "#0B4DA2"; HEAD = "#DCE6F1"
esc = html.escape
# ------------------------------------------------------------------ figures (SVG)
def box(x, y, w, h, text, fill="#0B4DA2", color="white", dash=None, size=11, stroke=None):
    lines = text.split("\n"); ty = y + h / 2 - (len(lines) - 1) * 7 + 4
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="1.6" stroke-dasharray="{dash}"' if dash else "") + "/>"
    for i, l in enumerate(lines): s += f'<text x="{x + w / 2}" y="{ty + i * 14}" text-anchor="middle" font-size="{size}" font-weight="bold" fill="{color}">{esc(l)}</text>'
    return s
def arrow(x1, y1, x2, y2, label="", dashed=False, above=True):
    d = ' stroke-dasharray="5,3"' if dashed else ""
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#222" stroke-width="1.2"{d} marker-end="url(#a)"/>'
    if label: s += f'<text x="{(x1 + x2) / 2}" y="{y1 - 5 if above else y1 + 13}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#222">{esc(label)}</text>'
    return s
DEFS = '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#222"/></marker></defs>'
def fig1():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="400" viewBox="0 0 760 400" font-family="Liberation Sans, Arial, sans-serif">{DEFS}'
    s += '<rect x="0" y="0" width="760" height="400" fill="white"/>'
    s += '<rect x="215" y="36" width="140" height="350" fill="#E8EBDD"/><rect x="505" y="36" width="140" height="350" fill="#E8EBDD"/>'
    s += box(20, 10, 130, 24, "Partner UI / Channel", "#8ED0FA", "#123", size=11) + box(360, 10, 130, 24, "Afillar APIs", "#4B6FB5", "white", size=11) + box(640, 10, 110, 24, "Platform services", "#8ED0FA", "#123", size=11)
    steps = [("Request for Token", "Get Token", None), ("Request for Plans", "Get Plans", "Rating service"), ("Create Proposal", "Create Proposal", "Policy service"), ("Issue Policy", "Issue Policy", "Policy service"), ("Request for Documents", "Documents", "Output service")]
    y = 62
    for req, api, plat in steps:
        s += arrow(150, y, 360, y, req) + box(360, y - 14, 130, 36, api, "#0B4DA2", "white")
        s += arrow(360, y + 14 + 6, 150, y + 14 + 6, "Response", True, False)
        if plat: s += arrow(490, y, 640, y, "Request") + box(640, y - 12, 110, 28, plat, "#F4A83A", "#222", size=10) + arrow(640, y + 24, 490, y + 24, "Response", True, False)
        y += 68
    return s + "</svg>"
def fig2():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="330" viewBox="0 0 760 330" font-family="Liberation Sans, Arial, sans-serif">{DEFS}<rect width="760" height="330" fill="white"/>'
    s += f'<text x="380" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="{NAVY}">INSURANCE — API ORCHESTRATION FLOWS</text>'
    s += box(10, 50, 64, 50, "JOURNEY A\nSales", "#0B4DA2", "white", size=10)
    xs = [86, 170, 254, 338, 422, 506, 590]; names = ["Get Plans", "Create\nProposal", "Update\nProposal", "Issue\nPolicy", "Policy\nDocuments", "Load Policy", "Reject\nProposal"]
    for x, nme in zip(xs, names):
        optional = nme.startswith("Update") or nme.startswith("Reject")
        s += box(x, 50, 76, 50, nme, "white" if optional else "#0B4DA2", "#168A5A" if optional else "white", dash="5,3" if optional else None, stroke="#168A5A" if optional else None, size=10)
    for a, b2 in zip(xs[:5], xs[1:6]): s += arrow(a + 76, 75, b2, 75)
    s += box(10, 190, 64, 50, "JOURNEY B\nCancel", "#168A5A", "white", size=10)
    s += box(86, 190, 90, 50, "Cancel Check\n(Checker)", "#0B4DA2", "white", size=10) + arrow(176, 215, 200, 215) + box(200, 190, 90, 50, "Cancel Approve\n(Approver)", "#0B4DA2", "white", size=10)
    s += arrow(290, 215, 314, 215) + box(314, 190, 90, 50, "Load Policy\n(Cancelled)", "#0B4DA2", "white", size=10)
    s += f'<text x="190" y="265" font-size="9.5" fill="#444" font-style="italic">Checker creates the pending request; the Approver decides APPROVE or REJECT</text>'
    s += '<rect x="86" y="292" width="14" height="10" fill="#0B4DA2"/><text x="106" y="301" font-size="9.5">Afillar API step</text><rect x="210" y="292" width="14" height="10" fill="white" stroke="#168A5A" stroke-dasharray="3,2"/><text x="230" y="301" font-size="9.5">Optional / exceptional step</text>'
    return s + "</svg>"

def fig_arch():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="470" viewBox="0 0 760 470" font-family="Liberation Sans, Arial, sans-serif">{DEFS}<rect width="760" height="470" fill="white"/>'
    cols = [("Channel", 10, "#8ED0FA"), ("InsureMO gateway", 140, "#8ED0FA"), ("iComposer APIs", 290, "#4B6FB5"), ("Common functions", 470, "#4B6FB5"), ("Platform services", 620, "#F4A83A")]
    for t, x, c in cols: s += box(x, 8, 120 if x != 290 else 165, 26, t, c, "#123" if c != "#4B6FB5" else "white", size=10)
    s += box(10, 60, 110, 44, "Partner system\nPostman / bank app", "white", "#123", dash="3,2", stroke="#0B4DA2", size=10) + box(140, 60, 120, 44, "Route + bearer\ntoken check", "white", "#123", dash="3,2", stroke="#0B4DA2", size=10)
    s += arrow(120, 82, 140, 82) + arrow(260, 82, 290, 82)
    s += box(290, 56, 165, 52, "13 API scripts\n(api/UP*/UP*.groovy)", "#0B4DA2", "white", size=10)
    fn = ["UPSecurity", "UPValidator", "UPProductData", "UPShaper", "UPCancelService", "UPDocService / UPDocBuilder", "UPErrorHandler", "UPDataUtil", "UPPlatformClient"]
    for i, t in enumerate(fn): s += box(470, 56 + i * 31, 140, 27, t, "#0B4DA2", "white", size=9)
    s += arrow(455, 82, 470, 82)
    svc = ["Proposal SDK\nload save calc issue search", "Endorsement REST\ncreateEx calculateEx\nvalidate issue suspend", "Print / Output\nservice (PDF)", "Rating\n<CODE>_PREM_CALC"]
    for i, t in enumerate(svc): s += box(620, 56 + i * 54, 130, 46, t, "#F4A83A", "#222", size=8)
    s += arrow(610, 190, 620, 190)
    s += box(10, 350, 740, 30, "iTables (read by the APIs, changed with imo): UP_ApiConfig  UP_FieldRule  UP_ProductMaster  UP_ProductPlanRelation  UP_PlanBenefitRelation  UP_ProductRule", "#E8EBDD", "#123", size=9)
    s += box(10, 386, 740, 30, "UP_DocTemplate  UP_DocWording  UP_BenefitText  UP_FeedColumn  UP_Channel  UP_Carrier   |   code tables: BranchCode GenderCode IdType Relationship ...", "#E8EBDD", "#123", size=9)
    s += f'<text x="380" y="445" text-anchor="middle" font-size="10" font-style="italic" fill="#444">Every API: readInput -> validate -> platform call(s) -> shapeResponse; any exception -> UPErrorHandler (status, code, message, trace_id)</text>'
    return s + "</svg>"
def fig_cancel():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="420" viewBox="0 0 760 420" font-family="Liberation Sans, Arial, sans-serif">{DEFS}<rect width="760" height="420" fill="white"/>'
    s += box(20, 8, 120, 24, "Checker", "#8ED0FA", "#123") + box(300, 8, 170, 24, "UPCancelService", "#4B6FB5", "white") + box(590, 8, 150, 24, "Platform (endorsement)", "#F4A83A", "#222", size=10)
    y = 52
    for lab, x1, x2, dash in [("cancel-check (policy, date, reason)", 140, 300, False), ("load policy, refundCalc", 470, 590, False), ("createEx (type 3, cancel 31/32)", 470, 590, False), ("RequestNo, refund details", 300, 140, True)]:
        s += arrow(x1, y, x2, y, lab, dash); y += 34
    s += box(20, 196, 120, 24, "Approver", "#8ED0FA", "#123")
    y = 236
    for lab, x1, x2, dash in [("cancel-approve (APPROVE)", 140, 300, False), ("queryPendingEndo (signed id)", 470, 590, False), ("suspendEndorsement", 470, 590, False), ("createEx, calculateEx, validate, issue", 470, 590, False), ("APPROVED, status 3, refund", 300, 140, True)]:
        s += arrow(x1, y, x2, y, lab, dash); y += 34
    s += f'<text x="20" y="412" font-size="9.5" font-style="italic" fill="#444">When the platform refuses a step the fresh endorsement stays pending: the answer is HTTP 409 and the request can be approved again or rejected.</text>'
    return s + "</svg>"

def fig_arch2():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="500" viewBox="0 0 760 500" font-family="Liberation Sans, Arial, sans-serif">{DEFS}<rect width="760" height="500" fill="white"/>'
    cols = [("Channels", 8, "#8ED0FA", 110), ("InsureMO gateway", 130, "#8ED0FA", 110), ("iComposer APIs", 255, "#4B6FB5", 150), ("Common functions", 425, "#4B6FB5", 150), ("Platform services", 595, "#F4A83A", 160)]
    for t, x, c, w in cols: s += box(x, 8, w, 26, t, c, "#123" if c != "#4B6FB5" else "white", size=10)
    s += box(8, 50, 110, 56, "Sohar portal\n(UIC page)", "white", "#123", dash="3,2", stroke="#0B4DA2", size=10) + box(8, 112, 110, 44, "Partner systems\nPostman / apps", "white", "#123", dash="3,2", stroke="#0B4DA2", size=10)
    s += box(130, 50, 110, 56, "Route + bearer\ntoken check", "white", "#123", dash="3,2", stroke="#0B4DA2", size=10) + arrow(118, 78, 130, 78) + arrow(118, 134, 150, 106)
    s += box(255, 50, 150, 100, "18 active API scripts\n13 original /up APIs\n+ me, worklist,\ndashboard, share,\ncancel-detail", "#0B4DA2", "white", size=10) + arrow(240, 78, 255, 78) + arrow(405, 98, 425, 98)
    fn = ["UPSecurity", "UPValidator", "UPProductData", "UPShaper", "UPCancelService", "UPDocService / UPDocBuilder", "UPErrorHandler", "UPDataUtil", "UPPlatformClient", "UPAccess (roles)", "UPNotify (email / SMS)", "UPWorklist (queues, dashboard)"]
    for i, t in enumerate(fn): s += box(425, 44 + i * 25, 150, 21, t, "#168A5A" if i >= 9 else "#0B4DA2", "white", size=9)
    svc = ["Proposal SDK\nload save calc issue", "Endorsement REST\ncreateEx ... issue", "Search index\npolicy + endorsement", "Print / Output\nservice (PDF)", "SNS service\nemail / SMS (dry run)", "Rating\n<CODE>_PREM_CALC"]
    for i, t in enumerate(svc): s += box(595, 44 + i * 46, 160, 40, t, "#F4A83A", "#222", size=8)
    s += arrow(575, 190, 595, 190)
    s += box(8, 356, 744, 26, "iTables read by the APIs: UP_ApiConfig  UP_FieldRule  UP_ProductMaster  UP_ProductPlanRelation  UP_PlanBenefitRelation  UP_ProductRule  UP_Carrier", "#E8EBDD", "#123", size=9)
    s += box(8, 386, 744, 26, "UP_DocTemplate  UP_DocWording  UP_BenefitText  UP_FeedColumn  UP_Channel  |  new in v1.2: UP_UserRole (roles)  UP_NotifyTemplate (messages)", "#E8EBDD", "#123", size=9)
    s += box(8, 416, 744, 26, "Not used by the /up APIs: iHub, the adapter table AdapterServiceCfg and the config-centre URLs used by the PA001 APIs (section 18)", "white", "#7a2", dash="4,3", stroke="#7a2", size=9)
    s += f'<text x="380" y="470" text-anchor="middle" font-size="10" font-style="italic" fill="#444">Every API: readInput -> validate -> role check -> platform call(s) -> shapeResponse; any exception -> UPErrorHandler (status, code, message, trace_id)</text>'
    return s + "</svg>"
def fig_wf():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="470" viewBox="0 0 760 470" font-family="Liberation Sans, Arial, sans-serif">{DEFS}<rect width="760" height="470" fill="white"/>'
    s += box(10, 8, 150, 26, "Maker", "#8ED0FA", "#123") + box(305, 8, 150, 26, "Platform (proposal, search)", "#F4A83A", "#222", size=10) + box(600, 8, 150, 26, "Checker", "#8ED0FA", "#123")
    y = 52
    for lab, x1, x2, dash in [("POST /up/proposal  (AgentCode = maker id)", 160, 305, False), ("SUBMITTED alert (UPNotify)", 305, 600, True)]:
        s += arrow(x1, y, x2, y, lab, dash); y += 32
    s += arrow(600, y, 455, y, "POST /up/worklist (PROPOSAL, PENDING)"); y += 32
    s += arrow(455, y, 600, y, "queue rows (index search + load)", True); y += 32
    s += arrow(600, y, 455, y, "GET /up/load-policy (detail)"); y += 40
    s += box(300, y - 14, 160, 30, "Approve: POST /up/issue", "#168A5A", "white", size=10) + box(480, y - 14, 160, 30, "Reject: POST /up/proposal-reject", "#C0392B", "white", size=9); y += 38
    s += arrow(305, y, 160, y, "PROPOSAL_ISSUED / REJECTED alert to the maker (+ customer)", True); y += 44
    s += box(10, y - 14, 150, 26, "Maker", "#8ED0FA", "#123") + box(305, y - 14, 150, 26, "Platform (endorsement)", "#F4A83A", "#222", size=10) + box(600, y - 14, 150, 26, "Cancellation Checker", "#8ED0FA", "#123", size=10); y += 30
    for lab, x1, x2, dash in [("POST /up/cancel-check -> pending endorsement", 160, 305, False), ("CANCEL_REQUESTED alert", 305, 600, True), ("POST /up/cancel-detail", 600, 455, False), ("POST /up/cancel-approve (APPROVE / REJECT)", 600, 455, False)]:
        s += arrow(x1, y, x2, y, lab, dash); y += 28
    s += f'<text x="10" y="{y + 14}" font-size="9.5" font-style="italic" fill="#444">Rule: the person who created the proposal / request cannot approve or reject it (UPAccess.requireNotCreator, switch AllowSelfApproval).</text>'
    return s + "</svg>"
def fig_pa001():
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="360" viewBox="0 0 760 360" font-family="Liberation Sans, Arial, sans-serif">{DEFS}<rect width="760" height="360" fill="white"/>'
    s += f'<text x="10" y="20" font-size="12" font-weight="bold" fill="{NAVY}">PA001 APIs (group Policy_API, routes /get-plans, /proposal ...)</text>'
    s += box(10, 34, 110, 40, "iComposer API\n(e.g. Proposal)", "#0B4DA2", "white", size=9) + arrow(120, 54, 150, 54) + box(150, 34, 120, 40, "SDK validate\n(proposal / quotation)", "#4B6FB5", "white", size=9) + arrow(270, 54, 300, 54)
    s += box(300, 34, 130, 40, "XxxService\n(ProposalService ...)", "#0B4DA2", "white", size=9) + arrow(430, 54, 460, 54) + box(460, 34, 150, 40, "IhubCallerIntegration-\nAdapter", "#0B4DA2", "white", size=9)
    s += arrow(610, 54, 630, 54) + box(630, 34, 120, 40, "AdapterServiceCfg\n(5 rows, PA001)", "#E8EBDD", "#123", size=9)
    s += box(460, 100, 150, 36, "ProductMaster.IsResident = Y ?", "white", "#123", dash="3,2", stroke="#0B4DA2", size=9) + arrow(535, 74, 535, 100)
    s += box(300, 170, 170, 40, "Yes (PA001): ImoAPICallerService\nPOST to the configured URL", "#168A5A", "white", size=9) + arrow(500, 136, 420, 170, "yes")
    s += box(520, 170, 170, 40, "No: IhubCallerService\nPOST to an iHub integration", "#F4A83A", "#222", size=9) + arrow(570, 136, 600, 170, "no")
    s += box(300, 236, 170, 30, "URL from config-centre key\nimo.motor.*.url (not readable)", "#E8EBDD", "#123", size=8) + arrow(385, 210, 385, 236)
    s += f'<text x="10" y="300" font-size="12" font-weight="bold" fill="{NAVY}">New products (group UP_PRODUCTS_API, routes /up/...)</text>'
    s += box(10, 312, 110, 36, "iComposer API\n(e.g. UPProposal)", "#0B4DA2", "white", size=9) + arrow(120, 330, 150, 330) + box(150, 312, 130, 36, "UPValidator\n(UP_FieldRule)", "#0B4DA2", "white", size=9) + arrow(280, 330, 310, 330)
    s += box(310, 312, 150, 36, "UPAccess role check", "#168A5A", "white", size=9) + arrow(460, 330, 490, 330) + box(490, 312, 260, 36, "Platform SDK / REST directly (no adapter, no iHub)", "#F4A83A", "#222", size=9)
    return s + "</svg>"
FIGS = {"fig1": (fig1(), 760, 400), "fig2": (fig2(), 760, 330), "arch": (fig_arch(), 760, 470), "cancel": (fig_cancel(), 760, 420), "arch2": (fig_arch2(), 760, 500), "wf": (fig_wf(), 760, 470), "pa001": (fig_pa001(), 760, 360)}
for k, (svg, w, h) in FIGS.items():
    open(f"{WORK}/{k}.html", "w").write(f"<html><head><style>html,body{{margin:0;overflow:hidden}}svg{{display:block}}</style></head><body>{svg}</body></html>")
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--force-device-scale-factor=2", f"--window-size={w},{h + 100}", f"--screenshot={WORK}/{k}.png", f"{WORK}/{k}.html"], capture_output=True, timeout=90)
# ------------------------------------------------------------------ HTML
def inline(t):
    x = esc(str(t))
    x = re.sub(r"`([^`]+)`", r"<code>\1</code>", x)
    x = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", x)
    x = re.sub(r"(?<![\w*])\*([^*\s][^*]*[^*\s])\*(?![\w*])", r"<em>\1</em>", x)
    return x
def slug(t): return "s" + re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
CSS = f"""
@page {{ size: A4; margin: 13mm 13mm 15mm 13mm; @bottom-right {{ content: counter(page); font: 9pt 'Liberation Sans', Arial; color: #666; }} }}
@page cover {{ margin: 13mm; @bottom-right {{ content: none; }} }}
body {{ font-family: Carlito, Calibri, 'Liberation Sans', Arial, sans-serif; font-size: 10.5pt; line-height: 1.32; color: #111; margin: 0; }}
.cover {{ page: cover; box-sizing: border-box; height: 250mm; text-align: center; padding-top: 70mm; }}
.cover h1 {{ font-size: 30pt; color: {NAVY}; margin: 0 0 8px; }} .cover h2 {{ font-size: 21pt; color: {BLUE}; margin: 6px 0; }} .cover .tag {{ font-style: italic; color: #444; font-size: 13pt; margin-bottom: 38px; }}
.cover .meta {{ font-size: 11pt; line-height: 1.5; }}
h1 {{ font-size: 18pt; color: {NAVY}; margin: 0 0 8px; page-break-before: always; }}
h1.first {{ page-break-before: auto; }}
h2 {{ font-size: 13pt; color: {NAVY}; margin: 14px 0 5px; page-break-after: avoid; }} h2.pg {{ page-break-before: always; margin-top: 0; }}
.lbl {{ font-weight: bold; color: {BLUE}; font-size: 11pt; margin: 10px 0 4px; page-break-after: avoid; }}
.lblb {{ font-weight: bold; margin: 8px 0 2px; page-break-after: avoid; }}
p {{ margin: 0 0 6px; text-align: left; }} p.note {{ font-style: italic; color: #444; }}
ul {{ margin: 0 0 6px 0; padding-left: 26px; list-style: none; }} ul li {{ position: relative; margin: 1px 0; }} ul li:before {{ content: '●'; position: absolute; left: -22px; font-size: 7pt; top: 3px; }}
ol {{ margin: 0 0 6px 0; padding-left: 26px; }}
.kv {{ font-weight: bold; margin: 2px 0; }} .kv span {{ font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; margin: 4px 0 8px; font-size: 9pt; table-layout: fixed; }}
th, td {{ border: 0.8px solid #000; padding: 4px 6px; vertical-align: top; text-align: left; word-wrap: break-word; overflow-wrap: anywhere; }}
th {{ background: {HEAD}; font-weight: bold; }} tr {{ page-break-inside: avoid; }} thead {{ display: table-header-group; }}
td.c {{ text-align: center; }}
code {{ font-family: 'DejaVu Sans Mono', monospace; font-size: 8.4pt; background: #F2F2F2; padding: 0 2px; }}
pre {{ background: #F5F5F5; border: 0.8px solid #999; padding: 6px 8px; font-family: 'DejaVu Sans Mono', monospace; font-size: 7.6pt; line-height: 1.25; white-space: pre-wrap; word-wrap: break-word; margin: 2px 0 8px; }}
figure {{ margin: 6px 0; text-align: center; page-break-inside: avoid; }} figure svg {{ width: 100%; height: auto; }} figcaption {{ font-style: italic; color: #444; font-size: 9.5pt; margin-top: 3px; }}
.toc {{ page-break-before: always; }} .toc h1 {{ page-break-before: auto; }} .toc .l {{ display: flex; font-size: 9.5pt; line-height: 1.55; }} .toc .l .t {{ white-space: nowrap; }} .toc .l .d {{ flex: 1; border-bottom: 1px dotted #555; margin: 0 4px 4px; }} .toc .l2 {{ padding-left: 14px; }} .toc .l3 {{ padding-left: 28px; }}
"""
def render_html(pages=None):
    pages = pages or {}
    toc = []; body = []
    first = True
    for b in sc.blocks:
        k = b[0]
        if k == "h1":
            toc.append((1, b[1])); body.append(f'<h1 id="{slug(b[1])}"{" class=first" if False else ""}>{inline(b[1])}</h1>')
        elif k == "h2":
            toc.append((2, b[1])); body.append(f'<h2 id="{slug(b[1])}"{" class=pg" if b[2] else ""}>{inline(b[1])}</h2>')
        elif k == "lbl":
            if re.match(r"^\d+\.\d+\.\d+ ", b[1]): toc.append((3, b[1])); body.append(f'<div class="lblb" id="{slug(b[1])}">{inline(b[1])}</div>')
            elif b[1].endswith(":") or b[1].startswith("Journey"): body.append(f'<div class="lblb">{inline(b[1])}</div>')
            else: body.append(f'<div class="lbl">{inline(b[1])}</div>')
        elif k == "p": body.append(f"<p>{inline(b[1])}</p>")
        elif k == "note": body.append(f'<p class="note">{inline(b[1])}</p>')
        elif k == "bul": body.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + "</ul>")
        elif k == "num": body.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in b[1]) + "</ol>")
        elif k == "kv": body.append(f'<div class="kv">{inline(b[1])} {inline(b[2])}</div>')
        elif k == "code": body.append(f"<pre>{esc(b[1])}</pre>")
        elif k == "fig": body.append(f"<figure>{sc_fig(b[1])}<figcaption>{inline(b[2])}</figcaption></figure>")
        elif k == "tbl":
            head, rows, widths = b[1], b[2], b[3]
            cg = "<colgroup>" + "".join(f'<col style="width:{w}%">' for w in widths) + "</colgroup>" if widths else ""
            reqcol = head.index("Required") if "Required" in head else -1
            trs = "".join("<tr>" + "".join(f'<td class="{"c" if i == reqcol else ""}">{inline(c)}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
            body.append(f"<table>{cg}<thead><tr>" + "".join(f"<th>{inline(h)}</th>" for h in head) + f"</tr></thead><tbody>{trs}</tbody></table>")
    tocl = ['<div class="toc"><h1>Table of Contents</h1>']
    tocl.append(f'<div class="l"><span class="t">Table of Contents</span><span class="d"></span><span>2</span></div>')
    for lvl, t in toc: tocl.append(f'<div class="l l{lvl}"><span class="t">{inline(t)}</span><span class="d"></span><span>{pages.get(t, "")}</span></div>')
    tocl.append("</div>")
    cover = f'<div class="cover"><h1>{TITLE}</h1><h2>{SUB}</h2><div class="tag">{TAG}</div><div class="meta">{VERSION}<br>{DATE}<br>{PREP}</div></div>'
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cover}{''.join(tocl)}{''.join(body)}</body></html>", toc
def sc_fig(name): return FIGS[name][0]
def to_pdf(html_text, path):
    open(WORK + "/spec.html", "w").write(html_text)
    r = subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={path}", WORK + "/spec.html"], capture_output=True, timeout=180)
def page_texts(pdf):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    return [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", pdf, "-"], capture_output=True, text=True).stdout for i in range(1, n + 1)]
def build_pdf():
    h, toc = render_html(); pdf = OUT + "/" + OUTNAME + ".pdf"
    to_pdf(h, pdf)
    for _ in range(2):
        txt = page_texts(pdf); pages = {}; start = 2
        for lvl, t in toc:
            key = re.sub(r"\s+", " ", t).strip()
            for i in range(start, len(txt)):
                if i < 2: continue
                if key in re.sub(r"[ \t]+", " ", txt[i]): pages[t] = i + 1; start = i; break
        h, _ = render_html(pages); to_pdf(h, pdf)
    return pdf, len(txt)
if __name__ == "__main__":
    pdf, n = build_pdf(); print("pdf pages", n)
