import pickle, warnings
import pandas as pd
warnings.filterwarnings('ignore')
from pptx import Presentation
from deckhelp import *
from pptx.util import Pt
from analysis import PROVIDERS
from deck_metrics import M, D, S as SD, A as AD
from classify import owner

prs = Presentation('aug_deck.pptx')
sl = prs.slides
OWNER_COL = {}
for _k in (9, 27, 45):
    _t = sl[18].shapes[_k].table
    for _r in range(1, len(_t.rows)):
        _run = _t.cell(_r, 2).text_frame.paragraphs[0].runs[0]
        OWNER_COL.setdefault(_run.text, _run.font.color.rgb)
for _o in ('Carrier', 'Fibe', 'Fibe Mapping', 'Unclassified'):
    OWNER_COL.setdefault(_o, OWNER_COL.get('Fibe'))
a, s = M['A'], M['S']
fa, fs = a['f'], s['f']
P3 = PROVIDERS
SHORT = {'ICICI Lombard': 'ICICI Lombard', 'Go Digit': 'Go Digit', 'Tata AIG': 'Tata AIG'}
GOOD = {}


def sh(i, k):
    return sl[i - 1].shapes[k]


def T(i, k, v):
    settext(sh(i, k), v)


def TB(i, k, rows, good=None):
    fill_table(sh(i, k).table, rows, good)


def TC(i, k, v, good=None):
    settext(sh(i, k), v)
    if good is not None:
        paint(sh(i, k), GREEN if good else RED)


def arrow(txt, up_good=True):
    """colour flag for a change string"""
    return (txt.startswith('▲')) == up_good


def row_good(rows, spec):
    """spec: {(r,c): up_good}; derive colour from the arrow in rows"""
    g = {}
    for (r, c), up in spec.items():
        g[(r, c)] = arrow(rows[r][c], up)
    return g


# ------------------------------------------------------------------ shared derived numbers
ihub = SD['fail'][SD['fail'].err_n.str.contains('iHub', na=False)]
ihub_n = len(ihub); ihub_days = ihub.groupby('date').size().sort_values(ascending=False)
ihub_top = int(ihub_days.iloc[0])
ihub_inc = int(ihub[ihub.date.isin(['2026-09-21', '2026-09-22'])].shape[0])
iss_s = SD['iss']
il_prop = iss_s[(iss_s.provider == 'ICICI Lombard') & (iss_s.txn == 2001)]
il_kyc = int((il_prop.err == 'KYC PENDING').sum()); il_prop_n = len(il_prop)
conv = lambda f: f['policies'] / f['apps']
L = lambda f: f['priced'] / f['leads']
tot_a, tot_s = fa['Total'], fs['Total']
days_s = s['days']

# per product x carrier stats
def prod_stats(d, prod):
    q = d['q']; pol = d['pol']; out = {}
    for p in P3:
        g = q[(q.provider == p) & (q['product'] == prod)]
        gg = g[g.reg != '']
        pp = pol[(pol.provider == p) & (pol['product'] == prod)]
        out[p] = dict(leads=gg.reg.nunique(), priced=gg[gg.ok].reg.nunique(), calls=len(g), succ=int(g.ok.sum()),
                      pol=len(pp), gwp=float(pp.premium.sum()),
                      top=(d['fail'][(d['fail'].provider == p) & (d['fail']['product'] == prod)].err_n.value_counts().head(1)))
    g = q[(q['product'] == prod) & (q.reg != '')]
    out['Total'] = dict(leads=g.reg.nunique(), priced=g[g.ok].reg.nunique(), calls=sum(out[p]['calls'] for p in P3),
                        succ=sum(out[p]['succ'] for p in P3), pol=sum(out[p]['pol'] for p in P3), gwp=sum(out[p]['gwp'] for p in P3))
    return out
PS = {m: {pr: prod_stats(d, pr) for pr in ('2W', '4W')} for m, d in (('A', AD), ('S', SD))}

# ================================================================== slide 1 title
T(1, 9, ['Fibe × InsureMO – Monthly Governance', 'Sep 2026', '', 'Powered by InsureMO'])

# ================================================================== slide 2 agenda
T(2, 1, 'Five sections — September against August throughout')
T(2, 12, 'The same metrics for all three carriers, 2W and 4W views, and a cumulative Aug + Sep view')
T(2, 26, ('Scope   ', 'This review covers September 2026 with August 2026 as the only comparison (the API holds July only from 5 July and it does not reconcile to the July figures in the August deck). '
          'All figures were extracted directly from the InsureMO transaction log; the same extraction reproduces the August deck exactly.'))

