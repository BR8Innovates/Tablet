import json,requests,os
import pandas as pd
from openpyxl import Workbook
t=requests.post('https://fibein-in-2.insuremo.com/cas/ebao/v2/json/tickets',json={"username":os.environ['INSUREMO_USER'],"password":os.environ['INSUREMO_PASS']},timeout=30).json()['access_token']
open('tok.txt','w').write(t)
from q import q
from extract import row_for
src=open('last10_logs.py').read()
ns=__import__('openpyxl.styles',fromlist=['x']).__dict__.copy(); ns.update(re=__import__('re'),json=json,pd=pd)
exec(src[src.index('PII='):src.index('Q=D;')],ns); clean,hdrrow,put=ns['clean'],ns['hdrrow'],ns['put']
def js(s):
    try: return json.loads(s) if isinstance(s,str) else (s or {})
    except Exception: return {}
s,d=q({'providerCode':'TATAAIG','transactionType':2003,'clientRequestTimeFrom':'2026/10/23','clientRequestTimeTo':'2026/10/25'},1,1000)
els=sorted(d.get('ElementsInCurrentPage',[]),key=lambda e:e['ClientRequestTime']); print(d.get('TotalElements'))
rows=[]
for e in els:
    lg=e['TransactionSyncLogs'][0]; p=js(e['TransRequest']).get('CarrierProposalNo'); ok=bool(row_for(e).get('carrier_policy_no'))
    s2,c=q({'providerCode':'TATAAIG','transactionType':2001,'clientRequestTimeFrom':'2026/10/16','clientRequestTimeTo':'2026/10/25'},1,1000)
    veh=['']*6;cdt=''
    for ce in c.get('ElementsInCurrentPage',[]):
        if row_for(ce).get('res_proposal_no')==p:
            r=js(ce['TransRequest'])['PolicyLobList'][0]['PolicyRiskList'][0]; x=row_for(ce)
            veh=[r.get('RegistrationNo'),x['product'],r.get('RTOCode'),r.get('RegistrationDate'),r.get('VehicleMaincode'),r.get('ChassisNo')]; cdt=ce['ClientRequestTime']
    try: j=js(lg['SyncResponse']); j=j.get('detail',j); m=j.get('message_txt') or j.get('ErrorMessage') or ''
    except Exception: m=''
    rows.append([e['ClientRequestTime'][:10],e['ClientRequestTime'],'Success' if ok else 'Failed',m,p]+veh+[cdt,e['TraceId'],e['ClientRequestId'],lg['SyncUrl'],lg['SyncStatus'],lg['SyncStartTime'],lg['SyncEndTime'],
        clean(e['TransRequest']),clean(lg['SyncRequest']),clean(lg['SyncResponse']),clean(lg['TransResponse'])])
wb=Workbook(); ws=wb.active; ws.title='Tata Issue Policy 23-25Oct'
hdrrow(ws,1,['Date','Call time','Result','Insurer error','CarrierProposalNo','Registration No','Vehicle type','RTO','Registration date','Vehicle code','Chassis No','Create-quote time','TraceId','ClientRequestId','Carrier endpoint','Sync status','Sync start','Sync end','Fibe → InsureMO request','InsureMO → Insurer request','Insurer response','InsureMO response'])
for i,r in enumerate(rows,2): put(ws,i,r)
for j,w in enumerate([11,20,9,45,18,14,9,8,12,10,20,20,34,38,30,8,20,20,60,60,60,60],1): ws.column_dimensions[chr(64+j)].width=w
ws.freeze_panes='F2'
wb.save('out10/Tata_IssuePolicy_Logs_23-25Oct2026.xlsx'); print(len(rows),[r[2] for r in rows],[r[5:8] for r in rows])
