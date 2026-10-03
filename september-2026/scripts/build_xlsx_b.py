# ---- part B (exec'd from build_xlsx.py; shares its namespace) ----
MON = {'2026-08': 'Aug 2026', '2026-09': 'Sep 2026'}

# ================================================================== POLICY ISSUANCE
ws = ws_pol
polA, polS = A['pol'], S['pol']
allpol = pd.concat([polA, polS]).sort_values(['month', 'provider', 'first_time']).reset_index(drop=True)
n_pol = len(allpol)
title(ws, 'Policy Issuance — PolicyNo & CarrierPolicyNo',
      'One row per issued policy. Go Digit: a policy counts as issued only when BOTH PolicyNo (carrier policyNumber returned by the issue-policy call) and '
      'CarrierPolicyNo are present (Digit\'s create-quote step also returns a CarrierPolicyNo — that is the quote id, not an issued policy). '
      'ICICI Lombard and Tata AIG: CarrierPolicyNo alone identifies the issued policy.', 12)
ws.row_dimensions[2].height = 52
HDR = 16
first, last = HDR + 1, HDR + n_pol
# summary block (formulas on the detail table)
ws.cell(row=4, column=1, value='Summary by insurer and month').font = font(True, '00B050', 12)
header(ws, 5, ['Insurer', 'Month', 'Policies (unique CarrierPolicyNo)', 'Flagged "Issued"', 'GWP (INR)', 'Avg Premium (INR)', 'With PolicyNo (Digit)'], fill='00B050')
r = 6
colrng = lambda c: '$%s$%d:$%s$%d' % (c, first, c, last)
for p in PROVIDERS:
    for m in ['2026-08', '2026-09']:
        sub = allpol[(allpol.provider == p) & (allpol.month == m)]
        label(ws, r, 1, p)
        text(ws, r, 2, MON[m])
        formula(ws, r, 3, '=COUNTIFS(%s,A%d,%s,B%d)' % (colrng('B'), r, colrng('A'), r), len(sub))
        issued = int((sub.apply(lambda x: (x.provider != 'Go Digit') or (x.policy_no != '' and x.carrier_policy_no != ''), axis=1)).sum())
        formula(ws, r, 4, '=COUNTIFS(%s,A%d,%s,B%d,%s,"Issued*")' % (colrng('B'), r, colrng('A'), r, colrng('L')), issued)
        formula(ws, r, 5, '=SUMIFS(%s,%s,A%d,%s,B%d)' % (colrng('J'), colrng('B'), r, colrng('A'), r), float(sub.premium.sum()))
        formula(ws, r, 6, '=IF(C%d=0,0,E%d/C%d)' % (r, r, r), float(sub.premium.sum() / len(sub)) if len(sub) else 0)
        if p == 'Go Digit':
            formula(ws, r, 7, '=COUNTIFS(%s,A%d,%s,B%d,%s,"<>")' % (colrng('B'), r, colrng('A'), r, colrng('G')), int((sub.policy_no != '').sum()))
        else:
            text(ws, r, 7, 'n/a')
        r += 1
label(ws, r, 1, 'TOTAL', total=True)
text(ws, r, 2, '', fill=TOTAL_FILL)
for c_, f_ in [(3, '=SUM(C6:C11)'), (4, '=SUM(D6:D11)'), (5, '=SUM(E6:E11)')]:
    pass
formula(ws, r, 3, '=SUM(C6:C11)', n_pol, total=True)
formula(ws, r, 4, '=SUM(D6:D11)', None, total=True)
formula(ws, r, 5, '=SUM(E6:E11)', float(allpol.premium.sum()), total=True)
formula(ws, r, 6, '=E%d/C%d' % (r, r), float(allpol.premium.sum() / n_pol), total=True)
text(ws, r, 7, '', fill=TOTAL_FILL)
POL_TOT_ROW = r
# digit quote-stage vs issued illustration
qs = {}
for m, d in [('2026-08', A), ('2026-09', S)]:
    x = d['iss']
    qs[m] = x[(x.provider == 'Go Digit') & (x.txn == 2001) & (x.carrier_policy_no != '')].carrier_policy_no.nunique()
note(ws, 13, 'Why both numbers for Go Digit: Digit\'s create-quote (2001) call returned a CarrierPolicyNo for %s distinct quotes in Aug and %s in Sep, but only %d and %d of them reached '
     'the issue-policy (2003) step with a carrier PolicyNo. Counting CarrierPolicyNo alone would overstate Digit issuance roughly %.0f×.'
     % (qs['2026-08'], qs['2026-09'], len(polA[polA.provider == 'Go Digit']), len(polS[polS.provider == 'Go Digit']),
        (qs['2026-08'] + qs['2026-09']) / max(1, len(polA[polA.provider == 'Go Digit']) + len(polS[polS.provider == 'Go Digit']))), 12, 44, color='595959')
note(ws, 14, 'Status caveat (same convention as the August deck, which counts every unique CarrierPolicyNo): %d Digit policy(ies) in Sep and 1 in Aug carry status UW_REFFERED (referred to '
     'underwriting) and %d ICICI policies in Aug have no status returned; they are counted as policies here for like-for-like comparison, and column L shows the strict check.'
     % ((polS.policy_status == 'UW_REFFERED').sum(), (polA[polA.provider == 'ICICI Lombard'].policy_status == '').sum()), 12, 44, color='595959')
header(ws, HDR, ['Month', 'Insurer', 'Product', 'Registration No', 'PlanType', 'Issued Date', 'PolicyNo (Digit only)', 'CarrierPolicyNo',
                  'Policy Status', 'Premium (INR)', 'Premium source', 'Issued? (formula)'], fill='00B050')
src = {'ICICI Lombard': 'Proposal GrossPremium', 'Go Digit': 'Issue response GrossPremium', 'Tata AIG': 'Payment Amount'}
n_issued_expected = 0
for i, x in enumerate(allpol.itertuples(index=False), start=first):
    text(ws, i, 1, MON[x.month])
    text(ws, i, 2, x.provider)
    text(ws, i, 3, x.product or '')
    text(ws, i, 4, x.reg)
    text(ws, i, 5, str(x.plantype))
    text(ws, i, 6, x.date)
    text(ws, i, 7, x.policy_no if x.provider == 'Go Digit' else 'n/a')
    text(ws, i, 8, x.carrier_policy_no)
    text(ws, i, 9, x.policy_status)
    num(ws, i, 10, float(x.premium), '#,##0.00')
    text(ws, i, 11, src[x.provider])
    if x.provider == 'Go Digit':
        f = ('=IF(AND(G{r}<>"",H{r}<>"",OR(I{r}="COMPLETE",I{r}="COMPLETED",I{r}="COMPLETE/COMPLETED")),"Issued",'
             'IF(AND(G{r}<>"",H{r}<>""),"Issued - check status ("&I{r}&")","Not issued"))').format(r=i)
        ok_ = x.policy_no != '' and x.carrier_policy_no != ''
        e = 'Issued' if (ok_ and x.policy_status in ('COMPLETE', 'COMPLETED', 'COMPLETE/COMPLETED')) else ('Issued - check status (%s)' % x.policy_status if ok_ else 'Not issued')
    else:
        f = '=IF(H{r}<>"",IF(I{r}="","Issued (no status returned)","Issued"),"Not issued")'.format(r=i)
        e = ('Issued (no status returned)' if x.policy_status == '' else 'Issued') if x.carrier_policy_no else 'Not issued'
    c = formula(ws, i, 12, f, e, 'General')
    c.alignment = Alignment(horizontal='left')
# fix expected of D total + summary issued counts (flag begins with "Issued")
EXPECTED[(ws.title, 'D%d' % POL_TOT_ROW)] = int(sum(1 for x in allpol.itertuples() if (x.provider != 'Go Digit' or (x.policy_no and x.carrier_policy_no))))
widths(ws, {'A': 11, 'B': 15, 'C': 12, 'D': 16, 'E': 16, 'F': 20, 'G': 18, 'H': 17, 'I': 16, 'J': 14, 'K': 26, 'L': 28})
ws.freeze_panes = ws.cell(row=HDR + 1, column=1)
ws.auto_filter.ref = 'A%d:L%d' % (HDR, last)
POL = dict(first=first, last=last)


def pol_f(kind, p=None, m=None, prod=None):
    """formula pieces on the Policy Issuance detail table"""
    cr = lambda c: "'Policy Issuance'!$%s$%d:$%s$%d" % (c, first, c, last)
    conds = []
    if p: conds += [cr('B'), '"%s"' % p]
    if m: conds += [cr('A'), '"%s"' % MON[m]]
    if prod: conds += [cr('C'), '"%s"' % prod]
    if kind == 'count':
        return 'COUNTIFS(' + ','.join(conds) + ')' if conds else 'COUNTA(%s)' % cr('A')
    return 'SUMIFS(%s,%s)' % (cr('J'), ','.join(conds))


def pol_exp(kind, p=None, m=None, prod=None):
    x = allpol
    if p: x = x[x.provider == p]
    if m: x = x[x.month == m]
    if prod: x = x[x['product'] == prod]
    return len(x) if kind == 'count' else float(x.premium.sum())


# ================================================================== FUNNEL & GWP
ws = ws_fun
title(ws, 'Funnel & GWP — September vs August 2026',
      'Unique-registration funnel per carrier. Leads = distinct registrations with at least one quote call; Priced = at least one successful quote; '
      'Applications = distinct registrations with a proposal call; Policies/GWP link to the Policy Issuance tab.', 9)
