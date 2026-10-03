# ---- part b (exec'd from build_deck.py) ----
def carrier_rows(p):
    f_a, f_s = fa[p], fs[p]
    ap = lambda f: f['gwp'] / f['policies']
    return [[None, 'August 2026', 'September 2026', None]] + [
        ['Registrations attempted', ind(f_a['leads']), ind(f_s['leads']), chg(f_s['leads'], f_a['leads'])],
        ['Leads with a price', ind(f_a['priced']), ind(f_s['priced']), chg(f_s['priced'], f_a['priced'])],
        ['Lead → price %', '%.1f%%' % (100 * L(f_a)), '%.1f%%' % (100 * L(f_s)), chgpp(L(f_s), L(f_a))],
        ['Applications', ind(f_a['apps']), ind(f_s['apps']), chg(f_s['apps'], f_a['apps'])],
        ['Policies issued', ind(f_a['policies']), ind(f_s['policies']), chg(f_s['policies'], f_a['policies'])],
        ['GWP (INR)', ind(f_a['gwp']), ind(f_s['gwp']), chg(f_s['gwp'], f_a['gwp'])],
        ['Average premium (INR)', ind(ap(f_a)), ind(ap(f_s)), chg(ap(f_s), ap(f_a))],
        ['Share of GWP %', '%.0f%%' % (100 * shr(fa, p)), '%.0f%%' % (100 * shr(fs, p)), chgpp(shr(fs, p), shr(fa, p), 1)],
        ['Quote calls', ind(f_a['calls']), ind(f_s['calls']), chg(f_s['calls'], f_a['calls'])],
        ['Failed calls', ind(fail_(fa, p)), ind(fail_(fs, p)), chg(fail_(fs, p), fail_(fa, p))]]


def carrier_good(rows):
    g = {}
    for r in range(1, 11):
        g[(r, 3)] = arrow(rows[r][3], r != 10)
    return g



def apps_by(d, p, prod):
    a_ = d['apps']
    return int(a_[(a_.provider == p) & (a_['product'] == prod)].reg.nunique())


def carrier_rows_pw(p):
    """metrics by 2W / 4W / Total, each cell 'Aug -> Sep (change)'"""
    def cellv(av, sv, fmt=ind, pp=False):
        if pp:
            return '%s → %s  (%s)' % (fmt(av), fmt(sv), chgpp(sv, av) if av is not None else '—')
        return '%s → %s  (%s)' % (fmt(av), fmt(sv), chg(sv, av) if av else '—')
    pct1 = lambda x: '%.1f%%' % (100 * x)
    rows = [[None, '2W: Aug → Sep', '4W: Aug → Sep', 'Total: Aug → Sep']]
    cols = []
    for prod in ('2W', '4W', 'Total'):
        if prod == 'Total':
            xa, xs = fa[p], fs[p]
            ap_a, ap_s = fa[p]['apps'], fs[p]['apps']
            pa_, ps_ = fa[p]['policies'], fs[p]['policies']
            ga, gs = fa[p]['gwp'], fs[p]['gwp']
        else:
            xa, xs = PS['A'][prod][p], PS['S'][prod][p]
            ap_a, ap_s = apps_by(AD, p, prod), apps_by(SD, p, prod)
            pa_, ps_ = xa['pol'], xs['pol']
            ga, gs = xa['gwp'], xs['gwp']
        lead_a, lead_s = xa['leads'], xs['leads']
        pr_a, pr_s = xa['priced'], xs['priced']
        c_a, c_s = xa['calls'], xs['calls']
        su_a, su_s = xa['succ'], xs['succ']
        cols.append([
            cellv(lead_a, lead_s), cellv(pr_a, pr_s), cellv(pr_a / lead_a, pr_s / lead_s, pct1, True),
            cellv(ap_a, ap_s), cellv(pa_, ps_), cellv(ga, gs),
            (cellv(ga / pa_, gs / ps_) if pa_ and ps_ else ('—' if not ps_ else '— → %s' % ind(gs / ps_))),
            cellv(su_a / c_a, su_s / c_s, pct1, True), cellv(c_a, c_s), cellv(c_a - su_a, c_s - su_s)])
    labels = ['Registrations attempted', 'Leads with a price', 'Lead → price %', 'Applications', 'Policies issued', 'GWP (INR)',
              'Average premium (INR)', 'Call success %', 'Quote calls', 'Failed calls']
    for i, lab in enumerate(labels):
        rows.append([lab, cols[0][i], cols[1][i], cols[2][i]])
    return rows


