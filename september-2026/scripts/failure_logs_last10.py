import pickle,json,re
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment,Font,PatternFill,Border,Side
D=pd.read_pickle('last10_quotes.pkl'); R=pickle.load(open('last10_failed_records.pkl','rb'))
PII=re.compile(r'(mobile|phone|e-?mail|first_?name|last_?name|middle_?name|full_?name|^name$|holder_?name|customer_?name|nominee|dob|date_?of_?birth|address|pan$|aadhaar|gender_?code|salutation|contact)',re.I)
def redact(o):
    if isinstance(o,dict): return {k:('[REDACTED]' if PII.search(k) and not isinstance(v,(dict,list)) and v not in ('',None) else redact(v)) for k,v in o.items()}
    if isinstance(o,list): return [redact(x) for x in o]
    return o
def clean(s):
    if s is None: return ''
    if not isinstance(s,str): s=json.dumps(s,ensure_ascii=False)
    try: s2=json.dumps(redact(json.loads(s)),ensure_ascii=False)
    except Exception: s2=s
    return s2 if len(s2)<=32000 else s2[:32000]+' …[truncated]'
NAVY='1F3864'; B=Border(*(Side(style='thin',color='BFBFBF'),)*4)
def hdrrow(ws,row,hdr):
    for j,h in enumerate(hdr,1):
        c=ws.cell(row=row,column=j,value=h); c.font=Font(name='Arial',bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor=NAVY); c.alignment=Alignment(wrap_text=True,horizontal='center',vertical='center'); c.border=B
def put(ws,row,vals,fmt={}):
    for j,v in enumerate(vals,1):
        c=ws.cell(row=row,column=j,value=v); c.font=Font(name='Arial',size=10); c.border=B; c.alignment=Alignment(wrap_text=True,vertical='top')
        if j in fmt: c.number_format=fmt[j]
Q=D; F=Q[(~Q.ok)]; F=F[F.reg!='']
summ=[]; logs={}
for p in ['ICICI Lombard','Go Digit','Tata AIG']:
    for pr in ['2W','4W']:
        a=Q[(Q.provider==p)&(Q['product']==pr)]; fa=a[~a.ok]; g=F[(F.provider==p)&(F['product']==pr)]
        top=g.groupby('err_n').agg(n=('trace','size'),v=('reg','nunique')).sort_values(['n','v'],ascending=False).head(5)
        for rank,(err,r) in enumerate(top.iterrows(),1):
            ge=g[g.err_n==err]; cat=ge.cat.iloc[0]
            veh=ge.groupby('reg').agg(att=('trace','size'),last=('time','max')).sort_values(['att','last'],ascending=[False,False]).head(5)
            summ.append(dict(p=p,pr=pr,rank=rank,err=err,cat=cat,n=int(r.n),v=int(r.v),share=r.n/len(fa),shown=len(veh),calls=len(a),fail=len(fa)))
            for reg,x in veh.iterrows():
                t=ge[ge.reg==reg].sort_values('time').iloc[-1]; e=R[t.trace]; lg=e['TransactionSyncLogs'][0]
                assert e['TraceId']==t.trace
                logs.setdefault(p,[]).append([pr,rank,err,reg,int(x.att),t.plantype,t.plancode,e['ClientRequestTime'],e['TraceId'],e['ClientRequestId'],lg['SyncUrl'],lg['SyncStatus'],lg['SyncStartTime'],lg['SyncEndTime'],
                    clean(e['TransRequest']),clean(lg['SyncRequest']),clean(lg['SyncResponse']),clean(lg['TransResponse'])])
