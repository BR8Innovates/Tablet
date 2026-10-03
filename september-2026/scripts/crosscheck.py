import gzip,glob,json,collections,openpyxl,warnings
warnings.filterwarnings('ignore')
def run(month):
    calls=collections.Counter(); succ=collections.Counter(); regs=collections.defaultdict(set); priced=collections.defaultdict(set)
    pol=collections.defaultdict(dict); n=0; ids=set()
    for f in sorted(glob.glob(f'raw_{month}/*.jsonl.gz')):
        for line in gzip.open(f,'rt'):
            r=json.loads(line); n+=1; ids.add(r['ListId'])
            t=r['TransactionType']; p=r['ProviderCode']
            lg=r['TransactionSyncLogs'][0]
            req=json.loads(r['TransRequest']); 
            try: tr=json.loads(lg['TransResponse'])
            except Exception: tr={}
            res=tr.get('Result') if isinstance(tr.get('Result'),dict) else {}
            if t in (1001,4001):
                prod='2W' if req.get('ProductType')==2 else '4W'
                ok=False
                for blk in ([res]+(res.get('Multiplan') or [])):
                    if isinstance(blk,dict):
                        for k in ('DuePremium','GrossPremium'):
                            try:
                                if float(str(blk.get(k)).replace(',',''))>0 and not blk.get('ErrorMessage'): ok=True
                            except Exception: pass
                calls[(p,prod)]+=1; succ[(p,prod)]+=ok
                reg=req['PolicyLobList'][0]['PolicyRiskList'][0].get('RegistrationNo') if req.get('PolicyLobList') else None
                if reg: regs[p].add(reg); 
                if reg and ok: priced[p].add(reg)
            if res.get('CarrierPolicyNo') and ((p=='IL' and t==2001) or (p in('DIGIT','TATAAIG') and t==2003)):
                pol[p][res['CarrierPolicyNo']]=1
    return n,len(ids),calls,succ,regs,priced,pol
for m in ['2026-09','2026-08']:
    n,ni,calls,succ,regs,priced,pol=run(m)
    print('=====',m,'rows',n,'distinct ListId',ni)
    tot=sum(calls.values()); ts=sum(succ.values()); print('quote calls',tot,'success',ts,'failed',tot-ts)
    for k in sorted(calls): print(' ',k,calls[k],succ[k],calls[k]-succ[k])
    print(' leads(unique regs, per carrier)',{p:len(v) for p,v in regs.items()},' priced',{p:len(v) for p,v in priced.items()})
    print(' policies per carrier',{p:len(v) for p,v in pol.items()},'total',sum(len(v) for v in pol.values()))
# compare with workbook
wb=openpyxl.load_workbook('lo_out/Fibe_Carrier_Error_Analysis_September_2026.xlsx',data_only=True)
ws=wb['Executive Summary']
print('WORKBOOK Sep exec summary:')
for r in range(5,12): print(' ',ws.cell(r,1).value,ws.cell(r,2).value,ws.cell(r,3).value,ws.cell(r,4).value,ws.cell(r,5).value)
