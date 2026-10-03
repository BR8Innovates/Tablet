"""Compute every table for Aug + Sep once; pickle to prep.pkl for the workbook and deck builders."""
import pickle
import pandas as pd
from analysis import load, policies, funnel, PROVIDERS

MONTHS = ['2026-08', '2026-09']
CATS = ['Underwriting Rule / Referral', 'Bundle/Add-on Configuration', 'Third-Party Cover Rule', 'RTO / Registration Data',
        'System/Technical Error', 'Mandatory Field Missing', 'Date/Policy Validity Rule', 'Invalid Input Value',
        'Vehicle Data Mismatch (Vahan)', 'Pricing/Limit Breach', 'Renewal/Policy State Issue', 'Other/Uncategorized']
CPS = [(p, pr) for p in PROVIDERS for pr in ('2W', '4W')]


def month_data(m):
    rows, q, iss = load(m)
    pol = policies(iss, rows)
    apps = iss[(iss.txn == 2001) & (iss.reg.fillna('') != '')].copy()
    d = dict(month=m, rows=rows, q=q, iss=iss, pol=pol, apps=apps)
    d['funnel'] = funnel(q, apps, pol)
    d['n_api_rows'] = len(rows)
    d['calls'] = (q.groupby(['provider', 'product']).agg(calls=('ok', 'size'), succ=('ok', 'sum'))
                  .assign(fail=lambda x: x.calls - x.succ))
    f = q[~q.ok].copy()
    f['reg_disp'] = f.reg.where(f.reg != '', '(blank)')
    d['fail'] = f
    # Raw-data aggregate (Insurer, Reg, Product, PlanType, Error, Occurrences, Category)
    raw = (f.groupby(['provider', 'reg_disp', 'product', 'plantype', 'err_n', 'cat']).size().reset_index(name='occ')
           .sort_values(['provider', 'reg_disp', 'product', 'plantype', 'err_n']).reset_index(drop=True))
    d['raw'] = raw
    # daily trend
    dd = q.groupby(['date', 'provider']).agg(calls=('ok', 'size'), succ=('ok', 'sum')).reset_index()
    d['daily'] = dd
    # retries
    per_reg = f[f.reg != ''].groupby('reg').size().sort_values(ascending=False)
    d['per_reg'] = per_reg
    return d


def main():
    D = {m: month_data(m) for m in MONTHS}
    pickle.dump(D, open('prep.pkl', 'wb'))
    for m in MONTHS:
        d = D[m]
        print(m, 'quote calls', len(d['q']), 'failed', len(d['fail']), 'raw rows', len(d['raw']), 'policies', len(d['pol']))


if __name__ == '__main__':
    main()
