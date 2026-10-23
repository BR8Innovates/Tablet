import gzip,json,glob,sys
import pandas as pd
from extract import row_for
src=open('last10_logs.py').read()
ns=__import__('openpyxl.styles',fromlist=['x']).__dict__.copy(); ns.update(re=__import__('re'),json=json,pd=pd)
exec(src[src.index('PII='):src.index('Q=D;')],ns)
clean,hdrrow,put=ns['clean'],ns['hdrrow'],ns['put']
from openpyxl import Workbook
rows=[]
for d in ['raw_2026-07','raw_2026-08','raw_2026-09','raw_2026-10']:
    for f in sorted(glob.glob(d+'/*.jsonl.gz')):
        for l in gzip.open(f,'rt'):
            if 'TATAAIG' not in l[:3000]: continue
            e=json.loads(l)
            if e.get('ProviderCode')!='TATAAIG': continue
            cp=row_for(e).get('carrier_policy_no')
            if not cp: continue
            lg=e['TransactionSyncLogs'][0]
            rows.append([e['ClientRequestTime'][:10],e['ClientRequestTime'],e['TransactionType'],cp,e['TraceId'],e['ClientRequestId'],lg['SyncUrl'],lg['SyncStatus'],
                         clean(e['TransRequest']),clean(lg['SyncRequest']),clean(lg['SyncResponse']),clean(e.get('TransResponse') or lg['TransResponse'])])
rows.sort(key=lambda r:r[1])
wb=Workbook(); ws=wb.active; ws.title='Tata CarrierPolicyNo Cases'
hdrrow(ws,1,['Date','Call time','Txn type','CarrierPolicyNo','TraceId','ClientRequestId','Carrier endpoint','Sync status','Fibe → InsureMO request','InsureMO → Insurer request','Insurer response','InsureMO response'])
for i,r in enumerate(rows,2): put(ws,i,r)
for j,w in enumerate([11,20,8,16,34,38,32,9,60,60,60,60],1): ws.column_dimensions[chr(64+j)].width=w
ws.freeze_panes='E2'
wb.save('out10/Tata_CarrierPolicyNo_Cases_with_Logs_Jul-Oct2026.xlsx'); print(len(rows))