# ================================================================== slide 3 executive summary
T(3, 1, 'September 2026 against August 2026 — demand and conversion both fell; reliability held but is still weak')
T(3, 6, ind(tot_s['leads'])); TC(3, 8, chg(tot_s['leads'], tot_a['leads']) + ' vs August', False)
T(3, 10, ind(tot_s['policies'])); TC(3, 12, chg(tot_s['policies'], tot_a['policies']) + ' vs August', False)
T(3, 14, 'INR ' + ind(tot_s['gwp'])); TC(3, 16, chg(tot_s['gwp'], tot_a['gwp']) + ' vs August', False)
T(3, 18, '%.1f%%' % (100 * L(tot_s))); TC(3, 20, chgpp(L(tot_s), L(tot_a)), True)
T(3, 22, ind(s['fail'])); TC(3, 24, chg(s['fail'], a['fail']) + ' vs August', True)
avg_s, avg_a = tot_s['gwp'] / tot_s['policies'], tot_a['gwp'] / tot_a['policies']
rows = [
    [None, 'August 2026', 'September 2026', None, None],
    [None, ind(tot_a['leads']), ind(tot_s['leads']), chg(tot_s['leads'], tot_a['leads']), 'Fewer vehicles entering the funnel'],
    [None, ind(tot_a['priced']), ind(tot_s['priced']), chg(tot_s['priced'], tot_a['priced']), 'Fell, but slower than leads'],
    [None, ind(tot_a['apps']), ind(tot_s['apps']), chg(tot_s['apps'], tot_a['apps']), 'Fewer vehicles entering the journey'],
    [None, ind(a['bought']), ind(s['bought']), chg(s['bought'], a['bought']), 'The step that fell most'],
    [None, ind(tot_a['policies']), ind(tot_s['policies']), chg(tot_s['policies'], tot_a['policies']), 'One policy per buying vehicle'],
    [None, ind(tot_a['gwp']), ind(tot_s['gwp']), chg(tot_s['gwp'], tot_a['gwp']), 'Fewer, richer policies'],
    [None, ind(avg_a), ind(avg_s), chg(avg_s, avg_a), 'Premium mix moved to 4W'],
    [None, ind(tot_a['calls']), ind(tot_s['calls']), chg(tot_s['calls'], tot_a['calls']), 'Machinery shrank with demand'],
    [None, ind(a['fail']), ind(s['fail']), chg(s['fail'], a['fail']), 'Down with volume; rate unchanged'],
]
g = {}
for r in range(1, 10):
    up_good = r not in (9,)
    g[(r, 3)] = arrow(rows[r][3], up_good); g[(r, 4)] = g[(r, 3)]
TB(3, 25, rows, g)
fourw_share = SD['pol'][SD['pol']['product'] == '4W'].premium.sum() / tot_s['gwp']
T(3, 28, ['▪   Leads getting a price: 92.3%% → %.1f%%' % (100 * L(tot_s)),
          '▪   Average premium up %s to INR %s' % (chg(avg_s, avg_a)[2:], ind(avg_s)),
          '▪   Go Digit GWP up %s to INR %s' % (chg(fs['Go Digit']['gwp'], fa['Go Digit']['gwp'])[2:], ind(fs['Go Digit']['gwp'])),
          '▪   Digit and Tata 4W call success both improved'])
T(3, 31, ['▪   Policies fell %s → %s; ICICI 25 → 5' % (ind(tot_a['policies']), ind(tot_s['policies'])),
          '▪   Application → bought: 24.4%% → %.1f%%' % (100 * conv(tot_s)),
          '▪   Tata AIG 2W priced only 3.0% of calls; iHub incident on 21–22 Sept'])
T(3, 33, ('The one-line story   ', 'Fewer vehicles and fewer buyers, with ICICI Lombard\'s funnel breaking at KYC — and no improvement in quote reliability.'))

# ================================================================== slide 4 section divider
T(4, 3, 'September against August, stage by stage')

