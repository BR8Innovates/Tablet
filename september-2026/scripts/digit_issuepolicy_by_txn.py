import json,requests,collections,os
import pandas as pd
t=requests.post('https://fibein-in-2.insuremo.com/cas/ebao/v2/json/tickets',json={"username":os.environ['INSUREMO_USER'],"password":os.environ['INSUREMO_PASS']},timeout=30).json()['access_token']
open('tok.txt','w').write(t)
from q import q
src=open('last10_logs.py').read()
ns=__import__('openpyxl.styles',fromlist=['x']).__dict__.copy(); ns.update(re=__import__('re'),json=json,pd=pd)
exec(src[src.index('PII='):src.index('Q=D;')],ns); clean,hdrrow,put=ns['clean'],ns['hdrrow'],ns['put']
TX='FIB_pay_TqDRsBy73eocFy'
allr=[]
for frm,to in [('2026/10/01','2026/10/31')]:
    s,d=q({'providerCode':'DIGIT','transactionType':2003,'clientRequestTimeFrom':frm,'clientRequestTimeTo':to},1,1000)
    print('digit 2003 oct',d.get('TotalElements')); allr+=d.get('ElementsInCurrentPage',[])
def js(s):
    try: return json.loads(s) if isinstance(s,str) else (s or {})
    except Exception: return {}
prop=None
for e in allr:
    if TX in (e['TransRequest'] or '') : prop=js(e['TransRequest']).get('CarrierProposalNo')
print('proposal',prop and prop[:20])
hits=[e for e in allr if TX in (e['TransRequest'] or '') or (prop and prop in (e['TransRequest'] or ''))]
hits.sort(key=lambda e:e['ClientRequestTime']); print(len(hits))
rows=[]
for e in hits:
    lg=e['TransactionSyncLogs'][0]; r=js(lg['SyncResponse']); tr=js(e['TransRequest']); pay=tr['PolicyPaymentInfoList'][0]
    res=js(lg['TransResponse']).get('Result',{})
    rows.append([e['ClientRequestTime'][:10],e['ClientRequestTime'],pay['TransactionNo'],pay['Amount'],r.get('ErrorMessage') or ('Success' if res.get('Success') in('true',True) else ''),r.get('ErrorCode'),res.get('Success'),
        e['TraceId'],e['ClientRequestId'],lg['SyncUrl'],lg['SyncStatus'],lg['SyncStartTime'],lg['SyncEndTime'],clean(e['TransRequest']),clean(lg['SyncRequest']),clean(lg['SyncResponse']),clean(lg['TransResponse'])])
from openpyxl import Workbook
wb=Workbook(); s=wb.active; s.title='Summary'
hdrrow(s,1,['Date','Requests','Digit result(s)'])
by=collections.defaultdict(list)
for r in rows: by[r[0]].append(r)
for i,(d,g) in enumerate(sorted(by.items()),2): put(s,i,[d,len(g),'; '.join(sorted({x[4] for x in g}))])
n=len(by)+3; put(s,n,['Total',len(rows),'']); put(s,n+1,['Payment TransactionNo',TX,'']); put(s,n+2,['Time span',f'{rows[0][1]} → {rows[-1][1]}' if rows else '',''])
s.column_dimensions['A'].width=24;s.column_dimensions['B'].width=34;s.column_dimensions['C'].width=70
ws=wb.create_sheet('Digit Issue Policy Logs'); hdrrow(ws,1,['Date','Call time','Payment TransactionNo','Amount','Digit result','Digit ErrorCode','InsureMO Success','TraceId','ClientRequestId','Endpoint','Sync status','Sync start','Sync end','Fibe → InsureMO request','InsureMO → Digit request','Digit response','InsureMO response'])
for i,r in enumerate(rows,2): put(ws,i,r)
for j,w in enumerate([11,20,26,9,50,9,9,34,38,28,8,20,20,60,60,60,60],1): ws.column_dimensions[chr(64+j)].width=w
ws.freeze_panes='D2'
wb.save('out10/Digit_IssuePolicy_FIB_pay_TqDRsBy73eocFy_Logs.xlsx')
for r in rows: print(r[1],r[4],r[7],r[8])
