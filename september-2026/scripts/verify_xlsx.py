import openpyxl,pickle,sys,warnings
warnings.filterwarnings('ignore')
path=sys.argv[1]
EXP=pickle.load(open('xl_expected.pkl','rb'))
wb=openpyxl.load_workbook(path,data_only=True)
bad=[];none=0;errs=[]
for (sh,cell),e in EXP.items():
    v=wb[sh][cell].value
    if isinstance(v,str) and v.startswith('#') or (isinstance(v,str) and v.startswith('Err:')):
        errs.append((sh,cell,v)); continue
    if v is None: none+=1; bad.append((sh,cell,v,e)); continue
    if e is None: continue
    if isinstance(e,(int,float)) and not isinstance(e,bool):
        try:
            if abs(float(v)-float(e))>max(0.01,abs(e)*1e-6): bad.append((sh,cell,v,e))
        except Exception: bad.append((sh,cell,v,e))
    else:
        if str(v)!=str(e): bad.append((sh,cell,v,e))
print('formula cells checked',len(EXP),'| mismatches',len(bad),'| errors',len(errs),'| empty',none)
for b in bad[:40]: print('MISMATCH',b)
for b in errs[:20]: print('ERROR',b)
