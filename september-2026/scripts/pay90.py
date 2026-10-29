import json,requests,collections,datetime,re,os
t=requests.post('https://fibein-in-2.insuremo.com/cas/ebao/v2/json/tickets',json={"username":os.environ['INSUREMO_USER'],"password":os.environ['INSUREMO_PASS']},timeout=30).json()['access_token']
open('tok.txt','w').write(t)
from q import q
from extract import row_for
today=datetime.date.today(); frm=today-datetime.timedelta(days=90)
def js(s):
    try: return json.loads(s) if isinstance(s,str) else (s or {})
    except Exception: return {}
def pull(prov,tt):
    els=[];page=1
    while True:
        s,d=q({'providerCode':prov,'transactionType':tt,'clientRequestTimeFrom':frm.strftime('%Y/%m/%d'),'clientRequestTimeTo':today.strftime('%Y/%m/%d')},page,1000)
        els+=d.get('ElementsInCurrentPage',[])
        if page*1000>=d.get('TotalElements',0): break
        page+=1
    return els
def emsg(lg):
    r=js(lg['SyncResponse']); m=r.get('ErrorMessage') or r.get('message_txt') or (r.get('detail') or {}).get('message_txt') or ''
    if not m and 'Premium mismatch' in (lg['SyncResponse'] or ''): m='Premium mismatch while Policy issuance'
    if not m: m=str(r.get('Message') or r.get('message') or '')[:120]
    return re.sub(r'\d{5,}','#',str(m))[:110]
out={}
for name,prov,tt in [('ICICI Lombard','IL',2001),('Go Digit','DIGIT',2003),('Tata AIG','TATAAIG',2003)]:
    els=pull(prov,tt); g=collections.defaultdict(list)
    for e in els:
        tr=js(e['TransRequest']); pay=(tr.get('PolicyPaymentInfoList') or [{}])[0]; tx=pay.get('TransactionNo')
        if not tx: continue
        lg=e['TransactionSyncLogs'][0]; ok=bool(row_for(e).get('carrier_policy_no'))
        g[tx].append((e['ClientRequestTime'],ok,emsg(lg),pay.get('Amount') or tr.get('GrossPremium'),e['TraceId'],e['ClientRequestId']))
    out[name]=g
    never=[k for k,v in g.items() if not any(x[1] for x in v)]
    multiday=[k for k,v in g.items() if len({x[0][:10] for x in v})>1]
    md_never=[k for k in multiday if k in never]
    print(f"{name}: calls={len(els)} payment_txns={len(g)} txns_never_issued={len(never)} multi-attempt={sum(1 for v in g.values() if len(v)>1)} multi-day={len(multiday)} multi-day_never_issued={len(md_never)}")
    for k in sorted(multiday,key=lambda k:-len(g[k]))[:8]:
        v=sorted(g[k]); print('  ',k,len(v),'attempts',len({x[0][:10] for x in v}),'days',v[0][0][:10],'→',v[-1][0][:10],'amt',v[0][3],'issued' if any(x[1] for x in v) else 'NOT ISSUED',Counter:=collections.Counter(x[2] for x in v if not x[1]).most_common(1))
import pickle; pickle.dump({k:dict(v) for k,v in out.items()},open('pay90.pkl','wb'))