HEAD = ['Metric'] + ['%s\n%s' % (c, m) for c in PROVIDERS + ['Total'] for m in ('Aug', 'Sep')]
header(ws, 4, HEAD)
fa, fs = A['funnel'], S['funnel']
rows_def = [('Unique registrations (leads)', 'leads'), ('Leads with at least one price', 'priced'), ('Applications (proposal calls, unique regs)', 'apps')]
r = 5
FROW = {}
for lab, key in rows_def:
    label(ws, r, 1, lab)
    FROW[key] = r
    for j, c in enumerate(PROVIDERS + ['Total']):
        num(ws, r, 2 + 2 * j, int(fa[c][key]), blue=True)
        num(ws, r, 3 + 2 * j, int(fs[c][key]), blue=True)
    r += 1
label(ws, r, 1, 'Policies issued')
FROW['policies'] = r
for j, c in enumerate(PROVIDERS):
    for k, m in enumerate(['2026-08', '2026-09']):
        formula(ws, r, 2 + 2 * j + k, '=' + pol_f('count', c, m), pol_exp('count', c, m))
formula(ws, r, 8, '=B%d+D%d+F%d' % (r, r, r), pol_exp('count', None, '2026-08'))
formula(ws, r, 9, '=C%d+E%d+G%d' % (r, r, r), pol_exp('count', None, '2026-09'))
r += 1
label(ws, r, 1, 'GWP (INR)')
FROW['gwp'] = r
for j, c in enumerate(PROVIDERS):
    for k, m in enumerate(['2026-08', '2026-09']):
        formula(ws, r, 2 + 2 * j + k, '=' + pol_f('sum', c, m), pol_exp('sum', c, m), '#,##0')
formula(ws, r, 8, '=B%d+D%d+F%d' % (r, r, r), pol_exp('sum', None, '2026-08'), '#,##0')
formula(ws, r, 9, '=C%d+E%d+G%d' % (r, r, r), pol_exp('sum', None, '2026-09'), '#,##0')
r += 1
label(ws, r, 1, 'Quote calls')
FROW['calls'] = r
for j, c in enumerate(PROVIDERS):
    for k, (m, d, sheet_) in enumerate([('2026-08', A, None), ('2026-09', S, 'ex')]):
        v = int(d['funnel'][c]['calls'])
        if sheet_:
            rows_ = [EXROW[(c, pr)] for pr in ('2W', '4W')]
            formula(ws, r, 2 + 2 * j + k, "='Executive Summary'!B%d+'Executive Summary'!B%d" % tuple(rows_), v)
        else:
            num(ws, r, 2 + 2 * j + k, v, blue=True)
formula(ws, r, 8, '=B%d+D%d+F%d' % (r, r, r), int(fa['Total']['calls']))
formula(ws, r, 9, '=C%d+E%d+G%d' % (r, r, r), int(fs['Total']['calls']))
r += 1
label(ws, r, 1, 'Failed quote calls')
FROW['failed'] = r
for j, c in enumerate(PROVIDERS):
    for k, (m, d) in enumerate([('2026-08', A), ('2026-09', S)]):
        v = int(d['funnel'][c]['calls'] - d['funnel'][c]['succ'])
        if m == '2026-09':
            rows_ = [EXROW[(c, pr)] for pr in ('2W', '4W')]
            formula(ws, r, 2 + 2 * j + k, "='Executive Summary'!D%d+'Executive Summary'!D%d" % tuple(rows_), v)
        else:
            num(ws, r, 2 + 2 * j + k, v, blue=True)
formula(ws, r, 8, '=B%d+D%d+F%d' % (r, r, r), int(fa['Total']['calls'] - fa['Total']['succ']))
formula(ws, r, 9, '=C%d+E%d+G%d' % (r, r, r), int(fs['Total']['calls'] - fs['Total']['succ']))
r += 2
ws.cell(row=r, column=1, value='Conversions & unit economics').font = font(True, '00B050', 12)
r += 1
header(ws, r, HEAD)
conv = [('Lead → price %', 'priced', 'leads'), ('Lead → application %', 'apps', 'leads'), ('Application → policy %', 'policies', 'apps'),
        ('Lead → policy %', 'policies', 'leads')]
vals = {}
for key in ['leads', 'priced', 'apps']:
    for c in PROVIDERS + ['Total']:
        vals[(key, c, 'a')] = fa[c][key]; vals[(key, c, 's')] = fs[c][key]
for c in PROVIDERS + ['Total']:
    vals[('policies', c, 'a')] = pol_exp('count', None if c == 'Total' else c, '2026-08')
    vals[('policies', c, 's')] = pol_exp('count', None if c == 'Total' else c, '2026-09')
    vals[('gwp', c, 'a')] = pol_exp('sum', None if c == 'Total' else c, '2026-08')
    vals[('gwp', c, 's')] = pol_exp('sum', None if c == 'Total' else c, '2026-09')
    vals[('calls', c, 'a')] = fa[c]['calls']; vals[('calls', c, 's')] = fs[c]['calls']
    vals[('failed', c, 'a')] = fa[c]['calls'] - fa[c]['succ']; vals[('failed', c, 's')] = fs[c]['calls'] - fs[c]['succ']
r += 1
for lab, nk, dk in conv:
    label(ws, r, 1, lab)
    for j, c in enumerate(PROVIDERS + ['Total']):
        for k, tag in enumerate(['a', 's']):
            col = 'BCDEFGHI'[2 * j + k]
            formula(ws, r, 2 + 2 * j + k, '=IF(%s%d=0,0,%s%d/%s%d)' % (col, FROW[dk], col, FROW[nk], col, FROW[dk]),
                    pct(vals[(nk, c, tag)], vals[(dk, c, tag)]), '0.00%')
    r += 1
for lab, nk, dk, fmt in [('Average premium (INR)', 'gwp', 'policies', '#,##0'), ('Calls per lead', 'calls', 'leads', '0.0'),
                         ('Call success rate %', None, None, '0.0%'), ('Failed share of calls %', 'failed', 'calls', '0.0%')]:
    label(ws, r, 1, lab)
    for j, c in enumerate(PROVIDERS + ['Total']):
        for k, tag in enumerate(['a', 's']):
            col = 'BCDEFGHI'[2 * j + k]
            if nk is None:
                formula(ws, r, 2 + 2 * j + k, '=1-%s%d/%s%d' % (col, FROW['failed'], col, FROW['calls']),
                        1 - vals[('failed', c, tag)] / vals[('calls', c, tag)], fmt)
            else:
                formula(ws, r, 2 + 2 * j + k, '=IF(%s%d=0,0,%s%d/%s%d)' % (col, FROW[dk], col, FROW[nk], col, FROW[dk]),
                        pct(vals[(nk, c, tag)], vals[(dk, c, tag)]), fmt)
    r += 1
label(ws, r, 1, 'Share of GWP %')
for j, c in enumerate(PROVIDERS + ['Total']):
    for k, tag in enumerate(['a', 's']):
        col = 'BCDEFGHI'[2 * j + k]
        tcol = 'HI'[k]
        formula(ws, r, 2 + 2 * j + k, '=IF(%s%d=0,0,%s%d/%s%d)' % (tcol, FROW['gwp'], col, FROW['gwp'], tcol, FROW['gwp']),
                pct(vals[('gwp', c, tag)], vals[('gwp', 'Total', tag)]), '0.0%')

# ---- registration funnel by product (2W / 4W)
r += 2
ws.cell(row=r, column=1, value='Registration funnel by product — 2W and 4W (all carriers, distinct registrations)').font = font(True, '00B050', 12)
r += 1
header(ws, r, ['Metric', '2W\nAug', '2W\nSep', '4W\nAug', '4W\nSep', 'Total\nAug', 'Total\nSep'])
pf = {}
for pr in ('2W', '4W'):
    for tag, d in (('a', A), ('s', S)):
        qq = d['q']; g = qq[(qq['product'] == pr) & (qq.reg != '')]
        ap = d['apps']; ap = ap[ap['product'] == pr]
        pf[(pr, tag)] = dict(leads=g.reg.nunique(), priced=g[g.ok].reg.nunique(), apps=ap.reg.nunique(),
                             pol=pol_exp('count', None, '2026-08' if tag == 'a' else '2026-09', pr),
                             gwp=pol_exp('sum', None, '2026-08' if tag == 'a' else '2026-09', pr))
PFROW = {}
r += 1
for lab, key in [('Unique registrations (leads)', 'leads'), ('Leads with at least one price', 'priced'), ('Applications (unique regs)', 'apps')]:
    label(ws, r, 1, lab); PFROW[key] = r
    for j, (pr, tag) in enumerate([('2W', 'a'), ('2W', 's'), ('4W', 'a'), ('4W', 's')]):
        num(ws, r, 2 + j, int(pf[(pr, tag)][key]), blue=True)
    formula(ws, r, 6, '=B%d+D%d' % (r, r), int(pf[('2W', 'a')][key] + pf[('4W', 'a')][key]))
    formula(ws, r, 7, '=C%d+E%d' % (r, r), int(pf[('2W', 's')][key] + pf[('4W', 's')][key]))
    r += 1