# ================================================================== slide 5 funnel
rows = [
    [None, 'August 2026', 'September 2026', None, None],
    [None, ind(tot_a['leads']), ind(tot_s['leads']), chg(tot_s['leads'], tot_a['leads']), 'Fewer vehicles entering the funnel'],
    [None, ind(tot_a['priced']), ind(tot_s['priced']), chg(tot_s['priced'], tot_a['priced']), 'Fell %s, slower than leads' % chg(tot_s['priced'], tot_a['priced'])[2:]],
    [None, ind(tot_a['apps']), ind(tot_s['apps']), chg(tot_s['apps'], tot_a['apps']), 'Fell as fast as leads'],
    [None, ind(a['bought']), ind(s['bought']), chg(s['bought'], a['bought']), 'The largest single decline'],
    [None, ind(tot_a['policies']), ind(tot_s['policies']), chg(tot_s['policies'], tot_a['policies']), 'One policy per buying vehicle'],
    [None, '', '', '', ''],
    [None, '%.1f%%' % (100 * L(tot_a)), '%.1f%%' % (100 * L(tot_s)), chgpp(L(tot_s), L(tot_a)), 'Improved'],
    [None, '%.1f%%' % (100 * tot_a['apps'] / tot_a['leads']), '%.1f%%' % (100 * tot_s['apps'] / tot_s['leads']), chgpp(tot_s['apps'] / tot_s['leads'], tot_a['apps'] / tot_a['leads']), 'Slipped back'],
    [None, '%.1f%%' % (100 * conv(tot_a)), '%.1f%%' % (100 * conv(tot_s)), chgpp(conv(tot_s), conv(tot_a)), 'Gave back much of August\'s gain'],
    [None, '%.2f%%' % (100 * tot_a['policies'] / tot_a['leads']), '%.2f%%' % (100 * tot_s['policies'] / tot_s['leads']), chgpp(tot_s['policies'] / tot_s['leads'], tot_a['policies'] / tot_a['leads'], 2), 'Down by about 40%'],
]
g = {}
for r in (1, 2, 3, 4, 5, 7, 8, 9, 10):
    g[(r, 3)] = arrow(rows[r][3], True); g[(r, 4)] = g[(r, 3)]
TB(5, 5, rows, g)
T(5, 0, 'The Funnel, September versus August')
T(5, 7, 'The bottom fell')
T(5, 8, ['▪   Application → bought: 24.4%% → %.1f%%' % (100 * conv(tot_s)),
         '▪   Lead → bought: 1.20%% → %.2f%%' % (100 * tot_s['policies'] / tot_s['leads']),
         '▪   %d vehicles bought, against %d in August' % (s['bought'], a['bought']),
         '▪   ICICI Lombard did most of the damage: 40 applications, 5 policies'])
T(5, 10, 'Price step improved')
T(5, 11, ['▪   Lead → price: 92.3%% → %.1f%%' % (100 * L(tot_s)),
          '▪   %d applications, down %s' % (tot_s['apps'], chg(tot_s['apps'], tot_a['apps'])[2:]),
          '▪   Only %.1f%% of leads got no price at all' % (100 * (1 - L(tot_s)))])
T(5, 13, 'To verify next month')
T(5, 14, 'Whether the application → bought rate recovers above 20%%, and whether ICICI proposals stuck at KYC pending (%d of %d proposal calls) convert.' % (il_kyc, il_prop_n))
T(5, 15, 'Vehicles that bought and policies issued are identical in both months — registration-level issuance reconciles for all three carriers.')

# ================================================================== slide 6 quote engine efficiency
cpl_a, cpl_s = tot_a['calls'] / tot_a['leads'], tot_s['calls'] / tot_s['leads']
sr_a, sr_s = tot_a['succ'] / tot_a['calls'], tot_s['succ'] / tot_s['calls']
T(6, 6, ind(tot_s['calls'])); T(6, 7, 'Quote calls in September'); TC(6, 8, chg(tot_s['calls'], tot_a['calls']) + ' vs August', False)
T(6, 10, '%.1f' % cpl_s); T(6, 12, 'August %.1f' % cpl_a)
T(6, 14, '%.1f%%' % (100 * sr_s)); TC(6, 16, chgpp(sr_s, sr_a), sr_s >= sr_a)
T(6, 18, ind(s['fail'])); TC(6, 20, chg(s['fail'], a['fail']), True)
set_chart(sh(6, 21).chart, ['August 2026', 'September 2026'], [[tot_a['calls'], tot_s['calls']], [round(100 * sr_a, 1), round(100 * sr_s, 1)]])
T(6, 23, 'Volume down, reliability flat')
T(6, 24, ['▪   %.1f%% of calls returned a price, against %.1f%% in August' % (100 * sr_s, 100 * sr_a),
          '▪   %s calls failed, against %s in August' % (ind(s['fail']), ind(a['fail'])),
          '▪   Calls fell %s to %s; calls per lead flat at %.1f' % (chg(tot_s['calls'], tot_a['calls'])[2:], ind(tot_s['calls']), cpl_s),
          '▪   Tata AIG is the bulk of it: %s failures on %s calls' % (ind(s['failed']['Tata AIG']), ind(fs['Tata AIG']['calls'])),
          '▪   iHub integration faults: %s calls, %s of them on 21–22 Sept' % (ind(ihub_n), ind(ihub_inc))])