def fill_pw(i, k, p):
    t = sh(i, k).table
    rows = carrier_rows_pw(p)
    fill_table(t, rows)
    wd = [1330000, 1780000, 1780000, 1780000]
    for c, w in zip(t.columns, wd):
        c.width = w
    recolor_arrows(t, {1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: True, 8: True, 9: False, 10: False}, skip_cols=(0,))
    for r in range(1, 11):
        for c in range(1, 4):
            for run in t.cell(r, c).text_frame.paragraphs[0].runs:
                run.font.size = Pt(7.5)
                run.font.bold = False


def top_cnt(p, err):
    return int(SD['fail'][(SD['fail'].provider == p) & (SD['fail'].err_n == err)].shape[0])


# ---------------- slide 13 divider
T(13, 3, 'One page per carrier, September against August')
# ---------------- slide 14 ICICI
p = il_
T(14, 1, 'Carrier deep dive — September 2026 against August')
T(14, 6, str(fs[p]['policies'])); T(14, 7, 'Policies in September'); TC(14, 8, '%d in August, down %s' % (fa[p]['policies'], chg(fs[p]['policies'], fa[p]['policies'])[2:]), False)
T(14, 10, 'INR ' + ind(fs[p]['gwp'])); T(14, 11, 'GWP in September'); T(14, 12, '%.0f%% of the book' % (100 * shr(fs, p)))
T(14, 14, '%.1f%%' % (100 * L(fs[p]))); T(14, 15, 'Leads priced'); TC(14, 16, '%.1f%% in August' % (100 * L(fa[p])), L(fs[p]) >= L(fa[p]))
T(14, 18, '%.1f' % s['calls_reg'][p]); T(14, 19, 'Calls per registration'); T(14, 20, 'Still the highest')
fill_pw(14, 21, p)
tp = top_cnt(p, 'TP is not allowed'); nsm = top_cnt(p, 'java.lang.NoSuchMethodError')
ilf = SD['fail'][SD['fail'].provider == p]
T(14, 24, ['▪   Lead → price held at %.1f%% (Aug %.1f%%)' % (100 * L(fs[p]), 100 * L(fa[p])),
           '▪   4W call success steady at %.1f%%' % (100 * SD['calls'].loc[(p, '4W')].succ / SD['calls'].loc[(p, '4W')].calls),
           '▪   Highest volume of any carrier: %s calls' % ind(fs[p]['calls']),
           '▪   Failures fell with volume: %s vs %s' % (ind(fail_(fs, p)), ind(fail_(fa, p)))])
T(14, 27, ['▪   %d policies from %d applications; %d of %d proposals at KYC PENDING' % (fs[p]['policies'], fs[p]['apps'], il_kyc, il_prop_n),
           '▪   GWP down %s to INR %s (%.0f%% of the book)' % (chg(fs[p]['gwp'], fa[p]['gwp'])[2:], ind(fs[p]['gwp']), 100 * shr(fs, p)),
           '▪   "TP is not allowed": %s calls, %.0f%% of failures (carrier rule)' % (ind(tp), 100 * tp / fail_(fs, p)),
           '▪   Platform faults: %d iHub, %d NoSuchMethod' % (len(ilf[ilf.err_n.str.contains('iHub')]), nsm)])
T(14, 28, 'ICICI\'s funnel broke at application → policy. Clearing KYC pending (cKYC with OTP, on hold) is the lever.')