for lab, key, fmt in [('Policies issued', 'pol', '#,##0'), ('GWP (INR)', 'gwp', '#,##0')]:
    label(ws, r, 1, lab); PFROW[key] = r
    for j, (pr, tag) in enumerate([('2W', 'a'), ('2W', 's'), ('4W', 'a'), ('4W', 's')]):
        m_ = '2026-08' if tag == 'a' else '2026-09'
        formula(ws, r, 2 + j, '=' + pol_f('count' if key == 'pol' else 'sum', None, m_, pr), pf[(pr, tag)][key], fmt)
    formula(ws, r, 6, '=B%d+D%d' % (r, r), pf[('2W', 'a')][key] + pf[('4W', 'a')][key], fmt)
    formula(ws, r, 7, '=C%d+E%d' % (r, r), pf[('2W', 's')][key] + pf[('4W', 's')][key], fmt)
    r += 1
for lab, nk, dk in [('Lead → price %', 'priced', 'leads'), ('Lead → application %', 'apps', 'leads'), ('Application → policy %', 'pol', 'apps'), ('Lead → policy %', 'pol', 'leads')]:
    label(ws, r, 1, lab)
    for j in range(6):
        col = 'BCDEFG'[j]
        if j < 4:
            pr, tag = [('2W', 'a'), ('2W', 's'), ('4W', 'a'), ('4W', 's')][j]
            e = pct(pf[(pr, tag)][nk], pf[(pr, tag)][dk])
        else:
            tag = 'a' if j == 4 else 's'
            e = pct(pf[('2W', tag)][nk] + pf[('4W', tag)][nk], pf[('2W', tag)][dk] + pf[('4W', tag)][dk])
        formula(ws, r, 2 + j, '=IF(%s%d=0,0,%s%d/%s%d)' % (col, PFROW[dk], col, PFROW[nk], col, PFROW[dk]), e, '0.00%')
    r += 1
note(ws, r + 1, 'Each registration is counted once per product; 2W + 4W equals the combined funnel above for every stage (leads, priced, applications, policies, GWP).', 9, 30, color='595959')

r += 2
note(ws, r, 'Registrations attempted sum to more than the Total because one vehicle is quoted with several carriers. Aug figures reproduce the August MBR deck exactly '
     '(4,935 leads / 4,556 priced / 242 applications / 59 policies / INR 1,27,793 GWP). July is not shown: the API holds July data only from 5 July and does not '
     'reconcile to the July figures in the August deck, so September is compared with August only.', 9, 58, color='595959')
widths(ws, {'A': 40, 'B': 12, 'C': 12, 'D': 12, 'E': 12, 'F': 12, 'G': 12, 'H': 12, 'I': 12})


# ================================================================== PRODUCT SHEETS (2W / 4W) and CUMULATIVE
def both(p=None, pr=None, cat=None, err=None):
    parts = {}
    if p: parts['ins'] = p
    if pr: parts['prod'] = pr
    if cat: parts['cat'] = cat
    if err is not None: parts['err'] = err
    return parts


def cum_f(ref_err=None, **kw):
    kw2 = dict(kw)
    if ref_err is not None: kw2['err'] = ref_err
    return '=' + sumifs(SEP, nS, **kw2) + '+' + sumifs(AUG, nA, **kw2)