# ================================================================== slide 7 business outcome
set_chart(sh(7, 5).chart, ['August 2026', 'September 2026'], [[tot_a['gwp'], tot_s['gwp']], [tot_a['policies'], tot_s['policies']]])
T(7, 7, 'Fewer policies, bigger ticket')
T(7, 8, ['▪   GWP fell %s to INR %s' % (chg(tot_s['gwp'], tot_a['gwp'])[2:], ind(tot_s['gwp'])),
         '▪   Policies %d → %d' % (tot_a['policies'], tot_s['policies']),
         '▪   Average premium rose %s to INR %s' % (chg(avg_s, avg_a)[2:], ind(avg_s)),
         '▪   Decline is volume-led: policies fell faster than GWP',
         '▪   4W is %.0f%% of GWP from %d of %d policies' % (100 * fourw_share, int((SD['pol']['product'] == '4W').sum()), tot_s['policies'])])
rows = [[None] * 5,
        ['Policies issued', str(tot_a['policies']), str(tot_s['policies']), chg(tot_s['policies'], tot_a['policies']), '%.1f a day' % (tot_s['policies'] / days_s)],
        ['GWP (INR)', ind(tot_a['gwp']), ind(tot_s['gwp']), chg(tot_s['gwp'], tot_a['gwp']), 'INR %s a day' % ind(tot_s['gwp'] / days_s)],
        ['Average premium (INR)', ind(avg_a), ind(avg_s), chg(avg_s, avg_a), '—'],
        ['Applications started', str(tot_a['apps']), str(tot_s['apps']), chg(tot_s['apps'], tot_a['apps']), '%.1f a day' % (tot_s['apps'] / days_s)]]
rows[0] = [None, 'August 2026', 'September 2026', None, 'Per day (Sep)']
g = {(1, 3): False, (2, 3): False, (3, 3): True, (4, 3): False}
TB(7, 9, rows, {k: arrow(rows[k[0]][3], True) for k in g})
T(7, 10, 'GWP is premium on policies issued in the month. Both months are complete (Aug 31 days, Sep 30 days), so per-day figures are comparable.')

# ================================================================== slide 8 divider
T(8, 4, ['—   Registrations, applications and policies', '—   Premium and average ticket', '—   Call efficiency, 2W / 4W views and the cumulative Aug + Sep view'])

# ================================================================== slide 9 scorecard
def sc_row(label, key=None, fmt=ind, f=None, total=None, up_good=True):
    pass

def cell(newv, oldv, fmt=lambda x: ind(x)):
    return '%s   (%s)' % (fmt(newv), chg(newv, oldv))

rows = [[None] * 5]
rows[0] = [None, 'ICICI Lombard', 'Go Digit', 'Tata AIG', 'Total']
def line(label, key, total_val=None, fmt=ind):
    r = [label]
    for p in P3:
        r.append(cell(fs[p][key], fa[p][key], fmt))
    r.append(total_val if total_val is not None else fmt(tot_s[key]))
    return r
