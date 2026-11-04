import json,requests,pickle,collections,datetime
import pandas as pd
from q import q
from extract import row_for
t=open('tok.txt').read().strip(); H={'Authorization':'Bearer '+t}
def pol_sys():
    out=[];pg=1
    while True:
        body={"Conditions":{},"FuzzyConditions":{},"OrFuzzyConditions":{},"FromRangeConditions":{"IssueDate":"2026-10-01T00:00:00"},"ToRangeConditions":{"IssueDate":"2026-10-31T23:59:59"},"PageNo":pg,"PageSize":1000,"SortField":"IssueDate","SortType":"asc","Module":"Policy"}
        d=requests.post('https://fibein-in-2.insuremo.com/api/platform/proposal/v1/queryPolicy',json=body,headers=H,timeout=120).json()
        docs=[x for r in d['Results'] for x in r['EsDocs']]; out+=docs
        if len(docs)<1000: break
        pg+=1
    return out
def pull(prov,tt):
    els=[];page=1
    while True:
        s,d=q({'providerCode':prov,'transactionType':tt,'clientRequestTimeFrom':'2026/10/01','clientRequestTimeTo':'2026/10/31'},page,1000)
        els+=d.get('ElementsInCurrentPage',[])
        if page*1000>=d.get('TotalElements',0): break
        page+=1
    return els
sysd=pol_sys(); print('policy system Oct',len(sysd),collections.Counter((x['CarrierCode'],x['PolicyStatus']) for x in sysd))
raw={'DIGIT':pull('DIGIT',2003),'TATAAIG':pull('TATAAIG',2003),'IL':pull('IL',2001)}
print({k:len(v) for k,v in raw.items()})
pickle.dump((sysd,raw),open('oct_issuance_raw.pkl','wb'))
