import pickle, re, sys
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill
from xlhelp import *
from prep import CATS, CPS
from analysis import PROVIDERS

D = pickle.load(open('prep.pkl', 'rb'))
S, A = D['2026-09'], D['2026-08']
SEP, AUG = 'Raw Data', 'Raw Data Aug'
nS, nA = len(S['raw']), len(A['raw'])
TABCOL = {'Go Digit': 'C00000', 'ICICI Lombard': '0F6FC6', 'Tata AIG': '548235'}
OUT = sys.argv[1] if len(sys.argv) > 1 else 'Fibe_Carrier_Error_Analysis_September_2026.xlsx'
SYS_CAT = 'System/Technical Error'

wb = Workbook()
wb.remove(wb.active)


def sheet(name, color):
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = color
    return ws


def occ(d, ins=None, prod=None, cat=None, err=None):
    r = d['raw']
    if ins: r = r[r.provider == ins]
    if prod: r = r[r['product'] == prod]
    if cat: r = r[r.cat == cat]
    if err is not None: r = r[r.err_n == err]
    return int(r.occ.sum())


def calls(d, p, pr):
    c = d['calls'].loc[(p, pr)]
    return int(c.calls), int(c.succ)


def cats_for(p):
    """categories with failures for this carrier in Sep OR Aug, ordered by Sep volume then Aug"""
    cs = [c for c in CATS if occ(S, p, cat=c) + occ(A, p, cat=c) > 0]
    return sorted(cs, key=lambda c: (-occ(S, p, cat=c), -occ(A, p, cat=c)))


def pct(a, b):
    return a / b if b else 0


def sx(*parts):
    """Sum of SUMIFS formulas over Sep + Aug raw sheets."""
    return None


# ------------------------------------------------------------------ RAW DATA sheets
def raw_sheet(name, d, n):
    ws = sheet(name, '808080')
    header(ws, 1, ['Insurer', 'Registration No', 'Product', 'PlanType', 'Error Encountered',
                   'Occurrences (%s)' % ('Sep' if d is S else 'Aug'), 'Category'], height=25.5)
    for i, r in enumerate(d['raw'].itertuples(index=False), start=2):
        vals = [r.provider, r.reg_disp, r.product, str(r.plantype), r.err_n, int(r.occ), r.cat]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.font = font(size=9)
    widths(ws, {'A': 15, 'B': 16, 'C': 9, 'D': 10, 'E': 60, 'F': 14, 'G': 26})
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = 'A1:G%d' % (n + 1)
    ws.sheet_view.showGridLines = False
    return ws


# ------------------------------------------------------------------ build sheets in final order
ws_readme = sheet('Read Me', NAVY)
ws_exec = sheet('Executive Summary', NAVY)
ws_cat = sheet('Category Breakdown', NAVY)
ws_car = {p: sheet(p, TABCOL[p]) for p in PROVIDERS}
ws_2w = sheet('2W', '7030A0')
ws_4w = sheet('4W', '7030A0')
ws_cum = sheet('Cumulative (Aug+Sep)', '7030A0')
ws_pol = sheet('Policy Issuance', '00B050')
ws_fun = sheet('Funnel & GWP', '00B050')
ws_ret = sheet('Retry & Cross-Carrier', 'BF8F00')
ws_sys = sheet('System-Technical Errors', 'BF8F00')
ws_find = sheet('Findings vs August', 'BF8F00')
ws_day = sheet('Daily Trend', 'BF8F00')
ws_ver = sheet('Data Verification', 'FF0000')
raw_sheet(SEP, S, nS)
raw_sheet(AUG, A, nA)

# ================================================================== EXECUTIVE SUMMARY
ws = ws_exec
title(ws, 'Executive Summary — September 2026',
      'Quote-generation call volume and outcomes by carrier and product, September 2026 (API-derived). Total calls & Success are '
      'pulled from the InsureMO transaction log (blue); Failed and Success rate are formulas; the August comparison is on the right.', 11)
