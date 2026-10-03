import gzip,glob,json,pickle,sys
out={}
for m in ['2026-08','2026-09']:
    d={}
    for f in sorted(glob.glob(f'raw_{m}/*.jsonl.gz')):
        for l in gzip.open(f,'rt'):
            r=json.loads(l)
            if r['TransactionType'] not in (1001,4001): continue
            lg=r['TransactionSyncLogs'][0]
            try: tr=json.loads(lg['TransResponse']); res=tr.get('Result') or {}
            except Exception: continue
            blks=[res]+list(res.get('Multiplan') or [])
            req=json.loads(r['TransRequest']); reg=req['PolicyLobList'][0]['PolicyRiskList'][0].get('RegistrationNo')
            if not reg: continue
            for b in blks:
                try:
                    idv=b['PolicyLobList'][0]['PolicyRiskList'][0].get('IDV')
                    if idv: d.setdefault(reg,[]).append((r['ClientRequestTime'],float(idv)))
                except Exception: pass
    out[m]=d
pickle.dump(out,open('idv.pkl','wb'))