# ---------------- slide 15 Digit
p = dg_
T(15, 1, 'Carrier deep dive — September 2026 against August')
T(15, 6, str(fs[p]['policies'])); T(15, 7, 'Policies in September'); T(15, 8, '%d in August' % fa[p]['policies'])
T(15, 10, 'INR ' + ind(fs[p]['gwp'])); T(15, 11, 'GWP in September'); T(15, 12, '%.0f%% → %.0f%% of the book' % (100 * shr(fa, p), 100 * shr(fs, p)))
T(15, 14, '%.1f%%' % (100 * L(fs[p]))); T(15, 15, 'Leads priced'); TC(15, 16, '%.1f%% in August' % (100 * L(fa[p])), L(fs[p]) >= L(fa[p]))
T(15, 18, '%.1f' % (fs[p]['apps'] / fs[p]['policies'])); T(15, 19, 'Applications per policy'); T(15, 20, '%.1f in August' % (fa[p]['apps'] / fa[p]['policies']))
fill_pw(15, 21, p)
uw = top_cnt(p, 'UW rules violated!!'); dgl = SD['fail'][SD['fail'].provider == p]
outt = int(dgl.err_n.str.contains('outtrf').sum())
rto = top_cnt(p, 'Invalid RTO identified from registration number (see RegistrationNo column)')
far = top_cnt(p, 'Quote creation cannot be possible as inception date of the policy is more than6 months in future')
polS_dg = SD['pol'][SD['pol'].provider == p]
T(15, 24, ['▪   GWP up %s to INR %s, now the biggest premium contributor' % (chg(fs[p]['gwp'], fa[p]['gwp'])[2:], ind(fs[p]['gwp'])),
           '▪   Highest average ticket after Tata: INR %s' % ind(avgp(fs, p)),
           '▪   Lead → price improved %.1f%% → %.1f%%' % (100 * L(fa[p]), 100 * L(fs[p])),
           '▪   Both 2W (%.1f%%) and 4W (%.1f%%) call success rose' % (100 * SD['calls'].loc[(p, '2W')].succ / SD['calls'].loc[(p, '2W')].calls, 100 * SD['calls'].loc[(p, '4W')].succ / SD['calls'].loc[(p, '4W')].calls)])
T(15, 27, ['▪   Policies %d → %d; applications per policy %.1f → %.1f' % (fa[p]['policies'], fs[p]['policies'], fa[p]['apps'] / fa[p]['policies'], fs[p]['apps'] / fs[p]['policies']),
           '▪   UW rules rejected %s calls (%.0f%%)' % (ind(uw), 100 * uw / fail_(fs, p)),
           '▪   %d calls hit the iHub "outtrf" rule fault (platform)' % outt,
           '▪   Fibe-fixable: RTO %d, far-future dates %d' % (rto, far)])
T(15, 28, 'Issued = PolicyNo and CarrierPolicyNo both returned; %d of %d Sept policies are UW_REFFERED (see workbook).' % (int((polS_dg.policy_status == 'UW_REFFERED').sum()), len(polS_dg)))

# ---------------- slide 16 Tata
p = ta_
T(16, 1, 'Carrier deep dive — September 2026 against August')
T(16, 6, str(fs[p]['policies'])); T(16, 7, 'Policies in September'); T(16, 8, '%d in August' % fa[p]['policies'])
T(16, 10, 'INR ' + ind(fs[p]['gwp'])); T(16, 11, 'GWP in September'); TC(16, 12, '%s on August' % chg(fs[p]['gwp'], fa[p]['gwp']), False)
T(16, 14, 'INR ' + ind(avgp(fs, p))); T(16, 15, 'Average premium'); T(16, 16, 'Highest of the three')
T(16, 18, '%.1f%%' % (100 * L(fs[p]))); T(16, 19, 'Leads priced'); TC(16, 20, '%.1f%% in August' % (100 * L(fa[p])), L(fs[p]) >= L(fa[p]))
fill_pw(16, 21, p)
bund = top_cnt(p, '1182-please provide bundle od start date and bundle od end date'); eso = top_cnt(p, 'engine_secure_options  is mandatory.'); ipp = top_cnt(p, 'Invalid Policy Plan')
t2 = SD['calls'].loc[(p, '2W')]; t4 = SD['calls'].loc[(p, '4W')]
T(16, 24, ['▪   Richest ticket: INR %s against a book average of %s' % (ind(avgp(fs, p)), ind(avg_s)),
           '▪   %d policies from %d applications — best close rate (%.0f%%) of the three' % (fs[p]['policies'], fs[p]['apps'], 100 * conv(fs[p])) if conv(fs[p]) >= max(conv(fs[x]) for x in P3) else '▪   %d policies from %d applications' % (fs[p]['policies'], fs[p]['apps']),
           '▪   4W call success improved %.1f%% → %.1f%%' % (100 * AD['calls'].loc[(p, '4W')].succ / AD['calls'].loc[(p, '4W')].calls, 100 * t4.succ / t4.calls),
           '▪   Still delivered INR %s GWP despite the failures' % ind(fs[p]['gwp'])])
