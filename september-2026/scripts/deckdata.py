import pickle,pandas as pd
from analysis import PROVIDERS
D=pickle.load(open('prep.pkl','rb'))
J=pd.DataFrame(pickle.load(open('rows_2026-07.pkl','rb')))
J=J[J.txn.isin([1001,4001])]
Aq,Sq=D['2026-08']['q'],D['2026-09']['q']
def regset(q): return set(q[q.reg!=''].reg)
rJ,rA,rS=regset(J),regset(Aq),regset(Sq)
if __name__=='__main__':
    print('Aug leads',len(rA),'new vs Jul(API)',len(rA-rJ),'returning',len(rA&rJ))
    print('Sep leads',len(rS),'new vs Jul+Aug',len(rS-rJ-rA),'returning',len(rS&(rJ|rA)),'; vs Aug only returning',len(rS&rA))
    print('cum unique Jul+Aug',len(rJ|rA),'+Sep',len(rJ|rA|rS))
    # busiest single registration (calls) per provider
    for m,q in [('Aug',Aq),('Sep',Sq)]:
        print(m,{p:int(q[(q.provider==p)&(q.reg!='')].groupby('reg').size().max()) for p in PROVIDERS},
              'calls/reg',{p:round(len(q[q.provider==p])/q[(q.provider==p)&(q.reg!='')].reg.nunique(),1) for p in PROVIDERS})