rows.append(line('Registrations attempted', 'leads', ind(tot_s['leads'])))
rows.append(line('Leads with a price', 'priced', ind(tot_s['priced'])))
rows.append(line('Applications', 'apps', ind(tot_s['apps'])))
rows.append(line('Policies issued', 'policies', ind(tot_s['policies'])))
rows.append(line('GWP (INR)', 'gwp', ind(tot_s['gwp'])))
avgp = lambda f, p: f[p]['gwp'] / f[p]['policies']
rows.append(['Average premium (INR)'] + ['%s   (%s)' % (ind(avgp(fs, p)), chg(avgp(fs, p), avgp(fa, p))) for p in P3] + [ind(avg_s)])
shr = lambda f, p: f[p]['gwp'] / f['Total']['gwp']
rows.append(['Share of GWP %'] + ['%.0f%%   (%s)' % (100 * shr(fs, p), chg(shr(fs, p), shr(fa, p))) for p in P3] + ['100%'])
rows.append(line('Quote calls', 'calls', ind(tot_s['calls'])))
fail_ = lambda f, p: f[p]['calls'] - f[p]['succ']
rows.append(['Failed calls'] + ['%s   (%s)' % (ind(fail_(fs, p)), chg(fail_(fs, p), fail_(fa, p))) for p in P3] + [ind(s['fail'])])
rows.append(['Lead → price %'] + ['%.1f%%   (%s)' % (100 * L(fs[p]), chgpp(L(fs[p]), L(fa[p]))) for p in P3] + ['%.1f%%' % (100 * L(tot_s))])
T(9, 1, 'September 2026 with the August comparison in brackets')
TB(9, 5, rows)
recolor_arrows(sh(9, 5).table, {8: False, 9: False})
il_, dg_, ta_ = 'ICICI Lombard', 'Go Digit', 'Tata AIG'
T(9, 8, '%d policies, down from %d, and %.0f%% of GWP gone — 40 applications became 5 policies (%d proposals stuck at KYC pending).'
  % (fs[il_]['policies'], fa[il_]['policies'], 100 * (1 - fs[il_]['gwp'] / fa[il_]['gwp']), il_kyc))
T(9, 11, '%d policies (Aug %d) but GWP up %s to INR %s — now the largest premium contributor at %.0f%%.' % (fs[dg_]['policies'], fa[dg_]['policies'], chg(fs[dg_]['gwp'], fa[dg_]['gwp'])[2:], ind(fs[dg_]['gwp']), 100 * shr(fs, dg_)))
T(9, 14, '%d policies at INR %s average — the richest ticket, but only %.1f%% of its leads got a price.' % (fs[ta_]['policies'], ind(avgp(fs, ta_)), 100 * L(fs[ta_])))
T(9, 15, 'Brackets compare September with August. Registrations attempted sum to more than the total because a vehicle is quoted with several carriers.')

# ================================================================== slide 10 registrations / apps / policies
cats3 = ['ICICI Lombard', 'Go Digit', 'Tata AIG']
nm = ['August 2026', 'September 2026']
for idx, key in [(6, 'leads'), (8, 'apps'), (10, 'policies')]:
    set_chart(sh(10, idx).chart, cats3, [[fa[p][key] for p in P3], [fs[p][key] for p in P3]], nm)
rows = [[None] * 7,
        ] + [[p] + ['{:,} → {:,}'.format(fa[p]['leads'], fs[p]['leads']), '%d → %d' % (fa[p]['apps'], fs[p]['apps']), '%d → %d' % (fa[p]['policies'], fs[p]['policies']),
              '%.1f' % (fs[p]['apps'] / fs[p]['policies']), '%.0f%%' % (100 * fs[p]['policies'] / tot_s['policies']),
              {'ICICI Lombard': 'Stalled', 'Go Digit': 'Steady', 'Tata AIG': 'Holding'}[p]] for p in P3]
rows[0] = [None, 'Registrations Aug → Sep', 'Applications Aug → Sep', 'Policies Aug → Sep', 'Applications per policy (Sep)', 'Share of September policies', None]
rows[1][6], rows[2][6], rows[3][6] = 'Stalled', 'Down, richer', 'Down, richest'
TB(10, 11, rows)
for r_ in (1, 2, 3):
    for c_ in (3, 6):
        set_cell_color(sh(10, 11).table, r_, c_, RED)
T(10, 13, ('ICICI Lombard stalled   ', 'In August ICICI needed 3.8 applications per policy; in September it needed %.1f. %d of its %d proposal calls returned KYC PENDING — the journey is stopping before issuance.'
           % (fs[il_]['apps'] / fs[il_]['policies'], il_kyc, il_prop_n)))
T(10, 14, 'Applications per policy is applications divided by policies issued in the same month (August: ICICI 3.8, Digit 4.1, Tata 5.5).')

