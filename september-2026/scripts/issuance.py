"""Issuance table from raw 2001/2003 records (no PII)."""
import gzip,glob,json,sys,pickle
from extract import jl,first_risk,num,PROV
def build(month):
    out=[]
    for f in sorted(glob.glob(f'raw_{month}/*.jsonl.gz')):
        for l in gzip.open(f,'rt'):
            r=json.loads(l)
            if r['TransactionType'] not in (2001,2003): continue
            lg=r['TransactionSyncLogs'][0] if r['TransactionSyncLogs'] else {}
            req=jl(r['TransRequest']) or {}; sr=jl(lg.get('SyncResponse')); tr=jl(lg.get('TransResponse')) or {}
            res=tr.get('Result') if isinstance(tr.get('Result'),dict) else {}
            risk=first_risk(req)
            pay=(req.get('PolicyPaymentInfoList') or [{}])[0]
            prov=r['ProviderCode']
            raw_policy=None
            if isinstance(sr,dict):
                if prov=='DIGIT': raw_policy=sr.get('policyNumber')
                elif prov=='TATAAIG' and isinstance(sr.get('data'),list) and sr['data'] and isinstance(sr['data'][0],dict): raw_policy=sr['data'][0].get('policy_no')
                elif prov=='IL': raw_policy=sr.get('PolicyNo') or sr.get('PolicyNumber')
            out.append(dict(month=month,time=r['ClientRequestTime'],date=r['ClientRequestTime'][:10],provider=PROV[prov],txn=r['TransactionType'],url=lg.get('SyncUrl'),
              product={2:'2W',1:'4W'}.get(req.get('ProductType'),{'IND-2W':'2W','IND-4W':'4W'}.get(r['CountryCode'],None)),
              reg=risk.get('RegistrationNo') or '',plantype=str(req.get('PlanType','')),
              proposal_no=req.get('CarrierProposalNo') or req.get('CarrierProposalId') or '',
              res_proposal_no=res.get('CarrierProposalNo') or res.get('ApplicationId') or '',
              carrier_policy_no=res.get('CarrierPolicyNo') or '',policy_no=raw_policy or '',
              policy_status=res.get('CarrierPolicyStatus') or res.get('StatusCode') or '',
              req_gross=num(req.get('GrossPremium')),pay_amt=num(pay.get('Amount')),
              res_gross=num(res.get('GrossPremium')),res_due=num(res.get('DuePremium')),
              err=res.get('ErrorMessage') or res.get('CarrierErrorMessage') or res.get('IMOErrorMessage') or '',
              crid=r['ClientRequestId'],trace=r['TraceId'],listid=r['ListId'],
              mobile_hash=hash(( (req.get('PolicyCustomerList') or [{}])[0].get('ContactMobile') )) if req.get('PolicyCustomerList') else None))
    return out
if __name__=='__main__':
    m=sys.argv[1]; o=build(m); pickle.dump(o,open(f'iss_{m}.pkl','wb')); print(m,len(o))
