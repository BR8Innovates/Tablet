import gzip,json,glob,sys,collections,re
import pandas as pd
from extract import row_for
src=open('last10_logs.py').read()
ns=__import__('openpyxl.styles',fromlist=['x']).__dict__.copy(); ns.update(re=__import__('re'),json=json,pd=pd)
exec(src[src.index('PII='):src.index('Q=D;')],ns)
clean,hdrrow,put=ns['clean'],ns['hdrrow'],ns['put']
def msg(sr):
    try:
        j=json.loads(sr); j=j.get('detail',j)
        return str(j.get('message_txt') or j.get('ErrorMessage') or j.get('message') or '')[:200]
    except Exception: return (sr or '')[:200]
rows=[];ok=0
for d in ['raw_2026-07','raw_2026-08','raw_2026-09','raw_2026-10']:
    for f in sorted(glob.glob(d+'/*.jsonl.gz')):
        for l in gzip.open(f,'rt'):
            e=json.loads(l)
            if e.get('ProviderCode')!='TATAAIG' or e['TransactionType']!=2003: continue
            x=row_for(e);lg=e['TransactionSyncLogs'][0]
            if x.get('carrier_policy_no'): ok+=1; continue
            rows.append([e['ClientRequestTime'][:10],e['ClientRequestTime'],msg(lg.get('SyncResponse')),e['TraceId'],e['ClientRequestId'],lg['SyncUrl'],lg['SyncStatus'],
                         clean(e['TransRequest']),clean(lg['SyncRequest']),clean(lg['SyncResponse']),clean(lg['TransResponse'])])
rows.sort(key=lambda r:r[1])
print('success',ok,'fail',len(rows))
sm=collections.Counter((r[0][:7],r[2]) for r in rows)
from openpyxl import Workbook
wb=Workbook(); s=wb.active; s.title='Summary'
hdrrow(s,1,['Month','Insurer error','Failed calls'])
for i,((m,er),n) in enumerate(sorted(sm.items()),2): put(s,i,[m,er,n])
for k,w in zip('ABC',[10,80,12]): s.column_dimensions[k].width=w
ws=wb.create_sheet('Failed Issue Policy Cases')
hdrrow(ws,1,['Date','Call time','Insurer error','TraceId','ClientRequestId','Carrier endpoint','Sync status','Fibe → InsureMO request','InsureMO → Insurer request','Insurer response','InsureMO response'])
for i,r in enumerate(rows,2): put(ws,i,r)
for j,w in enumerate([11,20,50,34,38,30,9,60,60,60,60],1): ws.column_dimensions[chr(64+j)].width=w
ws.freeze_panes='D2'
wb.save('out10/Tata_IssuePolicy_Failures_Jul-Oct2026.xlsx')
for k,v in sorted(sm.items()): print(k,v)
print(rows[-1][0], min(r[0] for r in rows if 'Product Name' in r[2]))
