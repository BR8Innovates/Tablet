import pickle,json,collections
import pandas as pd
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
from extract import row_for
sysd,raw=pickle.load(open('oct_issuance_raw.pkl','rb'))
def js(s):
    try: return json.loads(s) if isinstance(s,str) else (s or {})
    except Exception: return {}
ad=[]   # adapter rows with CarrierPolicyNo
for prov,els in raw.items():
    for e in els:
        x=row_for(e)
        if not x.get('carrier_policy_no'): continue
        pr=x.get('premium') or x.get('req_gross')
        if prov=='TATAAIG': pr=float(js(e['TransRequest'])['PolicyPaymentInfoList'][0]['Amount'])
        ad.append(dict(prop=js(e['TransRequest']).get('CarrierProposalNo'),prov=prov,cpn=x['carrier_policy_no'],time=e['ClientRequestTime'],premium=pr,pno=x.get('policy_no'),status=x.get('policy_status'),reg=x['reg'],product=x['product'],trace=e['TraceId']))
A=pd.DataFrame(ad); print(len(A),A.groupby('prov').cpn.nunique().to_dict())
A=A.sort_values('time').drop_duplicates(['prov','cpn'],keep='first')   # first call = issuance
t=lambda s:datetime.fromisoformat(s)
INS={'33':('Go Digit','DIGIT'),'25':('Tata AIG','TATAAIG')}
rowsA=[];used=set()
for x in sorted(sysd,key=lambda z:z['IssueDate']):
    _,code=INS[x['CarrierCode']]; cp=x.get('CarrierPolicyNo'); c=A[A.prov==code]
    if cp: m=c[c.cpn==cp]
    elif x.get('CarrierProposalNo') and (c.prop==x['CarrierProposalNo']).any(): m=c[c.prop==x['CarrierProposalNo']]
    else: m=c[(abs(c.premium.astype(float)-x['DuePremium'])<0.5)&(c.time.map(lambda s:abs((t(s)-t(x['IssueDate'])).total_seconds())<=30))&(~c.cpn.isin(used))]
    mm=m.iloc[0] if len(m)>=1 else None
    if mm is not None: used.add(mm.cpn)
    rowsA.append(dict(PolicyNo=x['PolicyNo'],InsurerCode=int(x['CarrierCode']),Insurer=code,CarrierPolicyNo=(mm.cpn if mm is not None else cp) or '',IssueDate=x['IssueDate'].replace('T',' ')[:16],Premium=round(float(x['DuePremium']),2),
        Vehicle_Type=(mm['product'] if mm is not None else ''),Registration_No=(mm.reg if mm is not None else ''),Carrier_Status=(mm.status if mm is not None and code=='DIGIT' else '')))