T(16, 27, ['▪   Only %.1f%% of leads got a price' % (100 * L(fs[p])),
           '▪   2W call success %.1f%% (%d of %s); Aug 18.0%%' % (100 * t2.succ / t2.calls, t2.succ, ind(t2.calls)),
           '▪   %s malformed requests: bundle OD dates %s, engine options %s' % (ind(bund + eso), ind(bund), ind(eso)),
           '▪   "Invalid Policy Plan" %s (Aug %d) — plan-code mapping'  % (ind(ipp), int(AD['fail'][(AD['fail'].provider == p) & (AD['fail'].err_n == 'Invalid Policy Plan')].shape[0]))])
T(16, 28, 'Tata AIG 2W is the clearest fix: %.1f%% success, flat all month, driven by request/mapping defects we control.' % (100 * t2.succ / t2.calls))

# ---------------- slide 17 divider
T(17, 3, 'Why September happened')

# ---------------- slide 18 new vs repeat
nr = M['newrep']
na, ra = nr['A']; ns, rs = nr['S']
T(18, 6, ind(ns)); T(18, 7, 'New vehicles in September'); TC(18, 8, '%s vs August' % chg(ns, na), False)
T(18, 10, ind(rs)); T(18, 11, 'Returning vehicles'); TC(18, 12, '%s vs August' % chg(rs, ra), True)
T(18, 14, '%.1f%%' % (100 * rs / (ns + rs))); T(18, 15, 'Repeat share'); T(18, 16, 'August %.1f%%' % (100 * ra / (na + ra)))
T(18, 18, ind(nr['cumS'])); T(18, 19, 'Cumulative unique vehicles'); T(18, 20, '%s at end of August' % ind(nr['cumA']))
set_chart(sh(18, 21).chart, ['August 2026', 'September 2026'], [[na, ns], [ra, rs]], ['New this month', 'Seen in an earlier month'])
T(1 + 17, 1, 'September\'s fall in leads is lost new demand, not fewer re-quotes')
T(18, 23, 'The fall in leads is a fall in new demand')
T(18, 24, ['▪   New vehicles fell %s, from %s to %s' % (chg(ns, na)[2:], ind(na), ind(ns)),
           '▪   Returning vehicles rose %s, %s → %s' % (chg(rs, ra)[2:], ind(ra), ind(rs)),
           '▪   Repeat share rose from %.1f%% to %.1f%%' % (100 * ra / (na + ra), 100 * rs / (ns + rs)),
           '▪   So the %s drop in leads is lost new demand, not fewer re-quotes' % chg(tot_s['leads'], tot_a['leads'])[2:],
           '▪   Cumulative base grew %s → %s unique vehicles' % (ind(nr['cumA']), ind(nr['cumS']))])
T(18, 25, 'Repeat = quoted in any earlier month in the API window (from 5 July 2026). August is restated on this basis (4,417 new / 518 returning; the August deck showed 4,368 / 567 using pre-July history the API does not hold).')

# ---------------- slide 19 failure reasons by carrier
T(19, 0, 'Failure Reasons by Carrier — September')
T(19, 1, 'The same %s failures, split by who is being asked to price' % ind(s['fail']))
blocks = {il_: dict(hdr=(7, 8), tbl=9, own=(12, 15, 18, 21)), dg_: dict(hdr=(25, 26), tbl=27, own=(30, 33, 36, 39)), ta_: dict(hdr=(43, 44), tbl=45, own=(48, 51, 54, 57))}
def short(e, n=44):
    e = e.replace('\n', ' ')
    rep = {'Invalid RTO identified from registration number (see RegistrationNo column)': 'Invalid RTO identified from registration number',
           'Quote creation cannot be possible as inception date of the policy is more than6 months in future': 'Inception date more than 6 months ahead',
           '1182-please provide bundle od start date and bundle od end date': '1182-bundle OD start/end date missing',
           'engine_secure_options  is mandatory.': 'engine_secure_options is mandatory',
           '1197-<id> - Referral triggered from the moratorium': '1197 - Referral: moratorium vehicle',
           'iHub transformation error [il/motor/2w/quickQuote]: unresolved route placeholder (@route.il.host@…) – IL endpoint not configured': 'iHub 2W: unresolved IL route placeholder',
           'iHub transformation error [il/motor/4w/quickQuote]: unresolved route placeholder (@route.il.host@…) – IL endpoint not configured': 'iHub 4W: unresolved IL route placeholder',
           'iHub transformation error [godigit/motor/quickQuote]: response-transformation rule failed (go-digit-in-motor-quick-quote-outtrf)': 'iHub Digit "outtrf" rule failed',
           'Vehicle Type entered do not match with Vahan data, please recheck the details entered.': 'Vehicle type does not match Vahan data'}
    return rep.get(e, e if len(e) <= n else e[:n - 1] + '…')