header(ws, 4, ['Carrier × Product', 'Total Calls', 'Success', 'Failed (Summary)', 'Failed (Raw Data check)', 'Success Rate',
               'Failure Share of Total', 'Aug Total Calls', 'Aug Success Rate', 'Δ Success Rate (pp)', 'Check'])
tot_calls = sum(calls(S, p, pr)[0] for p, pr in CPS)
tot_fail = sum(calls(S, p, pr)[0] - calls(S, p, pr)[1] for p, pr in CPS)
EXROW = {}
for i, (p, pr) in enumerate(CPS):
    r = 5 + i
    EXROW[(p, pr)] = r
    c, s = calls(S, p, pr)
    ca, sa = calls(A, p, pr)
    label(ws, r, 1, '%s — %s' % (p, pr))
    num(ws, r, 2, c, blue=True)
    num(ws, r, 3, s, blue=True)
    formula(ws, r, 4, '=B%d-C%d' % (r, r), c - s)
    formula(ws, r, 5, '=' + sumifs(SEP, nS, ins=p, prod=pr), occ(S, p, pr))
    formula(ws, r, 6, '=C%d/B%d' % (r, r), s / c, '0.0%')
    formula(ws, r, 7, '=D%d/SUM($B$5:$B$10)' % r, (c - s) / tot_calls, '0.0%')
    num(ws, r, 8, ca, blue=True)
    num(ws, r, 9, sa / ca, '0.0%', blue=True)
    formula(ws, r, 10, '=(F%d-I%d)*100' % (r, r), (s / c - sa / ca) * 100, '+0.0;-0.0;0.0')
    formula(ws, r, 11, '=IF(D%d=E%d,"OK","DIFF")' % (r, r), 'OK', 'General')
r = 11
label(ws, r, 1, 'TOTAL', total=True)
tot_succ = sum(calls(S, p, pr)[1] for p, pr in CPS)
formula(ws, r, 2, '=SUM(B5:B10)', tot_calls, total=True)
formula(ws, r, 3, '=SUM(C5:C10)', tot_succ, total=True)
formula(ws, r, 4, '=SUM(D5:D10)', tot_fail, total=True)
formula(ws, r, 5, '=SUM(E5:E10)', int(S['raw'].occ.sum()), total=True)
formula(ws, r, 6, '=C11/B11', tot_succ / tot_calls, '0.0%', total=True)
formula(ws, r, 7, '=SUM(G5:G10)', tot_fail / tot_calls, '0.0%', total=True)
a_calls = sum(calls(A, p, pr)[0] for p, pr in CPS)
a_succ = sum(calls(A, p, pr)[1] for p, pr in CPS)
formula(ws, r, 8, '=SUM(H5:H10)', a_calls, total=True)
num(ws, r, 9, a_succ / a_calls, '0.0%', total=True)
formula(ws, r, 10, '=(F11-I11)*100', (tot_succ / tot_calls - a_succ / a_calls) * 100, '+0.0;-0.0;0.0', total=True)
formula(ws, r, 11, '=IF(D11=E11,"OK","DIFF")', 'OK', 'General', total=True)
note(ws, 13, 'Definitions: a "call" is every quick-quote (txn 1001) and, for Tata AIG 4W, compare-quote (txn 4001) request logged by the InsureMO integration '
      'adapter. "Success" = the carrier response contained a premium and no error. Product (2W/4W) comes from the request ProductType, so Go Digit '
      '(whose CountryCode is just "IND") splits cleanly with no "Unknown" bucket. The same rules reproduce the August workbook and deck exactly '
      '(see Data Verification).', 11, 58, color='595959')
widths(ws, {'A': 24, 'B': 13, 'C': 13, 'D': 15, 'E': 17, 'F': 13, 'G': 16, 'H': 14, 'I': 14, 'J': 14, 'K': 9})

