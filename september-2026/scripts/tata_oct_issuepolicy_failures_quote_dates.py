import gzip,json,glob,collections
import pandas as pd
from openpyxl import Workbook
from extract import row_for
src=open('last10_logs.py').read()
ns=__import__('openpyxl.styles',fromlist=['x']).__dict__.copy(); ns.update(re=__import__('re'),json=json,pd=pd)
exec(src[src.index('PII='):src.index('Q=D;')],ns); clean,hdrrow,put=ns['clean'],ns['hdrrow'],ns['put']
def js(s):
    if not isinstance(s,str): return s or {}
    try: return json.loads(s)
    except Exception: return {}
cq={};quotes=collections.defaultdict(list);fails=[]
for d in ['raw_2026-09','raw_2026-10']:
    for f in sorted(glob.glob(d+'/*.jsonl.gz')):
        for l in gzip.open(f,'rt'):
            e=json.loads(l)
            if e.get('ProviderCode')!='TATAAIG': continue
            t=e['TransactionType']
            if t in(1001,4001):
                x=row_for(e)
                if x['reg']: quotes[x['reg']].append((e['ClientRequestTime'],bool(x['ok']),x['plantype']))
            elif t==2001:
                x=row_for(e); p=x.get('res_proposal_no')
                if p:
                    risk=js(e['TransRequest'])['PolicyLobList'][0]['PolicyRiskList'][0]
                    cq[p]=(e['ClientRequestTime'],risk,x)
            elif t==2003 and f.startswith('raw_2026-10') and not row_for(e).get('carrier_policy_no'): fails.append(e)
print('oct failed issue calls',len(fails))
for r in quotes.values(): r.sort()
def msg(sr):
    j=js(sr); j=j.get('detail',j) if isinstance(j,dict) else {}
    return str(j.get('message_txt') or j.get('ErrorMessage') or '')[:200]
rows=[];nomatch=0
for e in sorted(fails,key=lambda e:e['ClientRequestTime']):
    lg=e['TransactionSyncLogs'][0]; p=js(e['TransRequest']).get('CarrierProposalNo')
    c=cq.get(p)
    if not c: nomatch+=1; reg=''; ctime='';v=['']*8; qf=ql=qlok=None;plan=''
    else:
        ctime,risk,x=c; reg=risk.get('RegistrationNo')
        v=[x['product'],risk.get('CarrierType'),risk.get('RTOCode'),risk.get('RegistrationDate'),risk.get('ManufactureYear'),risk.get('FuelType'),risk.get('VehicleMaincode'),risk.get('ChassisNo')]
        qs=[q for q in quotes.get(reg,[]) if q[0]<=ctime]
        qok=[q for q in qs if q[1]]
        qf=qs[0][0] if qs else None; ql=qs[-1][0] if qs else None; qlok=qok[-1][0] if qok else None
    rows.append([e['ClientRequestTime'][:10],e['ClientRequestTime'],msg(lg['SyncResponse']),p,reg]+v+[ctime[:10] if ctime else '',ctime,qf[:10] if qf else '',qf or '',qlok or '',ql or '',e['TraceId'],e['ClientRequestId'],lg['SyncUrl'],
        clean(e['TransRequest']),clean(lg['SyncRequest']),clean(lg['SyncResponse']),clean(lg['TransResponse'])])
H=['Issue-policy date','Issue-policy time','Insurer error','CarrierProposalNo','Registration No','Vehicle type','CarrierType','RTO','Registration date','Mfg year','Fuel code','Vehicle code','Chassis No',
   'Create-quote date','Create-quote time','First quote date','First quote time','Last successful quote before create-quote','Last quote before create-quote','TraceId','ClientRequestId','Carrier endpoint',
   'Fibe → InsureMO request','InsureMO → Insurer request','Insurer response','InsureMO response']
wb=Workbook(); s=wb.active; s.title='Summary'
cnt=collections.Counter(r[2] for r in rows)
hdrrow(s,1,['Insurer error (all calls, duplicates kept)','Calls','Unique proposals','Unique vehicles'])
for i,(er,n) in enumerate(cnt.items(),2):
    g=[r for r in rows if r[2]==er]; put(s,i,[er,n,len({r[3] for r in g}),len({r[4] for r in g})])
s.column_dimensions['A'].width=60
ws=wb.create_sheet('Oct Failed Issue Policy'); hdrrow(ws,1,H)
for i,r in enumerate(rows,2): put(ws,i,r)
for j,w in enumerate([11,20,45,18,14,9,9,8,12,12,8,10,20,11,20,11,20,20,20,34,38,30,60,60,60,60],1): ws.column_dimensions[chr(64+j) if j<=26 else 'A'].width=w
ws.freeze_panes='F2'
wb.save('out10/Tata_Oct_IssuePolicy_Failures_All_Calls_with_Quote_Dates.xlsx')
print(len(rows),'nomatch',nomatch,cnt); print(rows[0][:21])