for p, b_ in blocks.items():
    T(19, b_['hdr'][0], ind(s['failed'][p]))
    T(19, b_['hdr'][1], 'failed calls  ·  %.1f%% of its quote calls' % (100 * s['failed'][p] / fs[p]['calls']))
    rows = [[None] * 3] + [[short(e), ind(n), o] for e, n, o in s['reasons'][p]]
    TB(19, b_['tbl'], rows)
    for r_ in range(1, 6):
        set_cell_color(sh(19, b_['tbl']).table, r_, 2, OWNER_COL[rows[r_][2]])
# ownership value boxes: for each carrier the (value,pct) shapes sit at fixed offsets from the table
own_idx = {il_: [(12, 13), (15, 16), (18, 19), (21, 22)], dg_: [(30, 31), (33, 34), (36, 37), (39, 40)], ta_: [(48, 49), (51, 52), (54, 55), (57, 58)]}
for p, lst in own_idx.items():
    ow = s['owner'][p]; tot_o = sum(ow.values())
    for (vi, pi), name in zip(lst, ['Carrier', 'Fibe', 'Fibe Mapping', 'Unclassified']):
        T(19, vi, ind(ow[name])); T(19, pi, '%.0f%%' % (100 * ow[name] / tot_o))
T(19, 60, ('Platform incident   ', '%s failed calls on 21–22 Sept (iHub: unresolved ICICI route placeholder, Digit "outtrf" rule, Tata gateway errors) sit under Unclassified — all engineering-fixable. Owner split is by root-cause category, applied identically to August.' % ind(ihub_n)))

# ---------------- slide 20 segment mix
T(20, 1, 'Who bought in September, and where the premium came from')
def segrows(lst):
    return [[None] * 4] + [[k, ind(l), ind(po), ind(g)] for k, l, po, g in lst]
TB(20, 6, segrows(s['seg_type'])); TB(20, 8, segrows(s['seg_age'])); TB(20, 10, segrows(s['seg_idv'])); TB(20, 12, segrows(s['seg_state']))
t2w, t4w = s['seg_type'][0], s['seg_type'][1]
age_best = max(s['seg_age'], key=lambda x: x[2])
T(20, 15, ['▪   Two-wheelers are %.0f%% of leads and %.0f%% of policies, but only %.0f%% of premium' % (100 * t2w[1] / tot_s['leads'], 100 * t2w[2] / tot_s['policies'], 100 * t2w[3] / tot_s['gwp']),
           '▪   Private car and commercial: %d policies carrying INR %s — INR %s a policy against %s for two-wheelers' % (t4w[2], ind(t4w[3]), ind(t4w[3] / t4w[2]), ind(t2w[3] / t2w[2])),
           '▪   Older vehicles convert best again: %s years produced %d policies and INR %s of premium' % (age_best[0], age_best[2], ind(age_best[3])),
           '▪   Maharashtra: %d of %d policies (INR %s)' % (s['seg_state'][0][2], tot_s['policies'], ind(s['seg_state'][0][3]))])
T(20, 16, 'Sept 2026, full month. Segments from the quote request; IDV = lowest returned per priced vehicle. August restated on the same basis.')

# ---------------- slide 21 divider
T(21, 4, ['—   Recommendations, re-prioritised after September', '—   Delivery mapped to funnel impact'])
# slide 22: status carried over
T(22, 1, 'Where each item lands in the funnel measured in this deck (status as reported at the August review — to be updated by owners)')
T(22, 1, 'Where each item lands in the funnel (status carried from the August review — owners to update)')