# ================================================================== CATEGORY BREAKDOWN
ws = ws_cat
title(ws, 'Root-Cause Category Breakdown — September 2026',
      'The %d distinct normalised error strings rolled up into 12 categories. Every value below is a live SUMIFS formula against the Raw Data tab.'
      % S['raw'].err_n.nunique(), 10)
header(ws, 4, ['Category'] + ['%s\n%s' % cp for cp in CPS] + ['Total', '% of All Failures', 'Aug Total', 'Δ vs Aug'])
cat_tot_s = {c: occ(S, cat=c) for c in CATS}
cat_tot_a = {c: occ(A, cat=c) for c in CATS}
order = sorted(CATS, key=lambda c: -cat_tot_s[c])
grand = sum(cat_tot_s.values())
for i, c in enumerate(order):
    r = 5 + i
    label(ws, r, 1, c)
    for j, (p, pr) in enumerate(CPS):
        formula(ws, r, 2 + j, '=' + sumifs(SEP, nS, ins=p, prod=pr, cat=c), occ(S, p, pr, c))
    formula(ws, r, 8, '=SUM(B%d:G%d)' % (r, r), cat_tot_s[c])
    formula(ws, r, 9, '=H%d/$H$17' % r, cat_tot_s[c] / grand, '0.0%')
    num(ws, r, 10, cat_tot_a[c], blue=True)
    formula(ws, r, 11, '=H%d-J%d' % (r, r), cat_tot_s[c] - cat_tot_a[c], '+#,##0;-#,##0;0')
r = 17
label(ws, r, 1, 'TOTAL', total=True)
for j, (p, pr) in enumerate(CPS):
    col = 'BCDEFG'[j]
    formula(ws, r, 2 + j, '=SUM(%s5:%s16)' % (col, col), occ(S, p, pr), total=True)
formula(ws, r, 8, '=SUM(H5:H16)', grand, total=True)
formula(ws, r, 9, '=SUM(I5:I16)', 1.0, '0.0%', total=True)
formula(ws, r, 10, '=SUM(J5:J16)', sum(cat_tot_a.values()), total=True)
formula(ws, r, 11, '=H17-J17', grand - sum(cat_tot_a.values()), '+#,##0;-#,##0;0', total=True)
note(ws, 19, 'Aug Total is the API-derived August figure on the same normalisation (categories shown above reproduce the August workbook within 0.2%; '
      'the only reclassification is Digit "JSON parse error … manufactureDate" which is now Invalid Input Value rather than Other).', 11, 32, color='595959')
widths(ws, {'A': 32, 'B': 13, 'C': 13, 'D': 13, 'E': 13, 'F': 13, 'G': 13, 'H': 12, 'I': 14, 'J': 11, 'K': 11})
for r in range(5, 17):
    ws.row_dimensions[r].height = 15


# ================================================================== CARRIER DEEP DIVES
def top_reasons(d, p, pr, k=10):
    f = d['fail']
    g = f[(f.provider == p) & (f['product'] == pr)]
    t = g.groupby('err_n').agg(o=('ok', 'size'), regs=('reg', lambda s: s[s != ''].nunique())).sort_values('o', ascending=False).head(k)
    return t


def sh(val, tot):
    return '%.0f%%' % (100 * val / tot) if tot else '0%'


