import json,requests,pickle,collections
import pandas as pd
from q import q
from extract import row_for
t=open('tok.txt').read().strip(); H={'Authorization':'Bearer '+t}
els=[]
for a,b in [('2026/07/01','2026/07/31'),('2026/08/01','2026/08/31'),('2026/09/01','2026/09/30'),('2026/10/01','2026/10/31'),('2026/11/01','2026/11/04')]:
    page=1
    while True:
        s,d=q({'providerCode':'IL','transactionType':2001,'clientRequestTimeFrom':a,'clientRequestTimeTo':b},page,1000)
        got=d.get('ElementsInCurrentPage',[]); els+=got
        if page*1000>=d.get('TotalElements',0): break
        page+=1
    print(a,d.get('TotalElements'))
rows=[]
for e in els:
    x=row_for(e)
    if x.get('carrier_policy_no'):
        lg=e['TransactionSyncLogs'][0]
        rows.append(dict(CarrierPolicyNo=x['carrier_policy_no'],IssueDate=e['ClientRequestTime'].replace('T',' ')[:16],Premium=x.get('req_gross') or x.get('premium'),Vehicle_Type=x['product'],Registration_No=x['reg'],PlanType=x['plantype'],Carrier_Status=x.get('policy_status') or '',TraceId=e['TraceId'],ClientRequestId=e['ClientRequestId']))
df=pd.DataFrame(rows).sort_values('IssueDate'); print('calls with CPN',len(df),'unique',df.CarrierPolicyNo.nunique())
df1=df.drop_duplicates('CarrierPolicyNo',keep='first').reset_index(drop=True)
df1['Premium']=pd.to_numeric(df1.Premium,errors='coerce')
# policy system check: any carrier 10 policy / these CPNs
body={"Conditions":{"CarrierCode":"10"},"FuzzyConditions":{},"OrFuzzyConditions":{},"PageNo":1,"PageSize":1000,"Module":"Policy"}
d=requests.post('https://fibein-in-2.insuremo.com/api/platform/proposal/v1/queryPolicy',json=body,headers=H,timeout=120).json()
docs=[x for r in d['Results'] for x in r['EsDocs']]; print('policy system carrier 10 docs',len(docs))
df1['PolicyNo']=''
pickle.dump((df,df1),open('il_since_start.pkl','wb'))
print(df1.groupby(df1.IssueDate.str[:7]).agg(n=('CarrierPolicyNo','size'),prem=('Premium','sum')),df1.Vehicle_Type.value_counts().to_dict(),df1.Premium.isna().sum())