LH=['Product','Error rank','Error (normalised)','Registration No','Attempts with this error','PlanType','PlanCode','Call time','TraceId','ClientRequestId','Carrier endpoint','Carrier sync status','Sync start','Sync end','Fibe → InsureMO request','InsureMO → Carrier request','Carrier response','InsureMO response']
W=[8,7,55,14,10,9,9,20,34,38,34,9,20,20,60,60,60,60]
NOTE=('Window: 12–21 Oct 2026 (10 days), InsureMO production integration adapter (queryTransactionPaged). Failure = quote call (1001/4001) with no premium or with an error message. '
      'Top 5 errors per product by occurrences; up to 5 unique vehicles per error (most attempts, latest failed call shown). Customer personal data (name, phone, email, DOB, address, PAN) is redacted; vehicle identifiers kept. '
      'Where fewer than 5 vehicles / errors exist in the window the list is complete, nothing is padded.')
def book(path,title,insurers):
    wb=Workbook(); ws=wb.active; ws.title='Index'
    ws['A1']=title; ws['A1'].font=Font(name='Arial',size=14,bold=True,color=NAVY)
    ws['A2']=NOTE; ws.merge_cells('A2:I2'); ws['A2'].alignment=Alignment(wrap_text=True,vertical='top'); ws.row_dimensions[2].height=64; ws['A2'].font=Font(name='Arial',size=10,color='595959')
    hdrrow(ws,4,['Insurer','Product','Rank','Error (normalised)','Category','Occurrences','Unique vehicles in window','Vehicles shown','Share of product failures'])
    r=5
    for s in summ:
        if s['p'] in insurers:
            put(ws,r,[s['p'],s['pr'],s['rank'],s['err'],s['cat'],s['n'],s['v'],s['shown'],s['share']],{6:'#,##0',7:'#,##0',9:'0.0%'}); r+=1
    for k,w in zip('ABCDEFGHI',[15,9,6,70,24,13,13,10,13]): ws.column_dimensions[k].width=w
    ws.sheet_view.showGridLines=False
    for p in insurers:
        for pr in ['2W','4W']:
            rows=[x for x in logs.get(p,[]) if x[0]==pr]
            w=wb.create_sheet(f'{p.split()[0]} {pr} Logs'); hdrrow(w,1,LH)
            for i,x in enumerate(rows,2): put(w,i,x)
            for j,wd in enumerate(W,1): w.column_dimensions[chr(64+j)].width=wd
            w.freeze_panes='E2'
    wb.save(path)
import os; os.makedirs('out10',exist_ok=True)
names={'ICICI Lombard':'ICICI_Lombard','Go Digit':'Go_Digit','Tata AIG':'Tata_AIG'}
for p,n in names.items(): book(f'out10/{n}_Failure_Logs_12-21Oct2026.xlsx',f'{p} — failed quote logs, top 5 errors × ≥5 vehicles (12–21 Oct 2026)',[p])
book('out10/All_Insurers_Failure_Logs_12-21Oct2026.xlsx','All insurers — failed quote logs, top 5 errors × ≥5 vehicles (12–21 Oct 2026)',list(names))
# summary workbook
wb=Workbook(); ws=wb.active; ws.title='Failure Summary'
hdrrow(ws,1,['Insurer','Product','Quote calls','Failed calls','Failure rate'])
r=2
seen=set()
for s in summ:
    k=(s['p'],s['pr'])
    if k in seen: continue
    seen.add(k); put(ws,r,[s['p'],s['pr'],s['calls'],s['fail'],f'=D{r}/C{r}'],{3:'#,##0',4:'#,##0',5:'0.0%'}); r+=1
r+=1; hdrrow(ws,r,['Insurer','Product','Rank','Error','Category','Occurrences','Unique vehicles','Vehicles with logs','Share of failures']); r+=1
for s in summ:
    put(ws,r,[s['p'],s['pr'],s['rank'],s['err'],s['cat'],s['n'],s['v'],s['shown'],s['share']],{6:'#,##0',7:'#,##0',9:'0.0%'}); r+=1
for k,w in zip('ABCDEFGHI',[15,9,12,70,24,13,13,13,13]): ws.column_dimensions[k].width=w
wb.save('out10/Failure_Summary_12-21Oct2026.xlsx')
pd.DataFrame(summ).to_pickle('summ10.pkl')
print(pd.DataFrame(summ)[['p','pr','rank','n','v','shown','err']].to_string(max_colwidth=60))