def carrier_notes(p):
    out = []
    t2 = {pr: top_reasons(S, p, pr, 3) for pr in ('2W', '4W')}
    tot = {pr: S['calls'].loc[(p, pr)].fail for pr in ('2W', '4W')}
    ca = {pr: calls(S, p, pr) for pr in ('2W', '4W')}
    aa = {pr: calls(A, p, pr) for pr in ('2W', '4W')}
    for pr in ('2W', '4W'):
        out.append('•  %s %s success rate is %.1f%% (%s of %s calls) against %.1f%% in August.' %
                   (p, pr, 100 * ca[pr][1] / ca[pr][0], format(ca[pr][1], ','), format(ca[pr][0], ','), 100 * aa[pr][1] / aa[pr][0]))
    ih = S['fail'][(S['fail'].provider == p) & S['fail'].err_n.str.contains('iHub', na=False)]
    if p == 'ICICI Lombard':
        for pr in ('2W', '4W'):
            e, r = t2[pr].index[0], t2[pr].iloc[0]
            if 'TP is not allowed' in e:
                out.append('•  "TP is not allowed" is %s of %s failures (%s occurrences across %s registrations) — a Third-Party-only cover restriction on the carrier side, '
                           'not a technical fault; worth asking ICICI whether it can be pre-filtered.' % (sh(r.o, tot[pr]), pr, format(int(r.o), ','), format(int(r.regs), ',')))
        if len(ih):
            d0 = ih.groupby('date').size().sort_values(ascending=False)
            out.append('•  %s calls failed with iHub integration errors, %s of them on %s. The dominant signature is an unresolved route placeholder '
                       '("@route.il.host@@route.il.motor.auth.endpoint@") — an endpoint configuration fault on the platform, fixable by engineering.'
                       % (format(len(ih), ','), format(int(d0.iloc[0]), ','), d0.index[0]))
        nsm = occ(S, p, err='java.lang.NoSuchMethodError')
        out.append('•  java.lang.NoSuchMethodError (%s occurrences) points to a platform build/dependency fault rather than carrier behaviour.' % format(nsm, ','))
    elif p == 'Go Digit':
        uw = occ(S, p, err='UW rules violated!!')
        regs = S['fail'][(S['fail'].provider == p) & (S['fail'].err_n == 'UW rules violated!!') & (S['fail'].reg != '')].reg.nunique()
        out.append('•  "UW rules violated!!" is %s of all Digit failures (%s occurrences across %s registrations) — carrier underwriting rejections, mostly retried on the same vehicles.'
                   % (sh(uw, int(S['calls'].loc[p].fail.sum())), format(uw, ','), format(regs, ',')))
        dg = S['fail'][(S['fail'].provider == p) & S['fail'].err_n.str.contains('outtrf', na=False)]
        if len(dg):
            d0 = dg.groupby('date').size().sort_values(ascending=False)
            out.append('•  %s calls failed on the iHub response-transformation rule "go-digit-in-motor-quick-quote-outtrf" (%s on %s) — a platform-side rule fault, not a Digit decision.'
                       % (format(len(dg), ','), format(int(d0.iloc[0]), ','), d0.index[0]))
        far = occ(S, p, err='Quote creation cannot be possible as inception date of the policy is more than6 months in future')
        rto = occ(S, p, err='Invalid RTO identified from registration number (see RegistrationNo column)')
        out.append('•  Fibe-side fixable: Invalid RTO (%s) and far-future start dates (%s) — both are input-validation gaps that can be blocked before the call.' % (format(rto, ','), format(far, ',')))
    else:
        b = occ(S, p, err='1182-please provide bundle od start date and bundle od end date')
        e = occ(S, p, err='engine_secure_options  is mandatory.')
        ip = occ(S, p, err='Invalid Policy Plan')
        out.append('•  Missing bundle OD start/end date (%s) and mandatory engine_secure_options (%s) are malformed requests — 100%% Fibe/integration-fixable.' % (format(b, ','), format(e, ',')))
        out.append('•  "Invalid Policy Plan" now accounts for %s occurrences (Aug %s) — a plan-code mapping gap, concentrated in 2W.' % (format(ip, ','), format(occ(A, p, err='Invalid Policy Plan'), ',')))
        fb = occ(S, p, err='Forbidden')
        st = occ(S, p, err='status=None')
        out.append('•  "Forbidden" (%s) and "status=None" (%s) are carrier/gateway-side faults worth raising with Tata\'s integration team.' % (format(fb, ','), format(st, ',')))
    return out