A0=pd.DataFrame(rowsA); A1=A0[A0.CarrierPolicyNo!=''].reset_index(drop=True); C1=A0[A0.CarrierPolicyNo==''].reset_index(drop=True)
print('C1',len(C1)); print('sheet A',len(A1),A1.Insurer.value_counts().to_dict(),'missing CPN',(A1.CarrierPolicyNo=='').sum())
pn_cpn=set(A1.CarrierPolicyNo)
B=A[~A.cpn.isin(pn_cpn)]
B1=pd.DataFrame([dict(InsurerCode={'IL':10,'DIGIT':33,'TATAAIG':25}[r.prov],Insurer=r.prov,CarrierPolicyNo=r.cpn,IssueDate=r.time.replace('T',' ')[:16],Premium=round(float(r.premium),2) if pd.notna(r.premium) else None,Vehicle_Type=r.product,Registration_No=r.reg,Carrier_Status=(r.status or '') if r.prov=='DIGIT' else '',TraceId=r.trace) for r in B.itertuples()]).sort_values('IssueDate')
print('sheet B',len(B1),B1.Insurer.value_counts().to_dict(),'premium',B1.Premium.sum(), 'sheetA premium',A1.Premium.sum())
pickle.dump((A1,B1),open('oct_lists.pkl','wb'))
NAVY='1F3864'; BD=Border(*(Side(style='thin',color='BFBFBF'),)*4)
wb=Workbook(); first=True
def sheet(name,df,cols,heads):
    global first
    ws=wb.active if first else wb.create_sheet(); first=False; ws.title=name
    for j,h in enumerate(heads,1):
        c=ws.cell(row=1,column=j,value=h); c.font=Font(name='Arial',bold=True,color='FFFFFF',size=10); c.fill=PatternFill('solid',fgColor=NAVY); c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True); c.border=BD
    for i,r in enumerate(df.itertuples(index=False),2):
        for j,k in enumerate(cols,1):
            c=ws.cell(row=i,column=j,value=getattr(r,k)); c.font=Font(name='Arial',size=10); c.border=BD
            if k=='Premium': c.number_format='#,##0.00'
    n=len(df)+1; pc=cols.index('Premium')+1; cc=cols.index('CarrierPolicyNo')+1
    ws.cell(row=n+1,column=1,value='TOTAL').font=Font(name='Arial',bold=True)
    ws.cell(row=n+1,column=cc,value=f'=COUNTA({chr(64+cc)}2:{chr(64+cc)}{n})').font=Font(name='Arial',bold=True)
    c=ws.cell(row=n+1,column=pc,value=f'=SUM({chr(64+pc)}2:{chr(64+pc)}{n})'); c.font=Font(name='Arial',bold=True); c.number_format='#,##0.00'
    for j in range(1,len(cols)+1): ws.column_dimensions[chr(64+j)].width=[36,12,11,34,17,12,12,15,16,34][j-1]
    ws.freeze_panes='A2'; ws.sheet_view.showGridLines=False
sheet('PolicyNo + CarrierPolicyNo',A1,['PolicyNo','InsurerCode','Insurer','CarrierPolicyNo','IssueDate','Premium','Vehicle_Type','Registration_No','Carrier_Status'],['PolicyNo','InsurerCode','Insurer','CarrierPolicyNo','IssueDate','Premium','Vehicle Type','Registration No','Carrier Status (Digit)'])
sheet('PolicyNo only',C1,['PolicyNo','InsurerCode','Insurer','CarrierPolicyNo','IssueDate','Premium','Vehicle_Type','Registration_No','Carrier_Status'],['PolicyNo','InsurerCode','Insurer','CarrierPolicyNo','IssueDate','Premium','Vehicle Type','Registration No','Carrier Status (Digit)'])
sheet('CarrierPolicyNo only',B1,['InsurerCode','Insurer','CarrierPolicyNo','IssueDate','Premium','Vehicle_Type','Registration_No','Carrier_Status','TraceId'],['InsurerCode','Insurer','CarrierPolicyNo','IssueDate','Premium','Vehicle Type','Registration No','Carrier Status (Digit)','TraceId'])
ws=wb.create_sheet('Notes'); ws.sheet_view.showGridLines=False
for i,s in enumerate(['October 2026 policy issuance (1–31 Oct; data pulled 4 Nov 2026)','',
 'Sheet 1: policies that have BOTH a PolicyNo (InsureMO policy system, queryPolicy by IssueDate) and a CarrierPolicyNo. Tata CarrierPolicyNo is joined from the adapter issue-policy response via CarrierProposalNo (the policy system holds none for Tata); a CarrierPolicyNo received on a later retry still counts.',
 'Sheet 2: policies with a PolicyNo in the policy system but NO CarrierPolicyNo (Tata: Tata rejected issuance - Product Name is Invalid - yet InsureMO holds the policy). Sheet 3: policies with ONLY a CarrierPolicyNo - ICICI Lombard (the policy system has no ICICI policies). IssueDate = first issuing call time; Premium from the call.',
 'CarrierPolicyNo counted once (first call) when the same policy appears in repeated calls.'],1):
    c=ws.cell(row=i,column=1,value=s); c.alignment=Alignment(wrap_text=True,vertical='top'); c.font=Font(name='Arial',size=14 if i==1 else 10,bold=(i==1))
ws.column_dimensions['A'].width=130
wb.save('out10/October_2026_Policies_Issued.xlsx'); print('saved')