# ================================================================== NEW slides: 2W, 4W (clone of scorecard slide 9) and Cumulative (clone of slide 12)
def product_slide(prod, name, insert_at):
    ns_ = duplicate_slide(prs, 8, insert_at)       # source slide 9 (index 8)
    ps_a, ps_s = PS['A'][prod], PS['S'][prod]
    sh_ = lambda k: ns_.shapes[k]
    settext(sh_(0), '%s View' % name)
    settext(sh_(1), 'September 2026 with the August comparison in brackets — %s only' % prod)
    tb = sh_(5).table
    def c(new, old, fmt=ind):
        return '%s   (%s)' % (fmt(new), chg(new, old))
    rows = [[None, 'ICICI Lombard', 'Go Digit', 'Tata AIG', 'Total']]
    keys = ['leads', 'priced', 'calls', 'succ', 'pol', 'gwp']
    rows.append(['Registrations attempted'] + [c(ps_s[p]['leads'], ps_a[p]['leads']) for p in P3] + [ind(ps_s['Total']['leads'])])
    rows.append(['Leads with a price'] + [c(ps_s[p]['priced'], ps_a[p]['priced']) for p in P3] + [ind(ps_s['Total']['priced'])])
    rows.append(['Lead → price %'] + ['%.1f%%   (%s)' % (100 * ps_s[p]['priced'] / ps_s[p]['leads'], chgpp(ps_s[p]['priced'] / ps_s[p]['leads'], ps_a[p]['priced'] / ps_a[p]['leads'])) for p in P3] + ['%.1f%%' % (100 * ps_s['Total']['priced'] / ps_s['Total']['leads'])])
    rows.append(['Quote calls'] + [c(ps_s[p]['calls'], ps_a[p]['calls']) for p in P3] + [ind(ps_s['Total']['calls'])])
    rows.append(['Call success %'] + ['%.1f%%   (%s)' % (100 * ps_s[p]['succ'] / ps_s[p]['calls'], chgpp(ps_s[p]['succ'] / ps_s[p]['calls'], ps_a[p]['succ'] / ps_a[p]['calls'])) for p in P3] + ['%.1f%%' % (100 * ps_s['Total']['succ'] / ps_s['Total']['calls'])])
    rows.append(['Failed calls'] + [c(ps_s[p]['calls'] - ps_s[p]['succ'], ps_a[p]['calls'] - ps_a[p]['succ']) for p in P3] + [ind(ps_s['Total']['calls'] - ps_s['Total']['succ'])])
    rows.append(['Policies issued'] + [c(ps_s[p]['pol'], ps_a[p]['pol']) if ps_a[p]['pol'] else str(ps_s[p]['pol']) for p in P3] + [ind(ps_s['Total']['pol'])])
    rows.append(['GWP (INR)'] + [c(ps_s[p]['gwp'], ps_a[p]['gwp']) if ps_a[p]['gwp'] else ind(ps_s[p]['gwp']) for p in P3] + [ind(ps_s['Total']['gwp'])])
    rows.append(['Average premium (INR)'] + [('%s   (%s)' % (ind(ps_s[p]['gwp'] / ps_s[p]['pol']), chg(ps_s[p]['gwp'] / ps_s[p]['pol'], ps_a[p]['gwp'] / ps_a[p]['pol']))) if ps_s[p]['pol'] and ps_a[p]['pol'] else '—' for p in P3]
                + [ind(ps_s['Total']['gwp'] / ps_s['Total']['pol']) if ps_s['Total']['pol'] else '—'])
    top = lambda p: '%s (%s)' % (short(ps_s[p]['top'].index[0], 30), ind(int(ps_s[p]['top'].iloc[0])))
    rows.append(['Top failure reason (Sep)'] + [top(p) for p in P3] + [''])
    fill_table(tb, rows)
    recolor_arrows(tb, {1: True, 2: True, 3: True, 4: False, 5: True, 6: False, 7: True, 8: True, 9: True})
    ref = tb.cell(1, 4).text_frame.paragraphs[0].runs[0].font.color.rgb
    for c_ in (1, 2, 3):
        set_cell_color(tb, 10, c_, ref)
    # cards
    for k, p in zip((7, 10, 13), P3):
        pass
    cards = []
    for p in P3:
        sr = ps_s[p]['succ'] / ps_s[p]['calls']; sra = ps_a[p]['succ'] / ps_a[p]['calls']
        cards.append('%s call success %.1f%% (Aug %.1f%%); %d %s policies, INR %s GWP.' % (p, 100 * sr, 100 * sra, ps_s[p]['pol'], prod, ind(ps_s[p]['gwp'])))
    for k, txt in zip((8, 11, 14), cards):
        settext(sh_(k), txt)
    settext(sh_(15), '%s figures count a registration once per carrier it was quoted with; totals show distinct registrations. Policies and GWP are split by the vehicle type on the issued policy.' % prod)
    return ns_