for p in PROVIDERS:
    ws = ws_car[p]
    col = TABCOL[p]
    title(ws, '%s — Deep Dive' % p, 'Category mix, top failure reasons and analyst notes for 2-wheeler and 4-wheeler quote calls, September 2026.', 8)
    header(ws, 4, ['Category', '2W Occ.', '2W %', '4W Occ.', '4W %', 'Aug 2W Occ.', 'Aug 4W Occ.'], fill=col)
    cats = cats_for(p)
    n = len(cats)
    t2, t4 = occ(S, p, '2W'), occ(S, p, '4W')
    for i, c in enumerate(cats):
        r = 5 + i
        label(ws, r, 1, c)
        formula(ws, r, 2, '=' + sumifs(SEP, nS, ins=p, prod='2W', cat=c), occ(S, p, '2W', c))
        formula(ws, r, 3, '=B%d/$B$%d' % (r, 5 + n), pct(occ(S, p, '2W', c), t2), '0.0%')
        formula(ws, r, 4, '=' + sumifs(SEP, nS, ins=p, prod='4W', cat=c), occ(S, p, '4W', c))
        formula(ws, r, 5, '=D%d/$D$%d' % (r, 5 + n), pct(occ(S, p, '4W', c), t4), '0.0%')
        formula(ws, r, 6, '=' + sumifs(AUG, nA, ins=p, prod='2W', cat=c), occ(A, p, '2W', c))
        formula(ws, r, 7, '=' + sumifs(AUG, nA, ins=p, prod='4W', cat=c), occ(A, p, '4W', c))
    r = 5 + n
    label(ws, r, 1, 'TOTAL', total=True)
    formula(ws, r, 2, '=SUM(B5:B%d)' % (r - 1), t2, total=True)
    formula(ws, r, 3, '=B%d/$B$%d' % (r, r), 1.0, '0.0%', total=True)
    formula(ws, r, 4, '=SUM(D5:D%d)' % (r - 1), t4, total=True)
    formula(ws, r, 5, '=D%d/$D$%d' % (r, r), 1.0, '0.0%', total=True)
    formula(ws, r, 6, '=SUM(F5:F%d)' % (r - 1), occ(A, p, '2W'), total=True)
    formula(ws, r, 7, '=SUM(G5:G%d)' % (r - 1), occ(A, p, '4W'), total=True)
    # top reasons
    r += 2
    for pr in ('2W', '4W'):
        ws.cell(row=r, column=1, value='Top Failure Reasons — %s' % pr).font = font(True, col, 12)
        r += 1
        header(ws, r, ['Error Message', 'Occurrences', 'Unique Regs', '% of Carrier-Product Total', 'Aug Occurrences'], fill=col)
        ptot = occ(S, p, pr)
        for k, (e, row_) in enumerate(top_reasons(S, p, pr).iterrows(), start=1):
            rr = r + k
            text(ws, rr, 1, e, wrap=True)
            formula(ws, rr, 2, '=' + sumifs(SEP, nS, ins=p, prod=pr, err=Ref('A%d' % rr)), int(row_.o))
            num(ws, rr, 3, int(row_.regs))
            formula(ws, rr, 4, '=B%d/' % rr + sumifs(SEP, nS, ins=p, prod=pr), pct(int(row_.o), ptot), '0.0%')
            formula(ws, rr, 5, '=' + sumifs(AUG, nA, ins=p, prod=pr, err=Ref('A%d' % rr)), occ(A, p, pr, err=e))
        r += 12
    ws.cell(row=r, column=1, value='Analyst Notes').font = font(True, col, 12)
    r += 1
    for line in carrier_notes(p):
        note(ws, r, line, 8, 44)
        r += 1
    widths(ws, {'A': 62, 'B': 12, 'C': 12, 'D': 14, 'E': 14, 'F': 12, 'G': 12, 'H': 4})

# ================================================================== SYSTEM / TECHNICAL
ws = ws_sys
sysS = S['raw'][S['raw'].cat == SYS_CAT]
sig = (sysS.groupby(['provider', 'err_n']).agg(o=('occ', 'sum'), regs=('reg_disp', lambda s: s[s != '(blank)'].nunique()))
       .reset_index().sort_values('o', ascending=False))
