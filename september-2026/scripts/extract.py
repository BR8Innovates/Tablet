"""Slim every raw API record into one flat row (no customer PII kept) -> pickle.
usage: python3 extract.py 2026-09
"""
import gzip, json, glob, re, sys, pickle

PROV = {'IL': 'ICICI Lombard', 'DIGIT': 'Go Digit', 'TATAAIG': 'Tata AIG'}


def jl(s):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def first_risk(req):
    try:
        return req['PolicyLobList'][0]['PolicyRiskList'][0]
    except Exception:
        return {}


def num(x):
    try:
        return float(str(x).replace('INR', '').replace(',', '').strip())
    except Exception:
        return None


def digit_err(sr, raw):
    """error text out of a Digit failed response"""
    if sr is None:
        return (raw or '').strip()[:200] or 'Empty response body'
    if sr.get('ErrorMessage'):
        return str(sr['ErrorMessage'])
    ed = sr.get('error_details') or {}
    d = ed.get('detail') if isinstance(ed, dict) and ed else sr.get('detail')
    if isinstance(d, dict):
        e = d.get('error')
        if isinstance(e, dict):
            vm = e.get('validationMessages')
            if vm:
                return str(vm[0] if isinstance(vm, list) else vm)
            return 'errorCode: %s (no validationMessages)' % e.get('errorCode')
        if d.get('Error'):
            return str(d['Error'])
        if d.get('message'):
            return str(d['message'])
        if d.get('statusMessage'):
            return str(d['statusMessage'])
    if isinstance(ed, dict) and ed.get('http_status_code'):
        return 'HTTP %s' % ed['http_status_code']
    return 'Unrecognised error response'


def row_for(r):
    lg = r['TransactionSyncLogs'][0] if r['TransactionSyncLogs'] else {}
    req = jl(r.get('TransRequest')) or {}
    risk = first_risk(req)
    sr_raw = lg.get('SyncResponse')
    sr = jl(sr_raw)
    tr = jl(lg.get('TransResponse')) or {}
    res = tr.get('Result') if isinstance(tr.get('Result'), dict) else {}
    prov = r['ProviderCode']
    t = r['TransactionType']
    ptype = req.get('ProductType')
    product = {2: '2W', 1: '4W'}.get(ptype)
    if not product:
        product = {'IND-2W': '2W', 'IND-4W': '4W'}.get(r['CountryCode'], 'Unknown')
    row = dict(
        date=r['ClientRequestTime'][:10], time=r['ClientRequestTime'], provider=PROV.get(prov, prov), prov_code=prov,
        product=product, txn=t, url=lg.get('SyncUrl'), reg=risk.get('RegistrationNo') or '',
        plantype=str(req.get('PlanType', '')), plancode=str(req.get('PlanCode', '') or ''),
        carriertype=risk.get('CarrierType'), idv=num(risk.get('VehicleIDV')),
        rto=risk.get('RTOCode'), regdate=risk.get('RegistrationDate'),
        make=risk.get('Make'), model=risk.get('Model'), vage=risk.get('VehicleAge'),
        effdate=req.get('EffectiveDate'), trace=r['TraceId'], crid=r['ClientRequestId'], listid=r['ListId'],
        crs=r['ClientRequestStatus'], bs=r['BusinessStatus'], syncstatus=lg.get('SyncStatus'),
        proposal_no=req.get('CarrierProposalNo') or req.get('CarrierProposalId'),
    )
    # ---- success / error / premium for the response -----------------------
    prem = num(res.get('DuePremium')) or num(res.get('GrossPremium'))
    if not prem and isinstance(res.get('Multiplan'), list):  # Tata 4W compare quote: several plans
        ps = [num(p.get('DuePremium')) or num(p.get('GrossPremium')) for p in res['Multiplan'] if isinstance(p, dict)]
        ps = [p for p in ps if p]
        prem = min(ps) if ps else None
    err = None
    ok = False
    if t in (1001, 4001):
        has_prem = bool(prem and prem > 0)
        if has_prem and not res.get('ErrorMessage'):
            ok = True
        else:
            if prov == 'IL':
                msg = res.get('ErrorMessage') or (isinstance(sr, dict) and sr.get('ErrorMessage')) or ''
                if not msg and sr is None:
                    raw = (sr_raw or '').strip()
                    msg = 'java.lang.NoSuchMethodError' if 'NoSuchMethodError' in raw else (raw[:200] or 'Empty response body')
                err = msg or 'No premium returned (Success=false or Premium<=0)'
            elif prov == 'DIGIT':
                if sr is not None and not (isinstance(sr, dict) and sr.get('contract')):
                    err = digit_err(sr, sr_raw)
                elif sr is None:
                    raw = (sr_raw or '').strip()
                    err = 'java.lang.NoSuchMethodError' if 'NoSuchMethodError' in raw else (raw[:200] or 'Empty response body')
                else:
                    err = 'No premium returned (Success=false or Premium<=0)'
            else:  # Tata
                msg = res.get('ErrorMessage') or (isinstance(sr, dict) and sr.get('message_txt')) or ''
                if not msg and isinstance(sr, dict):
                    ed = sr.get('error_details') or {}
                    dd = ed.get('detail') if isinstance(ed, dict) else None
                    if isinstance(dd, dict):
                        msg = dd.get('message') or dd.get('Error') or ''
                if not msg and sr is None:
                    raw = (sr_raw or '').strip()
                    msg = raw[:200] or 'Empty response body'
                err = msg or 'status=None'
    row['premium'] = prem
    row['ok'] = ok
    row['err'] = err
    # ---- policy / proposal identifiers ------------------------------------
    row['carrier_policy_no'] = res.get('CarrierPolicyNo') or res.get('PolicyNo') or None
    row['policy_no'] = None  # carrier-native policy number (Digit: policyNumber in raw response)
    row['policy_status'] = res.get('CarrierPolicyStatus') or res.get('StatusCode')
    if isinstance(sr, dict):
        if prov == 'DIGIT':
            row['policy_no'] = sr.get('policyNumber') or None
        elif prov == 'TATAAIG' and isinstance(sr.get('data'), list) and sr['data'] and isinstance(sr['data'][0], dict):
            row['policy_no'] = sr['data'][0].get('policy_no') or None
        elif prov == 'IL':
            row['policy_no'] = sr.get('PolicyNo') or sr.get('PolicyNumber') or None
    row['res_proposal_no'] = res.get('CarrierProposalNo') or res.get('ApplicationId')
    row['gross_premium_txt'] = res.get('GrossPremium')
    row['res_err'] = res.get('ErrorMessage') or res.get('IMOErrorMessage') or res.get('CarrierErrorMessage')
    row['res_success'] = res.get('Success')
    row['res_keys'] = ','.join(sorted(res.keys()))[:300]
    row['req_gross'] = req.get('GrossPremium')
    return row


def main(month):
    rows = []
    for f in sorted(glob.glob('raw_%s/*.jsonl.gz' % month)):
        for l in gzip.open(f, 'rt'):
            rows.append(row_for(json.loads(l)))
    pickle.dump(rows, open('rows_%s.pkl' % month, 'wb'))
    print(month, len(rows))


if __name__ == '__main__':
    main(sys.argv[1])