product_slide('2W', 'Two-Wheeler (2W)', 12)       # after slide 12 (index 12 => becomes slide 13)
product_slide('4W', 'Four-Wheeler (4W)', 13)

# cumulative slide (clone of slide 12 call-efficiency table)
ns_ = duplicate_slide(prs, 11, 14)
sh_ = lambda k: ns_.shapes[k]
settext(sh_(0), 'Cumulative — August + September')
settext(sh_(1), 'Both months combined, by carrier')
rows = [[None, None, 'August 2026', 'September 2026', 'Cumulative']]
CUMN = {}
for p in P3:
    ca, cs = fa[p], fs[p]
    pa = AD['pol'][AD['pol'].provider == p]; ps = SD['pol'][SD['pol'].provider == p]
    rows += [[p, 'Quote calls', ind(ca['calls']), ind(cs['calls']), ind(ca['calls'] + cs['calls'])],
             ['', 'Calls returning a price', '%.1f%%' % (100 * ca['succ'] / ca['calls']), '%.1f%%' % (100 * cs['succ'] / cs['calls']), '%.1f%%' % (100 * (ca['succ'] + cs['succ']) / (ca['calls'] + cs['calls']))],
             ['', 'Failed calls', ind(fail_(fa, p)), ind(fail_(fs, p)), ind(fail_(fa, p) + fail_(fs, p))],
             ['', 'Policies issued', str(len(pa)), str(len(ps)), str(len(pa) + len(ps))],
             ['', 'GWP (INR)', ind(pa.premium.sum()), ind(ps.premium.sum()), ind(pa.premium.sum() + ps.premium.sum())]]
fill_table(sh_(5).table, rows)
_t = sh_(5).table
for r_ in range(1, 16):
    _c = _t.cell(r_, 3).text_frame.paragraphs[0].runs[0].font.color.rgb
    set_cell_color(_t, r_, 4, _c)
    set_cell_color(_t, r_, 2, _t.cell(r_, 2).text_frame.paragraphs[0].runs[0].font.color.rgb)
cum_calls = tot_a['calls'] + tot_s['calls']; cum_succ = tot_a['succ'] + tot_s['succ']
cum_pol = tot_a['policies'] + tot_s['policies']; cum_gwp = tot_a['gwp'] + tot_s['gwp']
settext(sh_(7), ('Two months, one picture   ', '%s quote calls, %.1f%% returned a price; %d policies and INR %s GWP from %s distinct vehicles quoted since 5 July.' % (ind(cum_calls), 100 * cum_succ / cum_calls, cum_pol, ind(cum_gwp), ind(nr['cumS']))))
settext(sh_(9), ('Where the failures sit   ', '%s failed calls in total — Tata AIG %.0f%%, Go Digit %.0f%%, ICICI Lombard %.0f%%.' % (
    ind(a['fail'] + s['fail']), 100 * (fail_(fa, ta_) + fail_(fs, ta_)) / (a['fail'] + s['fail']), 100 * (fail_(fa, dg_) + fail_(fs, dg_)) / (a['fail'] + s['fail']), 100 * (fail_(fa, il_) + fail_(fs, il_)) / (a['fail'] + s['fail']))))


# ================================================================== NEW slides: registration funnel by product (clones of slide 5)
def pfunnel(d, prod):
    q = d['q']; g = q[(q['product'] == prod) & (q.reg != '')]
    ap = d['apps']; ap = ap[ap['product'] == prod]; pl = d['pol']; pl = pl[pl['product'] == prod]
    return dict(leads=g.reg.nunique(), priced=g[g.ok].reg.nunique(), apps=ap.reg.nunique(), bought=pl.reg.nunique(), pol=len(pl), gwp=float(pl.premium.sum()),
                calls=int((q['product'] == prod).sum()), succ=int(q[q['product'] == prod].ok.sum()))