def product_sheet(ws, pr, accent):
    title(ws, '%s — Carrier Comparison, Aug vs Sep vs Cumulative' % ('Two-Wheeler (2W)' if pr == '2W' else 'Four-Wheeler (4W)'),
          'Quote-call performance, failure mix and issuance for %s only. Cumulative = August + September 2026. Sep values link to the Executive Summary; Aug values are API-derived inputs (blue).' % pr, 11)
    header(ws, 4, ['Carrier', 'Aug Calls', 'Sep Calls', 'Cum. Calls', 'Aug Success', 'Sep Success', 'Cum. Success', 'Aug Success %', 'Sep Success %', 'Cum. Success %', 'Δ Aug→Sep (pp)'], fill=accent)
    for i, p in enumerate(PROVIDERS):
        r = 5 + i
        ca, sa = calls(A, p, pr)
        cs, ss = calls(S, p, pr)
        label(ws, r, 1, p)
        num(ws, r, 2, ca, blue=True)
        formula(ws, r, 3, "='Executive Summary'!B%d" % EXROW[(p, pr)], cs)
        formula(ws, r, 4, '=B%d+C%d' % (r, r), ca + cs)
        num(ws, r, 5, sa, blue=True)
        formula(ws, r, 6, "='Executive Summary'!C%d" % EXROW[(p, pr)], ss)
        formula(ws, r, 7, '=E%d+F%d' % (r, r), sa + ss)
        formula(ws, r, 8, '=E%d/B%d' % (r, r), sa / ca, '0.0%')
        formula(ws, r, 9, '=F%d/C%d' % (r, r), ss / cs, '0.0%')
        formula(ws, r, 10, '=G%d/D%d' % (r, r), (sa + ss) / (ca + cs), '0.0%')
        formula(ws, r, 11, '=(I%d-H%d)*100' % (r, r), (ss / cs - sa / ca) * 100, '+0.0;-0.0;0.0')
    r = 8
    label(ws, r, 1, 'TOTAL', total=True)
    ta = [sum(calls(A, p, pr)[i] for p in PROVIDERS) for i in (0, 1)]
    ts = [sum(calls(S, p, pr)[i] for p in PROVIDERS) for i in (0, 1)]
    for col, v in zip('BCDEFG', [ta[0], ts[0], ta[0] + ts[0], ta[1], ts[1], ta[1] + ts[1]]):
        formula(ws, r, 'ABCDEFG'.index(col) + 1, '=SUM(%s5:%s7)' % (col, col), v, total=True)
    formula(ws, r, 8, '=E8/B8', ta[1] / ta[0], '0.0%', total=True)
    formula(ws, r, 9, '=F8/C8', ts[1] / ts[0], '0.0%', total=True)
    formula(ws, r, 10, '=G8/D8', (ta[1] + ts[1]) / (ta[0] + ts[0]), '0.0%', total=True)
    formula(ws, r, 11, '=(I8-H8)*100', (ts[1] / ts[0] - ta[1] / ta[0]) * 100, '+0.0;-0.0;0.0', total=True)
    # issuance & funnel for this product
    r = 11
    ws.cell(row=r, column=1, value='Leads, applications, policies and GWP — %s' % pr).font = font(True, accent, 12)
    header(ws, r + 1, ['Carrier', 'Aug Leads', 'Sep Leads', 'Aug Priced', 'Sep Priced', 'Aug Policies', 'Sep Policies', 'Cum. Policies', 'Aug GWP (INR)', 'Sep GWP (INR)', 'Cum. GWP (INR)'], fill=accent)
    for i, p in enumerate(PROVIDERS):
        rr = r + 2 + i
        label(ws, rr, 1, p)
        for k, d in enumerate([A, S]):
            qq = d['q']
            g = qq[(qq.provider == p) & (qq['product'] == pr) & (qq.reg != '')]
            num(ws, rr, 2 + k, int(g.reg.nunique()), blue=True)
            num(ws, rr, 4 + k, int(g[g.ok].reg.nunique()), blue=True)
        for k, m in enumerate(['2026-08', '2026-09']):
            formula(ws, rr, 6 + k, '=' + pol_f('count', p, m, pr), pol_exp('count', p, m, pr))
            formula(ws, rr, 9 + k, '=' + pol_f('sum', p, m, pr), pol_exp('sum', p, m, pr))
        formula(ws, rr, 8, '=F%d+G%d' % (rr, rr), pol_exp('count', p, None, pr))
        formula(ws, rr, 11, '=I%d+J%d' % (rr, rr), pol_exp('sum', p, None, pr))
    rr = r + 5
    label(ws, rr, 1, 'TOTAL', total=True)
    for ci in range(2, 12):
        col = 'ABCDEFGHIJK'[ci - 1]
        # expected totals
        if ci in (2, 3, 4, 5):
            k = (ci - 2) % 2; kind = 'leads' if ci < 4 else 'priced'
            d = [A, S][k]
            qq = d['q']; g = qq[(qq['product'] == pr) & (qq.reg != '')]
            # sum of per-carrier uniques
            v = sum(int(qq[(qq.provider == p) & (qq['product'] == pr) & (qq.reg != '') & ((qq.ok) if kind == 'priced' else True)].reg.nunique()) for p in PROVIDERS)
        elif ci in (6, 7):
            v = pol_exp('count', None, ['2026-08', '2026-09'][ci - 6], pr)
        elif ci == 8:
            v = pol_exp('count', None, None, pr)
        elif ci in (9, 10):
            v = pol_exp('sum', None, ['2026-08', '2026-09'][ci - 9], pr)
        else:
            v = pol_exp('sum', None, None, pr)
        formula(ws, rr, ci, '=SUM(%s%d:%s%d)' % (col, r + 2, col, r + 4), v, total=True)
    note(ws, rr + 1, 'Leads/Priced are distinct registrations per carrier (a vehicle quoted with several carriers is counted once per carrier, so the total is the sum of the carrier counts).', 11, 30, color='595959')
    # category mix by carrier for this product, cumulative
    r = rr + 3
    ws.cell(row=r, column=1, value='Failure categories — %s (occurrences)' % pr).font = font(True, accent, 12)
    hd = ['Category']
    for p in PROVIDERS:
        hd += ['%s Aug' % p, '%s Sep' % p]
    hd += ['Total Aug', 'Total Sep', 'Cumulative', '% of Cum.']
    header(ws, r + 1, hd, fill=accent, height=42)
    cum_tot = sum(occ(d, None, pr, None) for d in (A, S))
    cats_sorted = sorted(CATS, key=lambda c: -(occ(A, None, pr, c) + occ(S, None, pr, c)))
    for i, c in enumerate(cats_sorted):
        rr = r + 2 + i
        label(ws, rr, 1, c)
        for j, p in enumerate(PROVIDERS):
            formula(ws, rr, 2 + 2 * j, '=' + sumifs(AUG, nA, ins=p, prod=pr, cat=c), occ(A, p, pr, c))
            formula(ws, rr, 3 + 2 * j, '=' + sumifs(SEP, nS, ins=p, prod=pr, cat=c), occ(S, p, pr, c))
        formula(ws, rr, 8, '=B%d+D%d+F%d' % (rr, rr, rr), occ(A, None, pr, c))
        formula(ws, rr, 9, '=C%d+E%d+G%d' % (rr, rr, rr), occ(S, None, pr, c))
        formula(ws, rr, 10, '=H%d+I%d' % (rr, rr), occ(A, None, pr, c) + occ(S, None, pr, c))
        formula(ws, rr, 11, '=J%d/$J$%d' % (rr, r + 14), (occ(A, None, pr, c) + occ(S, None, pr, c)) / cum_tot, '0.0%')
    rr = r + 14
    label(ws, rr, 1, 'TOTAL', total=True)
    for ci in range(2, 11):
        col = 'ABCDEFGHIJ'[ci - 1]
        if ci <= 7:
            p = PROVIDERS[(ci - 2) // 2]; d = [A, S][(ci - 2) % 2]
            v = occ(d, p, pr)
        elif ci == 8: v = occ(A, None, pr)
        elif ci == 9: v = occ(S, None, pr)
        else: v = cum_tot
        formula(ws, rr, ci, '=SUM(%s%d:%s%d)' % (col, r + 2, col, r + 13), v, total=True)
    formula(ws, rr, 11, '=SUM(K%d:K%d)' % (r + 2, r + 13), 1.0, '0.0%', total=True)
    # top reasons cumulative for this product (all carriers)
    r = rr + 3
    ws.cell(row=r, column=1, value='Top 12 failure reasons — %s, cumulative (Aug+Sep)' % pr).font = font(True, accent, 12)
    header(ws, r + 1, ['Error Message', 'Insurer', 'Aug', 'Sep', 'Cumulative', '%% of Cum. %s failures' % pr], fill=accent)
    allr = pd.concat([A['raw'][A['raw']['product'] == pr], S['raw'][S['raw']['product'] == pr]])
    top = allr.groupby(['provider', 'err_n']).occ.sum().sort_values(ascending=False).head(12)
    for k, ((p, e), v) in enumerate(top.items()):
        rr = r + 2 + k
        text(ws, rr, 1, e, wrap=True)
        text(ws, rr, 2, p)
        formula(ws, rr, 3, '=' + sumifs(AUG, nA, ins=Ref('$B%d' % rr), prod=pr, err=Ref('$A%d' % rr)), occ(A, p, pr, err=e))
        formula(ws, rr, 4, '=' + sumifs(SEP, nS, ins=Ref('$B%d' % rr), prod=pr, err=Ref('$A%d' % rr)), occ(S, p, pr, err=e))
        formula(ws, rr, 5, '=C%d+D%d' % (rr, rr), occ(A, p, pr, err=e) + occ(S, p, pr, err=e))
        formula(ws, rr, 6, '=E%d/%d' % (rr, cum_tot), (occ(A, p, pr, err=e) + occ(S, p, pr, err=e)) / cum_tot, '0.0%')
    widths(ws, {'A': 58, 'B': 15, 'C': 13, 'D': 13, 'E': 13, 'F': 13, 'G': 13, 'H': 13, 'I': 13, 'J': 13, 'K': 13})


product_sheet(ws_2w, '2W', '7030A0')
product_sheet(ws_4w, '4W', '7030A0')

# ---------------------------------------------------------------- CUMULATIVE
ws = ws_cum
title(ws, 'Cumulative — August + September 2026',
      'Both months combined for every carrier × product. Aug values are API-derived inputs (blue); Sep values link to the Executive Summary; '
      'category and error counts are SUMIFS across both Raw Data tabs.', 11)
header(ws, 4, ['Carrier × Product', 'Aug Calls', 'Sep Calls', 'Cum. Calls', 'Aug Success', 'Sep Success', 'Cum. Success', 'Cum. Failed', 'Aug Success %', 'Sep Success %', 'Cum. Success %'])
for i, (p, pr) in enumerate(CPS):
    r = 5 + i
    ca, sa = calls(A, p, pr); cs, ss = calls(S, p, pr)
    label(ws, r, 1, '%s — %s' % (p, pr))
    num(ws, r, 2, ca, blue=True)
    formula(ws, r, 3, "='Executive Summary'!B%d" % EXROW[(p, pr)], cs)
    formula(ws, r, 4, '=B%d+C%d' % (r, r), ca + cs)
    num(ws, r, 5, sa, blue=True)
    formula(ws, r, 6, "='Executive Summary'!C%d" % EXROW[(p, pr)], ss)
    formula(ws, r, 7, '=E%d+F%d' % (r, r), sa + ss)
    formula(ws, r, 8, '=D%d-G%d' % (r, r), ca + cs - sa - ss)
    formula(ws, r, 9, '=E%d/B%d' % (r, r), sa / ca, '0.0%')
    formula(ws, r, 10, '=F%d/C%d' % (r, r), ss / cs, '0.0%')
    formula(ws, r, 11, '=G%d/D%d' % (r, r), (sa + ss) / (ca + cs), '0.0%')
r = 11
label(ws, r, 1, 'TOTAL', total=True)
vals_ = [a_calls, tot_calls, a_calls + tot_calls, a_succ, tot_succ, a_succ + tot_succ, a_calls + tot_calls - a_succ - tot_succ]
for ci, v in enumerate(vals_, start=2):
    col = 'ABCDEFGH'[ci - 1]
    formula(ws, r, ci, '=SUM(%s5:%s10)' % (col, col), v, total=True)
formula(ws, r, 9, '=E11/B11', a_succ / a_calls, '0.0%', total=True)
formula(ws, r, 10, '=F11/C11', tot_succ / tot_calls, '0.0%', total=True)
formula(ws, r, 11, '=G11/D11', (a_succ + tot_succ) / (a_calls + tot_calls), '0.0%', total=True)
# categories
r = 14
ws.cell(row=r, column=1, value='Root-cause categories — all carriers and products').font = font(True, '7030A0', 12)
header(ws, r + 1, ['Category', 'Aug', 'Sep', 'Cumulative', '% of Cumulative', 'Δ Sep vs Aug', 'Δ %'], fill='7030A0')
cum_all = sum(cat_tot_s.values()) + sum(cat_tot_a.values())
ordc = sorted(CATS, key=lambda c: -(cat_tot_s[c] + cat_tot_a[c]))
for i, c in enumerate(ordc):
    rr = r + 2 + i
    label(ws, rr, 1, c)
    formula(ws, rr, 2, '=' + sumifs(AUG, nA, cat=Ref('$A%d' % rr)), cat_tot_a[c])
    formula(ws, rr, 3, '=' + sumifs(SEP, nS, cat=Ref('$A%d' % rr)), cat_tot_s[c])
    formula(ws, rr, 4, '=B%d+C%d' % (rr, rr), cat_tot_a[c] + cat_tot_s[c])
    formula(ws, rr, 5, '=D%d/$D$%d' % (rr, r + 14), (cat_tot_a[c] + cat_tot_s[c]) / cum_all, '0.0%')
    formula(ws, rr, 6, '=C%d-B%d' % (rr, rr), cat_tot_s[c] - cat_tot_a[c], '+#,##0;-#,##0;0')
    formula(ws, rr, 7, '=IF(B%d=0,0,F%d/B%d)' % (rr, rr, rr), pct(cat_tot_s[c] - cat_tot_a[c], cat_tot_a[c]), '+0.0%;-0.0%;0.0%')
rr = r + 14
label(ws, rr, 1, 'TOTAL', total=True)
formula(ws, rr, 2, '=SUM(B%d:B%d)' % (r + 2, r + 13), sum(cat_tot_a.values()), total=True)
formula(ws, rr, 3, '=SUM(C%d:C%d)' % (r + 2, r + 13), grand, total=True)
formula(ws, rr, 4, '=SUM(D%d:D%d)' % (r + 2, r + 13), cum_all, total=True)
formula(ws, rr, 5, '=SUM(E%d:E%d)' % (r + 2, r + 13), 1.0, '0.0%', total=True)
formula(ws, rr, 6, '=C%d-B%d' % (rr, rr), grand - sum(cat_tot_a.values()), '+#,##0;-#,##0;0', total=True)
formula(ws, rr, 7, '=F%d/B%d' % (rr, rr), (grand - sum(cat_tot_a.values())) / sum(cat_tot_a.values()), '+0.0%;-0.0%;0.0%', total=True)
# cumulative carrier x product category matrix
r = rr + 3
ws.cell(row=r, column=1, value='Cumulative category × carrier × product (Aug+Sep)').font = font(True, '7030A0', 12)
header(ws, r + 1, ['Category'] + ['%s\n%s' % cp for cp in CPS] + ['Total'], fill='7030A0')
for i, c in enumerate(ordc):
    rr = r + 2 + i
    label(ws, rr, 1, c)
    for j, (p, pr) in enumerate(CPS):
        formula(ws, rr, 2 + j, cum_f(ins=p, prod=pr, cat=Ref('$A%d' % rr)), occ(A, p, pr, c) + occ(S, p, pr, c))
    formula(ws, rr, 8, '=SUM(B%d:G%d)' % (rr, rr), cat_tot_a[c] + cat_tot_s[c])
rr = r + 14
label(ws, rr, 1, 'TOTAL', total=True)
for j, (p, pr) in enumerate(CPS):
    col = 'BCDEFG'[j]
    formula(ws, rr, 2 + j, '=SUM(%s%d:%s%d)' % (col, r + 2, col, r + 13), occ(A, p, pr) + occ(S, p, pr), total=True)
formula(ws, rr, 8, '=SUM(H%d:H%d)' % (r + 2, r + 13), cum_all, total=True)
# top reasons cumulative
r = rr + 3
ws.cell(row=r, column=1, value='Top 20 failure reasons — all carriers, cumulative').font = font(True, '7030A0', 12)
header(ws, r + 1, ['Error Message', 'Insurer', 'Aug', 'Sep', 'Cumulative', '% of Cumulative'], fill='7030A0')
allr = pd.concat([A['raw'], S['raw']]).groupby(['provider', 'err_n']).occ.sum().sort_values(ascending=False).head(20)
for k, ((p, e), v) in enumerate(allr.items()):
    rr = r + 2 + k
    text(ws, rr, 1, e, wrap=True)
    text(ws, rr, 2, p)
    formula(ws, rr, 3, '=' + sumifs(AUG, nA, ins=Ref('$B%d' % rr), err=Ref('$A%d' % rr)), occ(A, p, err=e))
    formula(ws, rr, 4, '=' + sumifs(SEP, nS, ins=Ref('$B%d' % rr), err=Ref('$A%d' % rr)), occ(S, p, err=e))
    formula(ws, rr, 5, '=C%d+D%d' % (rr, rr), occ(A, p, err=e) + occ(S, p, err=e))
    formula(ws, rr, 6, '=E%d/%d' % (rr, cum_all), (occ(A, p, err=e) + occ(S, p, err=e)) / cum_all, '0.0%')
widths(ws, {'A': 58, 'B': 15, 'C': 13, 'D': 13, 'E': 13, 'F': 13, 'G': 13, 'H': 13, 'I': 13, 'J': 13, 'K': 13})

# ================================================================== FINDINGS VS AUGUST
ws = ws_find
title(ws, 'Findings — September 2026 vs August 2026',
      'Month-over-month fact-check. Every number below is a live formula against the Raw Data / Raw Data Aug tabs or the Executive Summary.', 9)
tata2w_s, tata2w_a = calls(S, 'Tata AIG', '2W'), calls(A, 'Tata AIG', '2W')
r = 4
FIND = []
tw = EXROW[('Tata AIG', '2W')]
fnd = [
    ('Finding #1', '"Tata AIG 2W is still the worst-performing endpoint — success rate fell from %.1f%% in August to %.1f%% in September; only %d of %s calls returned a price."'
     % (100 * tata2w_a[1] / tata2w_a[0], 100 * tata2w_s[1] / tata2w_s[0], tata2w_s[1], format(tata2w_s[0], ',')), 'CONFIRMED',
     [('Tata AIG 2W success rate, Sep:', "='Executive Summary'!F%d" % tw, tata2w_s[1] / tata2w_s[0], '0.0%'),
      ('Tata AIG 2W success rate, Aug:', "='Executive Summary'!I%d" % tw, tata2w_a[1] / tata2w_a[0], '0.0%'),
      ('"1182-please provide bundle od start date and bundle od end date", Tata 2W, Sep:', '=' + sumifs(SEP, nS, ins='Tata AIG', prod='2W', err='1182-please provide bundle od start date and bundle od end date'),
       occ(S, 'Tata AIG', '2W', err='1182-please provide bundle od start date and bundle od end date'), '#,##0'),
      ('"Invalid Policy Plan", Tata 2W, Sep:', '=' + sumifs(SEP, nS, ins='Tata AIG', prod='2W', err='Invalid Policy Plan'), occ(S, 'Tata AIG', '2W', err='Invalid Policy Plan'), '#,##0'),
      ('"Invalid Policy Plan", Tata 2W, Aug:', '=' + sumifs(AUG, nA, ins='Tata AIG', prod='2W', err='Invalid Policy Plan'), occ(A, 'Tata AIG', '2W', err='Invalid Policy Plan'), '#,##0')],
     'The weakness is flat across the month (1–6% every day, see Daily Trend), so it is structural, not an incident. Two fixable request defects dominate: missing bundle OD dates '
     'and an unmapped policy plan code.'),
    ('Finding #2', '"Go Digit failures are dominated by \'UW rules violated!!\' — carrier underwriting rejections concentrated on a small set of retried vehicles."', 'CONFIRMED',
     [('"UW rules violated!!" occurrences, Go Digit, Sep:', '=' + sumifs(SEP, nS, ins='Go Digit', err='UW rules violated!!'), occ(S, 'Go Digit', err='UW rules violated!!'), '#,##0'),
      ('"UW rules violated!!" occurrences, Go Digit, Aug:', '=' + sumifs(AUG, nA, ins='Go Digit', err='UW rules violated!!'), occ(A, 'Go Digit', err='UW rules violated!!'), '#,##0'),
      ('Digit success rate, 2W, Sep / Aug (pp change):', "=('Executive Summary'!F%d-'Executive Summary'!I%d)*100" % (EXROW[('Go Digit', '2W')], EXROW[('Go Digit', '2W')]),
       (calls(S, 'Go Digit', '2W')[1] / calls(S, 'Go Digit', '2W')[0] - calls(A, 'Go Digit', '2W')[1] / calls(A, 'Go Digit', '2W')[0]) * 100, '+0.0;-0.0;0.0')],
     'UW rejections fell with call volume: as a share of Digit quote calls they eased from %.1f%% in August to %.1f%% in September, and Digit 2W success improved by %.1f pp.'
     % (100 * occ(A, 'Go Digit', err='UW rules violated!!') / int(A['calls'].loc['Go Digit'].calls.sum()),
        100 * occ(S, 'Go Digit', err='UW rules violated!!') / int(S['calls'].loc['Go Digit'].calls.sum()),
        (calls(S, 'Go Digit', '2W')[1] / calls(S, 'Go Digit', '2W')[0] - calls(A, 'Go Digit', '2W')[1] / calls(A, 'Go Digit', '2W')[0]) * 100)),
    ('Finding #3', '"ICICI Lombard failures are dominated by the single business rule \'TP is not allowed\'."', 'CONFIRMED',
     [('"TP is not allowed" occurrences, ICICI, Sep:', '=' + sumifs(SEP, nS, ins='ICICI Lombard', err='TP is not allowed'), occ(S, 'ICICI Lombard', err='TP is not allowed'), '#,##0'),
      ('...as a share of all ICICI failures, Sep:', '=B%d/' % 0, None, '0.0%'),
      ('"TP is not allowed" occurrences, ICICI, Aug:', '=' + sumifs(AUG, nA, ins='ICICI Lombard', err='TP is not allowed'), occ(A, 'ICICI Lombard', err='TP is not allowed'), '#,##0')],
     'TP-only requests are a carrier rule, not a defect; pre-filtering them before the call would remove roughly three quarters of ICICI\'s failed calls.'),
    ('Finding #4 (new in September)', '"21–22 September: a platform incident produced iHub integration failures across ICICI Lombard, Go Digit and Tata AIG."', 'NEW',
     [('Failed calls with an iHub error signature, Sep (all carriers):', '=' + sumifs(SEP, nS, err='*iHub*'), int(S['raw'][S['raw'].err_n.str.contains('iHub')].occ.sum()), '#,##0'),
      ('iHub error signatures, Aug:', '=' + sumifs(AUG, nA, err='*iHub*'), int(A['raw'][A['raw'].err_n.str.contains('iHub')].occ.sum()), '#,##0')],
     'Almost all of these fall on 21–22 Sept (see System-Technical Errors). The ICICI signature is an unresolved route placeholder (@route.il.host@…), i.e. a configuration '
     'fault; the Digit one is the "outtrf" response-transformation rule. August had none.'),
]
ret_note = None
for tag, claim, verdict, checks, concl in fnd:
    ws.cell(row=r, column=1, value='%s (September analysis)' % tag).font = font(True, 'BF8F00', 12)
    r += 1
    note(ws, r, claim, 6, 32, bold=False)
    r += 1
    label(ws, r, 1, 'Verdict:')
    text(ws, r, 2, verdict, bold=True, color='C00000' if verdict == 'NEW' else '548235')
    r += 1
    first_chk = r
    for lab, f, e, fmt in checks:
        text(ws, r, 1, lab, wrap=True)
        if f.startswith('=B%d/' % 0):
            f = '=B%d/' % (r - 1) + sumifs(SEP, nS, ins='ICICI Lombard')
            e = occ(S, 'ICICI Lombard', err='TP is not allowed') / int(S['calls'].loc['ICICI Lombard'].fail.sum())
        formula(ws, r, 2, f, e, fmt)
        r += 1
    note(ws, r, 'Conclusion: ' + concl, 6, 46, color='595959')
    r += 2
# MoM table of success rates
ws.cell(row=r, column=1, value='Success rate by carrier × product — Sep vs Aug').font = font(True, 'BF8F00', 12)
r += 1
header(ws, r, ['Carrier × Product', 'Aug', 'Sep', 'Δ (pp)'], fill='BF8F00')
for i, (p, pr) in enumerate(CPS):
    rr = r + 1 + i
    label(ws, rr, 1, '%s — %s' % (p, pr))
    formula(ws, rr, 2, "='Executive Summary'!I%d" % EXROW[(p, pr)], calls(A, p, pr)[1] / calls(A, p, pr)[0], '0.0%')
    formula(ws, rr, 3, "='Executive Summary'!F%d" % EXROW[(p, pr)], calls(S, p, pr)[1] / calls(S, p, pr)[0], '0.0%')
    formula(ws, rr, 4, '=(C%d-B%d)*100' % (rr, rr), (calls(S, p, pr)[1] / calls(S, p, pr)[0] - calls(A, p, pr)[1] / calls(A, p, pr)[0]) * 100, '+0.0;-0.0;0.0')
widths(ws, {'A': 62, 'B': 16, 'C': 12, 'D': 12, 'E': 12, 'F': 12})

# ================================================================== DAILY TREND
ws = ws_day
title(ws, 'Daily Trend — quote calls and success rate', 'API-derived daily quote-call volume per carrier (Aug and Sep 2026). Success % is a formula.', 11)
header(ws, 4, ['Date', 'ICICI Calls', 'ICICI Success', 'Digit Calls', 'Digit Success', 'Tata Calls', 'Tata Success', 'Total Calls', 'Total Success', 'Total Success %', 'Failed'])
dd = pd.concat([A['daily'], S['daily']])
dates = sorted(dd.date.unique())
for i, dt in enumerate(dates):
    r = 5 + i
    text(ws, r, 1, dt)
    tc = ts_ = 0
    for j, p in enumerate(PROVIDERS):
        x = dd[(dd.date == dt) & (dd.provider == p)]
        c_, s_ = (int(x.calls.sum()), int(x.succ.sum()))
        num(ws, r, 2 + 2 * j, c_, blue=True)
        num(ws, r, 3 + 2 * j, s_, blue=True)
        tc += c_; ts_ += s_
    formula(ws, r, 8, '=B%d+D%d+F%d' % (r, r, r), tc)
    formula(ws, r, 9, '=C%d+E%d+G%d' % (r, r, r), ts_)
    formula(ws, r, 10, '=IF(H%d=0,0,I%d/H%d)' % (r, r, r), pct(ts_, tc), '0.0%')
    formula(ws, r, 11, '=H%d-I%d' % (r, r), tc - ts_)
lastd = 4 + len(dates)
r = lastd + 1
label(ws, r, 1, 'TOTAL', total=True)
for ci in range(2, 10):
    col = 'ABCDEFGHI'[ci - 1]
    v = int(dd[dd.provider == PROVIDERS[(ci - 2) // 2]][['calls', 'succ'][(ci - 2) % 2]].sum()) if ci <= 7 else (int(dd.calls.sum()) if ci == 8 else int(dd.succ.sum()))
    formula(ws, r, ci, '=SUM(%s5:%s%d)' % (col, col, lastd), v, total=True)
formula(ws, r, 10, '=I%d/H%d' % (r, r), dd.succ.sum() / dd.calls.sum(), '0.0%', total=True)
formula(ws, r, 11, '=H%d-I%d' % (r, r), int(dd.calls.sum() - dd.succ.sum()), total=True)
widths(ws, {'A': 12, 'B': 12, 'C': 12, 'D': 12, 'E': 12, 'F': 12, 'G': 12, 'H': 12, 'I': 12, 'J': 14, 'K': 10})
ws.freeze_panes = 'B5'


# ================================================================== SUMMARY 2W & 4W by PlanType
ws = ws_sum
title(ws, 'Summary — 2W & 4W by PlanType, September 2026',
      'Unique registrations, quote calls, success rate, failures and the major errors (with counts) for each product and PlanType. Section 1 = all carriers; section 2 = by carrier. '
      'Calls, success and unique registrations are API-derived inputs (blue); failures, success rate and error counts are formulas on the Raw Data tab. PlanType codes are as sent by Fibe in the request.', 17)
ws.row_dimensions[2].height = 44
SH = ['Product', 'Carrier', 'PlanType', 'Unique Registrations', 'Quote Calls', 'Success', 'Failures', 'Success Rate', 'Aug Success Rate', 'Δ (pp)', 'Failures (Raw Data check)',
      'Major error #1', 'Count #1', 'Major error #2', 'Count #2', 'Major error #3', 'Count #3']
qS, qA = S['q'], A['q']


def grp(q_, p=None, pr=None, plan=None):
    g = q_
    if p: g = g[g.provider == p]
    if pr: g = g[g['product'] == pr]
    if plan is not None: g = g[g.plantype == plan]
    return g


def raw_occ(p, pr, plan, err=None):
    r_ = S['raw']
    if p: r_ = r_[r_.provider == p]
    if pr: r_ = r_[r_['product'] == pr]
    if plan is not None: r_ = r_[r_.plantype == plan]
    if err is not None: r_ = r_[r_.err_n == err]
    return int(r_.occ.sum())


def sum_row(r, pr, p, plan, total=False):
    g = grp(qS, p, pr, plan); ga = grp(qA, p, pr, plan)
    calls_, succ_ = len(g), int(g.ok.sum())
    label(ws, r, 1, pr, total=total); label(ws, r, 2, p or 'All carriers', total=total); label(ws, r, 3, plan if plan is not None else 'All PlanTypes', total=total)
    num(ws, r, 4, int(g[g.reg != ''].reg.nunique()), blue=True, total=total)
    num(ws, r, 5, calls_, blue=True, total=total); num(ws, r, 6, succ_, blue=True, total=total)
    formula(ws, r, 7, '=E%d-F%d' % (r, r), calls_ - succ_, total=total)
    formula(ws, r, 8, '=IF(E%d=0,0,F%d/E%d)' % (r, r, r), pct(succ_, calls_), '0.0%', total=total)
    if len(ga):
        num(ws, r, 9, float(ga.ok.mean()), '0.0%', blue=True, total=total)
        formula(ws, r, 10, '=(H%d-I%d)*100' % (r, r), (pct(succ_, calls_) - float(ga.ok.mean())) * 100, '+0.0;-0.0;0.0', total=total)
    else:
        text(ws, r, 9, 'n/a'); text(ws, r, 10, 'n/a')
    conds = dict(prod=pr)
    if p: conds['ins'] = p
    if plan is not None: conds['plan'] = plan
    formula(ws, r, 11, '=' + sumifs(SEP, nS, **conds), raw_occ(p, pr, plan), total=total)
    f_ = S['fail']; f_ = f_[f_['product'] == pr]
    if p: f_ = f_[f_.provider == p]
    if plan is not None: f_ = f_[f_.plantype == plan]
    top = f_.groupby('err_n').size().sort_values(ascending=False).head(3)
    for k in range(3):
        if k < len(top):
            e_ = top.index[k]
            text(ws, r, 12 + 2 * k, e_, wrap=True)
            formula(ws, r, 13 + 2 * k, '=' + sumifs(SEP, nS, err=Ref('%s%d' % ('LNP'[k], r)), **conds), raw_occ(p, pr, plan, e_))
        else:
            text(ws, r, 12 + 2 * k, '—'); text(ws, r, 13 + 2 * k, '')


r = 4
ws.cell(row=r, column=1, value='1. All carriers — by product and PlanType').font = font(True, '7030A0', 12)
r += 1
header(ws, r, SH, fill='7030A0', height=42)
r += 1
for pr in ('2W', '4W'):
    plans = sorted(set(qS[qS['product'] == pr].plantype), key=lambda z: int(z) if str(z).isdigit() else 99)
    for plan in plans:
        sum_row(r, pr, None, plan); r += 1
    sum_row(r, pr, None, None, total=True); r += 1
r += 1
ws.cell(row=r, column=1, value='2. By carrier — product and PlanType').font = font(True, '7030A0', 12)
r += 1
header(ws, r, SH, fill='7030A0', height=42)
r += 1
for p_ in PROVIDERS:
    for pr in ('2W', '4W'):
        plans = sorted(set(qS[(qS.provider == p_) & (qS['product'] == pr)].plantype), key=lambda z: int(z) if str(z).isdigit() else 99)
        for plan in plans:
            sum_row(r, pr, p_, plan); r += 1
        sum_row(r, pr, p_, None, total=True); r += 1
r += 1
note(ws, r, 'Unique registrations in a TOTAL row are distinct vehicles for that scope, so they can be lower than the sum of the PlanType rows (a vehicle may be quoted under more than one PlanType). '
     'Failures are failed quote calls; Success Rate = successful calls ÷ quote calls. Major errors are the three most frequent normalised errors for that row.', 17, 44, color='595959')
widths(ws, {'A': 9, 'B': 15, 'C': 13, 'D': 13, 'E': 11, 'F': 11, 'G': 10, 'H': 10, 'I': 11, 'J': 9, 'K': 13, 'L': 46, 'M': 9, 'N': 46, 'O': 9, 'P': 46, 'Q': 9})
ws.freeze_panes = 'D6'
SUMLAST = r


# ================================================================== ERROR BIFURCATION: Insurer x Product x PlanType x Error
ws = ws_bif
bif = (S['raw'][S['raw'].reg_disp != ''].groupby(['provider', 'product', 'plantype', 'err_n', 'cat'])
       .agg(o=('occ', 'sum'), regs=('reg_disp', lambda s_: s_[s_ != '(blank)'].nunique())).reset_index())
bif['pn'] = bif.plantype.map(lambda z: int(z) if str(z).isdigit() else 99)
bif['po'] = bif.provider.map({p_: i_ for i_, p_ in enumerate(PROVIDERS)})
bif = bif.sort_values(['po', 'product', 'pn', 'o'], ascending=[True, True, True, False]).reset_index(drop=True)
title(ws, 'Error Bifurcation — Insurer × Product × PlanType × Error (September 2026)',
      'Every distinct failed-call error for each insurer, product and PlanType. Occurrences are live SUMIFS on the Raw Data tab; "% of PlanType failures" divides by the failures of the same insurer, product and PlanType; '
      'August occurrences come from Raw Data Aug. Use the filters on the header row to slice (e.g. Insurer = Tata AIG, Product = 2W, PlanType = 3).', 11)
ws.row_dimensions[2].height = 44
header(ws, 4, ['Insurer', 'Product', 'PlanType', 'Error', 'Category', 'Occurrences (Sep)', 'Unique Vehicles', '% of PlanType failures', 'PlanType failures (Sep)', 'Occurrences (Aug)', 'Δ vs Aug'], height=42)
ptot = S['raw'].groupby(['provider', 'product', 'plantype']).occ.sum()
BIF0 = 5
for i, x in enumerate(bif.itertuples(index=False)):
    r = BIF0 + i
    text(ws, r, 1, x.provider); text(ws, r, 2, x.product); text(ws, r, 3, str(x.plantype)); text(ws, r, 4, x.err_n, wrap=False); text(ws, r, 5, x.cat)
    conds = dict(ins=Ref('$A%d' % r), prod=Ref('$B%d' % r), plan=Ref('$C%d' % r), err=Ref('$D%d' % r))
    formula(ws, r, 6, '=' + sumifs(SEP, nS, **conds), int(x.o))
    num(ws, r, 7, int(x.regs))
    pt = int(ptot[(x.provider, x.product, x.plantype)])
    formula(ws, r, 8, '=F%d/I%d' % (r, r), x.o / pt, '0.0%')
    formula(ws, r, 9, '=' + sumifs(SEP, nS, ins=Ref('$A%d' % r), prod=Ref('$B%d' % r), plan=Ref('$C%d' % r)), pt)
    ao = int(A['raw'][(A['raw'].provider == x.provider) & (A['raw']['product'] == x.product) & (A['raw'].plantype == x.plantype) & (A['raw'].err_n == x.err_n)].occ.sum())
    formula(ws, r, 10, '=' + sumifs(AUG, nA, **conds), ao)
    formula(ws, r, 11, '=F%d-J%d' % (r, r), int(x.o) - ao, '+#,##0;-#,##0;0')
BIFN = BIF0 + len(bif) - 1
r = BIFN + 1
label(ws, r, 1, 'TOTAL', total=True)
for c_ in range(2, 6): text(ws, r, c_, '', fill=TOTAL_FILL)
formula(ws, r, 6, '=SUM(F%d:F%d)' % (BIF0, BIFN), int(bif.o.sum()), total=True)
for c_ in (7, 8, 9): text(ws, r, c_, '', fill=TOTAL_FILL)
text(ws, r, 10, '', fill=TOTAL_FILL); text(ws, r, 11, '', fill=TOTAL_FILL)
BIFTOT = r
note(ws, r + 2, 'Aug occurrences are shown per error; errors that occurred only in August are not listed here (see Raw Data Aug and the Findings tab).', 11, 30, color='595959')
widths(ws, {'A': 14, 'B': 9, 'C': 10, 'D': 70, 'E': 28, 'F': 14, 'G': 11, 'H': 13, 'I': 14, 'J': 13, 'K': 10})
ws.freeze_panes = 'E5'
ws.auto_filter.ref = 'A4:K%d' % BIFN

# ================================================================== DATA VERIFICATION
ws = ws_ver
title(ws, 'Data Verification — reconciliation checks',
      'Independent checks run on this workbook. "Expected" is the figure from an independent source (API row counts, the August deck/workbook, or another tab); '
      '"Actual" is read from this workbook. Status = PASS when they agree.', 6)
header(ws, 4, ['Check', 'Expected', 'Actual', 'Status', 'Source of "Expected"'])
sepm = json_summary = None
import json
sumS = json.load(open('raw_2026-09/summary.json')); sumA = json.load(open('raw_2026-08/summary.json'))
checks = [
    ('Sep: transactions downloaded = API total for 2026/09/01–2026/09/30', 91959, sum(v[1] for v in sumS.values()), 'queryTransactionPaged TotalElements (single range query), blue'),
    ('Sep: distinct ListIds = rows (no duplicates / gaps)', sum(v[1] for v in sumS.values()), sum(v[2] for v in sumS.values()), 'Per-day download log'),
    ('Aug: transactions downloaded = API total for 2026/08/01–2026/08/31', 146995, sum(v[1] for v in sumA.values()), 'queryTransactionPaged TotalElements, blue'),
    ('Sep: Failed (Summary) = Failed (Raw Data check), all carriers', '=\'Executive Summary\'!D11', "='Executive Summary'!E11", 'Executive Summary'),
    ('Sep: Category Breakdown total = Raw Data occurrences', "=SUM('Raw Data'!F2:F%d)" % (nS + 1), "='Category Breakdown'!H17", 'Raw Data tab'),
    ('Sep: ICICI deep-dive 2W+4W = Executive Summary failed', "='Executive Summary'!D5+'Executive Summary'!D6", None, 'Executive Summary'),
    ('Sep: Go Digit deep-dive 2W+4W = Executive Summary failed', "='Executive Summary'!D7+'Executive Summary'!D8", None, 'Executive Summary'),
    ('Sep: Tata AIG deep-dive 2W+4W = Executive Summary failed', "='Executive Summary'!D9+'Executive Summary'!D10", None, 'Executive Summary'),
    ('Sep: Retry-tab share base = total failed (all failures incl. blank reg)', "='Executive Summary'!D11", len(S['fail']), 'Executive Summary'),
    ('Cum: Cumulative failed (calls − success) = Cumulative category total', "='Cumulative (Aug+Sep)'!H11", None, 'Cumulative tab'),
    ('Cum: 2W + 4W cumulative calls = Cumulative total calls', "='Cumulative (Aug+Sep)'!D11", None, 'Cumulative tab'),
    ('Policies: Policy Issuance total = Funnel & GWP total (Aug+Sep)', None, None, 'Funnel & GWP'),
    ('Digit: every Digit policy has BOTH PolicyNo and CarrierPolicyNo', int((allpol.provider == 'Go Digit').sum()), None, 'Policy Issuance detail'),
    ('Summary 2W & 4W: failures (all carriers, all PlanTypes) = Executive Summary failed', "='Executive Summary'!D11", None, 'Executive Summary'),
    ('Error Bifurcation: Sep occurrences total = Raw Data occurrences', None, None, 'Raw Data tab'),
    ('Aug (calibration): quote calls vs August MBR deck (146,324)', 146324, "='Cumulative (Aug+Sep)'!B11", 'FIBE x insureMO MBR August 2026 v2, slide 6'),
    ('Aug (calibration): failed calls vs August MBR deck (63,023)', 63023, "='Cumulative (Aug+Sep)'!B11-'Cumulative (Aug+Sep)'!E11", 'MBR August deck, slide 6'),
    ('Aug (calibration): ICICI failed calls vs deck (10,766)', 10766, "=SUM('Cumulative (Aug+Sep)'!B5:B6)-SUM('Cumulative (Aug+Sep)'!E5:E6)", 'MBR August deck, slide 9'),
    ('Aug (calibration): Go Digit failed calls vs deck (21,611)', 21611, "=SUM('Cumulative (Aug+Sep)'!B7:B8)-SUM('Cumulative (Aug+Sep)'!E7:E8)", 'MBR August deck, slide 9'),
    ('Aug (calibration): Tata AIG failed calls vs deck (30,646)', 30646, "=SUM('Cumulative (Aug+Sep)'!B9:B10)-SUM('Cumulative (Aug+Sep)'!E9:E10)", 'MBR August deck, slide 9'),
    ('Aug (calibration): policies issued vs deck (59)', 59, '=' + pol_f('count', None, '2026-08'), 'MBR August deck, slide 3'),
    ('Aug (calibration): GWP vs deck (INR 1,27,793, rounded)', 127793, '=ROUND(' + pol_f('sum', None, '2026-08') + ',0)', 'MBR August deck, slide 3'),
    ('Aug (calibration): applications vs deck (242)', 242, "='Funnel & GWP'!H%d" % FROW['apps'], 'MBR August deck, slide 3'),
    ('Aug (calibration): unique registrations vs deck (4,935)', 4935, "='Funnel & GWP'!H%d" % FROW['leads'], 'MBR August deck, slide 3'),
]
tot_cum_failed = int(a_calls + tot_calls - a_succ - tot_succ)
for i, (lab, e, a, srcx) in enumerate(checks):
    r = 5 + i
    text(ws, r, 1, lab, wrap=True)
    # expected
    if isinstance(e, str):
        formula(ws, r, 2, e, None)
    elif e is None:
        pass
    else:
        num(ws, r, 2, e, blue=True)
    if isinstance(a, str):
        formula(ws, r, 3, a, None)
    elif a is None:
        pass
    else:
        num(ws, r, 3, a, blue=False)
    text(ws, r, 5, srcx, wrap=True)
    c = ws.cell(row=r, column=4)
    c.value = '=IF(ABS(B%d-C%d)<0.5,"PASS","FAIL")' % (r, r)
    c.font = font(True)
    c.alignment = Alignment(horizontal='center')
    c.border = BORDER
    EXPECTED[(ws.title, c.coordinate)] = 'PASS'
CHK = {lab: 5 + i for i, (lab, *_rest) in enumerate(checks)}


def setf(label_, col, f, e, fmt='#,##0'):
    r = CHK[label_]
    formula(ws, r, col, f, e, fmt)


setf('Sep: ICICI deep-dive 2W+4W = Executive Summary failed', 3, "=SUM('ICICI Lombard'!B%d,'ICICI Lombard'!D%d)" % ((5 + len(cats_for('ICICI Lombard')),) * 2), int(S['calls'].loc['ICICI Lombard'].fail.sum()))
setf('Sep: Go Digit deep-dive 2W+4W = Executive Summary failed', 3, "=SUM('Go Digit'!B%d,'Go Digit'!D%d)" % ((5 + len(cats_for('Go Digit')),) * 2), int(S['calls'].loc['Go Digit'].fail.sum()))
setf('Sep: Tata AIG deep-dive 2W+4W = Executive Summary failed', 3, "=SUM('Tata AIG'!B%d,'Tata AIG'!D%d)" % ((5 + len(cats_for('Tata AIG')),) * 2), int(S['calls'].loc['Tata AIG'].fail.sum()))
setf('Cum: Cumulative failed (calls − success) = Cumulative category total', 3, "='Cumulative (Aug+Sep)'!D%d" % (14 + 14), tot_cum_failed)
setf('Cum: 2W + 4W cumulative calls = Cumulative total calls', 3, "='2W'!D8+'4W'!D8", int(a_calls + tot_calls))
setf('Summary 2W & 4W: failures (all carriers, all PlanTypes) = Executive Summary failed', 3, "=SUMIFS('Summary 2W & 4W'!$G$6:$G$%d,'Summary 2W & 4W'!$C$6:$C$%d,\"All PlanTypes\",'Summary 2W & 4W'!$B$6:$B$%d,\"All carriers\")" % ((SUMLAST,) * 3), len(S['fail']))
EXPECTED[(ws.title, 'B%d' % CHK['Summary 2W & 4W: failures (all carriers, all PlanTypes) = Executive Summary failed'])] = len(S['fail'])
setf('Error Bifurcation: Sep occurrences total = Raw Data occurrences', 2, "=SUM('Raw Data'!$F$2:$F$%d)" % (nS + 1), int(bif.o.sum()))
setf('Error Bifurcation: Sep occurrences total = Raw Data occurrences', 3, "='Error Bifurcation'!F%d" % BIFTOT, int(bif.o.sum()))
setf('Policies: Policy Issuance total = Funnel & GWP total (Aug+Sep)', 2, "='Policy Issuance'!C%d" % POL_TOT_ROW, n_pol)
setf('Policies: Policy Issuance total = Funnel & GWP total (Aug+Sep)', 3, "='Funnel & GWP'!H%d+'Funnel & GWP'!I%d" % (FROW['policies'], FROW['policies']), n_pol)
setf('Digit: every Digit policy has BOTH PolicyNo and CarrierPolicyNo', 3,
     "=COUNTIFS('Policy Issuance'!$B$%d:$B$%d,\"Go Digit\",'Policy Issuance'!$G$%d:$G$%d,\"<>\",'Policy Issuance'!$H$%d:$H$%d,\"<>\")" % (first, last, first, last, first, last),
     int(((allpol.provider == 'Go Digit') & (allpol.policy_no != '') & (allpol.carrier_policy_no != '')).sum()))
# fix None expecteds for checks whose expected were formulas
for lab, e in [('Sep: Failed (Summary) = Failed (Raw Data check), all carriers', len(S['fail'])),
               ('Sep: Category Breakdown total = Raw Data occurrences', int(S['raw'].occ.sum()))]:
    EXPECTED[(ws.title, 'B%d' % CHK[lab])] = e
    EXPECTED[(ws.title, 'C%d' % CHK[lab])] = e
for lab, e in [('Sep: ICICI deep-dive 2W+4W = Executive Summary failed', int(S['calls'].loc['ICICI Lombard'].fail.sum())),
               ('Sep: Go Digit deep-dive 2W+4W = Executive Summary failed', int(S['calls'].loc['Go Digit'].fail.sum())),
               ('Sep: Tata AIG deep-dive 2W+4W = Executive Summary failed', int(S['calls'].loc['Tata AIG'].fail.sum()))]:
    EXPECTED[(ws.title, 'B%d' % CHK[lab])] = e
EXPECTED[(ws.title, 'B%d' % CHK['Sep: Retry-tab share base = total failed (all failures incl. blank reg)'])] = len(S['fail'])
EXPECTED[(ws.title, 'B%d' % CHK['Cum: Cumulative failed (calls − success) = Cumulative category total'])] = tot_cum_failed
EXPECTED[(ws.title, 'B%d' % CHK['Cum: 2W + 4W cumulative calls = Cumulative total calls'])] = int(a_calls + tot_calls)
widths(ws, {'A': 66, 'B': 14, 'C': 14, 'D': 10, 'E': 52})
ws.freeze_panes = 'A5'

# ================================================================== READ ME
ws = ws_readme
ws['A1'] = 'Fibe — September 2026 Carrier Error Analysis'
ws['A1'].font = font(True, NAVY, 16)
ws['A2'] = 'Quote-failure diagnostics across ICICI Lombard, Go Digit and Tata AIG (2W & 4W), plus policy issuance — prepared for internal review. Data extracted from the InsureMO transaction log.'
ws['A2'].font = font(False, '595959')
ws.sheet_view.showGridLines = False
lines = [
    ('WHAT THIS WORKBOOK IS', None),
    (None, 'This workbook analyses every quote-generation call logged in September 2026 (2026/09/01–2026/09/30) across the three motor carriers Fibe integrates with, for 2W and 4W.'),
    (None, 'Unlike the August workbook (built from a supplied file), the data here was pulled directly from the InsureMO integration-adapter API (queryTransactionPaged), filtered by date range,'),
    (None, 'day by day: %s transactions, reconciled to the API\'s own total. The identical extraction was re-run for August and reproduces the August deck/workbook (see Data Verification).' % format(91959, ',')),
    ('HOW TO READ IT', None),
    (None, '1. Executive Summary — carrier × product call volume, success and failure, with the August comparison.'),
    (None, '2. Category Breakdown — failed calls rolled up into 12 root-cause categories (live SUMIFS on Raw Data).'),
    (None, '3. ICICI Lombard / Go Digit / Tata AIG — one deep-dive per carrier: category mix, top failure reasons, analyst notes.'),
    (None, '4. 2W / 4W — NEW: carrier comparison per product, Aug vs Sep vs cumulative, with categories, issuance and top reasons.'),
    (None, '5. Cumulative (Aug+Sep) — NEW: both months combined for every carrier × product, category and error.'),
    (None, '6. Policy Issuance — NEW: every issued policy. Go Digit shows PolicyNo AND CarrierPolicyNo; ICICI Lombard / Tata AIG show CarrierPolicyNo only.'),
    (None, '7. Funnel & GWP — NEW: leads → price → application → policy and GWP, Aug vs Sep, by carrier.'),
    (None, '8. Retry & Cross-Carrier — registrations retried hardest and those failing at all three carriers.'),
    (None, '9. System-Technical Errors — pure infrastructure/integration faults (incl. the 21–22 Sept iHub incident).'),
    (None, '10. Findings vs August — month-over-month fact-check of the headline findings.'),
    (None, '11. Daily Trend / Data Verification — day-level volumes and the reconciliation checks. 12. Raw Data (Sep) and Raw Data Aug — the rows every formula reads.'),
    ('KEY DEFINITIONS', None),
    (None, 'Total calls = quick-quote (1001) and, for Tata AIG 4W, compare-quote (4001) requests logged in the month. Success = a premium came back with no error.'),
    (None, 'Product = request ProductType (2 = 2W, 1 = 4W). Occurrences = number of times an (Insurer, Registration, Product, PlanType, Error) combination recurred.'),
    (None, 'Category = root-cause grouping on normalised error strings (registration numbers, policy numbers, trace ids and timestamps stripped so identical errors aggregate).'),
    (None, 'Policy issued: ICICI Lombard = proposal response with a CarrierPolicyNo; Tata AIG = issue-policy response with a CarrierPolicyNo; Go Digit = issue-policy response with BOTH a carrier'),
    (None, 'PolicyNo and a CarrierPolicyNo (Digit\'s create-quote also returns a CarrierPolicyNo, which is only a quote id). GWP = premium on those policies.'),
    ('NOTES & CAVEATS', None),
    (None, 'July 2026 is not compared: the API holds July only from 5 July and its figures do not reconcile to the July numbers in the August deck. September is compared with August, which does.'),
    (None, 'August category totals reproduce the August workbook exactly for 9 of 12 categories; the other three differ by ≤0.2% of failures because Digit date-format parse errors are now Invalid Input Value.'),
    (None, 'Aug raw detail differs from the August workbook by 6 occurrences (63,023 vs 63,029) — the same discrepancy the August workbook footnotes between its Summary and detail tabs.'),
    (None, 'Digit and Tata policy statuses: 3 Digit policies in Sep (1 in Aug) are UW_REFFERED (referred to underwriting). They are counted as policies for like-for-like comparison with the August deck.'),
]
r = 4
for h, t in lines:
    if h:
        r += 1
        ws.cell(row=r, column=1, value=h).font = font(True, NAVY, 12)
    else:
        ws.cell(row=r, column=2, value=t).font = font()
    r += 1
widths(ws, {'A': 22, 'B': 14})
for c in 'CDEFGH':
    ws.column_dimensions[c].width = 14

wb.save(OUT)
pickle.dump(EXPECTED, open('xl_expected.pkl', 'wb'))
print('saved', OUT, 'formula cells', len(EXPECTED))