tot_sys = int(sysS.occ.sum())
title(ws, 'Pure System / Technical Errors — September 2026',
      'The subset of failures caused by infrastructure or integration faults (timeouts, gateway errors, iHub/route configuration, missing services, null responses) '
      'rather than business rules or bad input data — i.e. failures that are 100% fixable on the engineering side.', 9)
note(ws, 4, 'Total system/technical failures, Sep 2026: %s occurrences (%.1f%% of all failures) across %d distinct error signatures. (Aug: %s, %.1f%%)'
     % (format(tot_sys, ','), 100 * tot_sys / grand, len(sig), format(cat_tot_a[SYS_CAT], ','), 100 * cat_tot_a[SYS_CAT] / sum(cat_tot_a.values())), 9, 18, bold=True)
header(ws, 6, ['Insurer', 'Error Signature', 'Occurrences', 'Unique Regs Affected', "% of Insurer's Total Failures", 'Aug Occurrences'])
ptot_s = {p: int(S['calls'].loc[p].fail.sum()) for p in PROVIDERS}
for i, row_ in enumerate(sig.itertuples(index=False)):
    r = 7 + i
    text(ws, r, 1, row_.provider)
    text(ws, r, 2, row_.err_n, wrap=True)
    formula(ws, r, 3, '=' + sumifs(SEP, nS, ins=row_.provider, err=Ref('B%d' % r)), int(row_.o))
    num(ws, r, 4, int(row_.regs))
    formula(ws, r, 5, '=C%d/' % r + sumifs(SEP, nS, ins=row_.provider), row_.o / ptot_s[row_.provider], '0.0%')
    formula(ws, r, 6, '=' + sumifs(AUG, nA, ins=row_.provider, err=Ref('B%d' % r)), occ(A, row_.provider, err=row_.err_n))
last = 6 + len(sig)
r = last + 2
ws.cell(row=r, column=1, value='Total System/Technical Failures by Insurer').font = font(True, 'BF8F00', 12)
header(ws, r + 1, ['Insurer', 'Total System/Tech Occurrences'])
for k, p in enumerate(PROVIDERS):
    formula(ws, r + 2 + k, 2, '=SUMIFS($C$7:$C$%d,$A$7:$A$%d,"%s")' % (last, last, p), occ(S, p, cat=SYS_CAT))
    label(ws, r + 2 + k, 1, p)
r += 6
ih = S['fail'][S['fail'].err_n.str.contains('iHub', na=False)]
d0 = ih.groupby('date').size().sort_values(ascending=False)
note(ws, r, 'Read as: the iHub / route-configuration faults are concentrated in a single incident window — %s iHub-related failures in total, %s of them on %s '
     '(unresolved ICICI route placeholder "@route.il.host@…" and the Go Digit "outtrf" response-transformation rule). Outside that window the system-fault floor is low, '
     'which suggests a one-off deployment/configuration event rather than chronic instability.' % (format(len(ih), ','), format(int(d0.iloc[0]), ','), d0.index[0]), 9, 62)
widths(ws, {'A': 15, 'B': 80, 'C': 13, 'D': 14, 'E': 17, 'F': 14})

# ================================================================== RETRY & CROSS-CARRIER
ws = ws_ret
fS = S['fail'][S['fail'].reg != '']
per = S['per_reg']
reg_tot = int(per.sum())
title(ws, 'Retry Concentration & Cross-Carrier Failures — September 2026',
      'How much of the failure volume sits with a small set of registration numbers, and which ones fail at every carrier at once.', 9)
note(ws, 4, 'Total failed occurrences (Sep 2026, all carriers): %s   |   Distinct registration numbers involved: %s   (failures with no registration number: %d)'
     % (format(len(S['fail']), ','), format(len(per), ','), int((S['fail'].reg == '').sum())), 9, 18, bold=True)
