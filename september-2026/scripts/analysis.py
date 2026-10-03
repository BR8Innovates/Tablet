"""Shared analysis layer: loads extracted rows for a month and produces every table used by the workbook and deck."""
import pickle
import pandas as pd
from classify import normalise, categorise, owner

PROVIDERS = ['ICICI Lombard', 'Go Digit', 'Tata AIG']
QUOTE_TXNS = (1001, 4001)   # 1001 quick quote; 4001 = Tata 4W compare-quote (counted in the August "Total Calls" as well)


def load(month):
    rows = pd.DataFrame(pickle.load(open('rows_%s.pkl' % month, 'rb')))
    iss = pd.DataFrame(pickle.load(open('iss_%s.pkl' % month, 'rb')))
    rows['month'] = month
    iss['month'] = month
    q = rows[rows.txn.isin(QUOTE_TXNS)].copy()
    q['reg'] = q.reg.fillna('')
    q['err_n'] = q.err.map(lambda e: normalise(e) if isinstance(e, str) else None)
    q['cat'] = q.err_n.map(lambda e: categorise(e) if isinstance(e, str) else None)
    q['owner'] = q.cat.map(lambda c: owner(c) if isinstance(c, str) else None)
    return rows, q, iss


def policies(iss, rows):
    """One row per issued policy (unique CarrierPolicyNo), registration resolved through the proposal number.

    Digit: issued = 2003 (issue-policy) call returning a carrier policyNumber (PolicyNo) AND CarrierPolicyNo.
           (Digit's 2001 create-quote also returns a CarrierPolicyNo - that is the *quote* id, not an issued policy.)
    ICICI Lombard: proposal call (2001) that returns CarrierPolicyNo.
    Tata AIG: issue-policy call (2003) that returns CarrierPolicyNo.
    """
    d = iss.copy()
    prop = d[(d.txn == 2001)]
    # proposal number -> (reg, product, plantype) from the proposal (2001) calls
    pmap = {}
    for _, r in prop.iterrows():
        k = r.res_proposal_no
        if k and r.reg:
            pmap[k] = (r.reg, r['product'], r.plantype)
    out = []
    for prov in PROVIDERS:
        if prov == 'ICICI Lombard':
            x = d[(d.provider == prov) & (d.txn == 2001) & (d.carrier_policy_no != '')]
        else:
            x = d[(d.provider == prov) & (d.txn == 2003) & (d.carrier_policy_no != '')]
        x = x.sort_values('time')
        for pno, g in x.groupby('carrier_policy_no', sort=False):
            r = g.iloc[0]
            reg, prod, plan = r.reg, r['product'], r.plantype
            if not reg:
                reg, prod2, plan2 = pmap.get(r.proposal_no, ('', None, ''))
                prod = prod if isinstance(prod, str) and prod else prod2
                plan = plan or plan2
            if not (isinstance(prod, str) and prod):
                prod = {'2': '2W', '3': '2W', '4': '2W', '5': '2W'}.get(str(plan), '4W' if str(plan) in ('17', '19', '20', '21') else 'Unknown')
            if prov == 'ICICI Lombard':
                prem = r.req_gross
            elif prov == 'Go Digit':
                prem = r.res_gross
            else:
                prem = r.pay_amt
            statuses = sorted(set(g.policy_status) - {''})
            out.append(dict(month=r.month, provider=prov, product=prod, reg=reg, plantype=plan,
                            first_time=r.time, date=r.date, carrier_policy_no=pno,
                            policy_no=(g.policy_no[g.policy_no != ''].iloc[0] if (g.policy_no != '').any() else ''),
                            policy_status='/'.join(statuses), premium=prem, n_calls=len(g)))
    return pd.DataFrame(out)


def funnel(q, apps, pol):
    """Unique-registration funnel overall and per carrier."""
    res = {}
    qq = q[q.reg != '']
    res['Total'] = dict(leads=qq.reg.nunique(), priced=qq[qq.ok].reg.nunique(),
                        apps=apps.reg.nunique(), policies=len(pol), gwp=pol.premium.sum(),
                        calls=len(q), succ=int(q.ok.sum()))
    for p in PROVIDERS:
        a = qq[qq.provider == p]
        res[p] = dict(leads=a.reg.nunique(), priced=a[a.ok].reg.nunique(),
                      apps=apps[apps.provider == p].reg.nunique(),
                      policies=int((pol.provider == p).sum()), gwp=pol[pol.provider == p].premium.sum(),
                      calls=int((q.provider == p).sum()), succ=int(q[q.provider == p].ok.sum()))
    return res