# ================================================================== slide 11 premium
set_chart(sh(11, 6).chart, cats3, [[fa[p]['gwp'] for p in P3], [fs[p]['gwp'] for p in P3]], nm)
set_chart(sh(11, 8).chart, cats3, [[round(avgp(fa, p)) for p in P3], [round(avgp(fs, p)) for p in P3]], nm)
rows = [[None] * 7] + [[p, ind(fa[p]['gwp']), ind(fs[p]['gwp']), chg(fs[p]['gwp'], fa[p]['gwp']), '%.0f%%' % (100 * shr(fa, p)), '%.0f%%' % (100 * shr(fs, p)), 'INR ' + ind(avgp(fs, p))] for p in P3]
rows[0] = [None, 'GWP August', 'GWP September', None, 'Share August', 'Share September', 'Average premium September']
g = {(i + 1, 3): arrow(rows[i + 1][3], True) for i in range(3)}
TB(11, 9, rows, g)
T(11, 11, ('A more concentrated book   ', 'September split is %.0f%% / %.0f%% / %.0f%% against August\'s %.0f%% / %.0f%% / %.0f%%. Go Digit is now the largest contributor, Tata AIG has the richest ticket, and ICICI Lombard — nearly half the book in August — has fallen to %.0f%%.'
           % (100 * shr(fs, il_), 100 * shr(fs, dg_), 100 * shr(fs, ta_), 100 * shr(fa, il_), 100 * shr(fa, dg_), 100 * shr(fa, ta_), 100 * shr(fs, il_))))

# ================================================================== slide 12 call efficiency
crow = lambda m, p: (m['calls_reg'][p], m['busiest'][p])
rows = [[None] * 5]
rows[0] = [None, None, 'August 2026', 'September 2026', 'Change']
for p in P3:
    q_a, q_s = fa[p]['calls'], fs[p]['calls']
    sr_a_, sr_s_ = fa[p]['succ'] / q_a, fs[p]['succ'] / q_s
    rows += [[p, 'Quote calls', ind(q_a), ind(q_s), chg(q_s, q_a)],
             ['', 'Calls per registration', '%.1f' % a['calls_reg'][p], '%.1f' % s['calls_reg'][p], chgpp(s['calls_reg'][p] / 100, a['calls_reg'][p] / 100).replace(' pp', ' pp') if False else ('▲ ' if s['calls_reg'][p] >= a['calls_reg'][p] else '▼ ') + '%.1f pp' % abs(s['calls_reg'][p] - a['calls_reg'][p])],
             ['', 'Calls returning a price', '%.1f%%' % (100 * sr_a_), '%.1f%%' % (100 * sr_s_), chgpp(sr_s_, sr_a_)],
             ['', 'Failed calls', ind(fail_(fa, p)), ind(fail_(fs, p)), chg(fail_(fs, p), fail_(fa, p))],
             ['', 'Busiest single registration', str(a['busiest'][p]), str(s['busiest'][p]), chg(s['busiest'][p], a['busiest'][p])]]
g = {}
for r in range(1, 16):
    kind = (r - 1) % 5
    if kind in (1, 3, 4):   # calls/reg, failed, busiest: lower is better
        g[(r, 4)] = arrow(rows[r][4], False)
    elif kind == 2:
        g[(r, 4)] = arrow(rows[r][4], True)
    else:
        g[(r, 4)] = arrow(rows[r][4], True)
TB(12, 5, rows, g)
recolor_arrows(sh(12, 5).table, {r: (((r - 1) % 5) == 2) for r in range(1, 16)}, skip_cols=(0, 1))
better = [p for p in P3 if fs[p]['succ'] / fs[p]['calls'] > fa[p]['succ'] / fa[p]['calls']]
T(12, 7, ('Digit improved, ICICI slipped   ',
          'ICICI call success eased %.1f%% → %.1f%%; Digit rose %.1f%% → %.1f%%; Tata %.1f%% → %.1f%% (Tata 2W only 3.0%%).' % (
              100 * fa[il_]['succ'] / fa[il_]['calls'], 100 * fs[il_]['succ'] / fs[il_]['calls'],
              100 * fa[dg_]['succ'] / fa[dg_]['calls'], 100 * fs[dg_]['succ'] / fs[dg_]['calls'],
              100 * fa[ta_]['succ'] / fa[ta_]['calls'], 100 * fs[ta_]['succ'] / fs[ta_]['calls'])))
T(12, 9, ('And the machinery shrank with demand   ', '%s calls for %s leads — %.1f each, flat on %.1f in August.' % (ind(tot_s['calls']), ind(tot_s['leads']), cpl_s, cpl_a)))

pickle.dump(dict(done_part1=True), open('deck_part1.flag', 'wb'))
exec(open('build_deck_b.py').read())