ws.cell(row=6, column=1, value='Retry Concentration').font = font(True, 'BF8F00', 12)
header(ws, 7, ['Top N Registrations (by total failed attempts)', 'Failed Occurrences', 'Share of All Failures', 'Aug Share'])
perA = A['per_reg']
for i, nn in enumerate([10, 50, 100, 200, 500]):
    r = 8 + i
    label(ws, r, 1, 'Top %d registrations' % nn)
    num(ws, r, 2, int(per.head(nn).sum()))
    formula(ws, r, 3, '=B%d/%d' % (r, len(S['fail'])), per.head(nn).sum() / len(S['fail']), '0.0%')
    num(ws, r, 4, perA.head(nn).sum() / len(A['fail']), '0.0%')
n50 = int((per >= 50).sum())
note(ws, 14, '%d registration numbers (%.1f%% of all %s distinct regs involved) were retried 50+ times each and account for %.1f%% of all failure volume — '
     'a signal that retry logic is not backing off or halting after repeated identical failures. (Aug: %d regs, %.1f%%.)'
     % (n50, 100 * n50 / len(per), format(len(per), ','), 100 * per[per >= 50].sum() / len(S['fail']),
        int((perA >= 50).sum()), 100 * perA[perA >= 50].sum() / len(A['fail'])), 9, 44)
ws.cell(row=16, column=1, value='Top 20 Registration Numbers by Total Failed Attempts (all carriers)').font = font(True, 'BF8F00', 12)
header(ws, 17, ['Registration No', 'Total Failed Occ.', 'ICICI Lombard', 'Go Digit', 'Tata AIG', '# Carriers Hit', 'Most Common Error'])
by = fS.groupby(['reg', 'provider']).size().unstack(fill_value=0)
for k, (reg, tot_) in enumerate(per.head(20).items()):
    r = 18 + k
    text(ws, r, 1, reg)
    rowv = by.loc[reg]
    for j, p in enumerate(PROVIDERS):
        formula(ws, r, 3 + j, '=' + sumifs(SEP, nS, reg=Ref('$A%d' % r), ins=p), int(rowv.get(p, 0)))
    formula(ws, r, 2, '=SUM(C%d:E%d)' % (r, r), int(tot_))
    num(ws, r, 6, int((rowv > 0).sum()))
    text(ws, r, 7, fS[fS.reg == reg].err_n.value_counts().index[0], wrap=True)
allc = by[(by > 0).all(axis=1)]
ccocc = int(allc.sum().sum())
r = 40
ws.cell(row=r, column=1, value='Cross-Carrier Failures — Registrations That Fail at ALL Three Carriers').font = font(True, 'BF8F00', 12)
note(ws, r + 1, '%s registration numbers (%.1f%% of all distinct regs) failed at every one of the three carriers, contributing %s occurrences (%.1f%% of all failures). '
     'A registration no carrier can quote is unlikely to be a carrier-specific problem — it points to bad/duplicate input data reaching all three integrations. '
     '(Aug: 969 regs, 19,222 occurrences.)' % (format(len(allc), ','), 100 * len(allc) / len(per), format(ccocc, ','), 100 * ccocc / len(S['fail'])), 9, 44)
header(ws, r + 2, ['Registration No', 'Total Failed Occ.', 'ICICI Lombard', 'Go Digit', 'Tata AIG'])
for k, (reg, rowv) in enumerate(allc.assign(t=allc.sum(axis=1)).sort_values('t', ascending=False).head(20).iterrows()):
    rr = r + 3 + k
    text(ws, rr, 1, reg)
    for j, p in enumerate(PROVIDERS):
        formula(ws, rr, 3 + j, '=' + sumifs(SEP, nS, reg=Ref('$A%d' % rr), ins=p), int(rowv[p]))
    formula(ws, rr, 2, '=SUM(C%d:E%d)' % (rr, rr), int(rowv.t))
widths(ws, {'A': 40, 'B': 16, 'C': 14, 'D': 12, 'E': 12, 'F': 12, 'G': 70})

pickle.dump(dict(EXPECTED=EXPECTED), open('xl_expected_partA.pkl', 'wb'))
exec(open('build_xlsx_b.py').read())