def funnel_slide(prod, name, insert_at):
    ns_ = duplicate_slide(prs, 4, insert_at)
    x = lambda k: ns_.shapes[k]
    fa_, fs_ = pfunnel(AD, prod), pfunnel(SD, prod)
    settext(x(0), 'The Funnel — %s' % name)
    settext(x(1), 'September versus August, %s only — every stage and step conversion, per unique registration' % prod)
    r1 = lambda n, o: '%.1f%%' % (100 * n / o)
    rows = [[None, 'August 2026', 'September 2026', None, None]]
    for lab_, k_, com in [(None, 'leads', 'Vehicles entering the funnel'), (None, 'priced', 'Leads that got a price'), (None, 'apps', 'Vehicles reaching application'),
                          (None, 'bought', 'Vehicles that bought'), (None, 'pol', 'One policy per buying vehicle')]:
        rows.append([None, ind(fa_[k_]), ind(fs_[k_]), chg(fs_[k_], fa_[k_]), com])
    rows.append([None, '', '', '', ''])
    conv_ = [('priced', 'leads', 'Lead → quote'), ('apps', 'leads', 'Quote→ Proposal'), ('bought', 'apps', 'Proposal→ Purchase'), ('bought', 'leads', 'Lead → Purchase')]
    for n_, d_, _l in conv_:
        va, vs = fa_[n_] / fa_[d_], fs_[n_] / fs_[d_]
        dec = 2 if (n_, d_) == ('bought', 'leads') else 1
        flat = round(100 * vs, dec) == round(100 * va, dec)
        rows.append([None, '%.*f%%' % (dec, 100 * va), '%.*f%%' % (dec, 100 * vs), '▬ no change' if flat else chgpp(vs, va, dec),
                     'Flat' if flat else ('Improved' if vs > va else 'Slipped')])
    fill_table(x(5).table, rows)
    recolor_arrows(x(5).table, {i: True for i in range(1, 11)})
    from pptx.dml.color import RGBColor as _R
    for r_ in range(7, 11):
        if rows[r_][3] == '▬ no change':
            set_cell_color(x(5).table, r_, 3, _R(0x59, 0x59, 0x59)); set_cell_color(x(5).table, r_, 4, _R(0x59, 0x59, 0x59))
    cA, cS = fa_['bought'] / fa_['apps'], fs_['bought'] / fs_['apps']
    settext(x(7), 'The bottom of the funnel')
    settext(x(8), ['▪   Application → bought: %.1f%% → %.1f%%' % (100 * cA, 100 * cS),
                   '▪   Lead → bought: %.2f%% → %.2f%%' % (100 * fa_['bought'] / fa_['leads'], 100 * fs_['bought'] / fs_['leads']),
                   '▪   %d %s vehicles bought, against %d in August' % (fs_['bought'], prod, fa_['bought']),
                   '▪   %s GWP: INR %s (Aug INR %s)' % (prod, ind(fs_['gwp']), ind(fa_['gwp']))])
    settext(x(10), 'The price step')
    settext(x(11), ['▪   Lead → price: %.1f%% → %.1f%%' % (100 * fa_['priced'] / fa_['leads'], 100 * fs_['priced'] / fs_['leads']),
                    '▪   %s applications, %s' % (fs_['apps'], chg(fs_['apps'], fa_['apps']).replace('▼ ', 'down ').replace('▲ ', 'up ')),
                    '▪   Quote-call success %.1f%% (Aug %.1f%%)' % (100 * fs_['succ'] / fs_['calls'], 100 * fa_['succ'] / fa_['calls'])])
    settext(x(13), 'By carrier (Sep)')
    pc = PS['S'][prod]
    settext(x(14), ' · '.join('%s %d of %d priced' % (p, pc[p]['priced'], pc[p]['leads']) for p in P3))
    settext(x(15), 'Applications and policies are split by the vehicle type on the request / issued policy. Same definitions as the combined funnel.')
    return fs_, fa_


FUN = {}
FUN['2W'] = funnel_slide('2W', 'Two-Wheeler (2W)', 5)
FUN['4W'] = funnel_slide('4W', 'Four-Wheeler (4W)', 6)
pickle.dump({k: v for k, v in FUN.items()}, open('deck_funnel_pw.pkl', 'wb'))

exec(open('diag_pw.py').read())

# ================================================================== housekeeping: footers, page numbers
order = list(prs.slides)
for n, slide in enumerate(order, start=1):
    for shp in slide.shapes:
        if shp.has_text_frame and shp.text_frame.text.startswith('FIBE  ·  Monthly Business Review'):
            settext(shp, 'FIBE  ·  Monthly Business Review  ·  September 2026')
for n, slide in enumerate(order, start=1):
    for shp in slide.shapes:
        if shp.has_text_frame and shp.text_frame.text.strip().isdigit() and shp.top > 6000000 and shp.left > 10000000:
            settext(shp, str(n))
prs.save('FIBE_x_insureMO_-_MBR_September_2026.pptx')
print('saved', len(prs.slides), 'slides')
