import pickle,pandas as pd,numpy as np
from analysis import PROVIDERS
from deckdata import D,rJ,rA,rS,J
from classify import owner
S,A=D['2026-09'],D['2026-08']
IDV=pickle.load(open('idv.pkl','rb'))
STATE={'AP':'Andhra Pradesh','AR':'Arunachal Pradesh','AS':'Assam','BR':'Bihar','CG':'Chhattisgarh','CH':'Chandigarh','DD':'Daman & Diu','DL':'Delhi','DN':'Dadra & Nagar Haveli','GA':'Goa','GJ':'Gujarat','HP':'Himachal Pradesh','HR':'Haryana','JH':'Jharkhand','JK':'Jammu & Kashmir','KA':'Karnataka','KL':'Kerala','LA':'Ladakh','MH':'Maharashtra','ML':'Meghalaya','MN':'Manipur','MP':'Madhya Pradesh','MZ':'Mizoram','NL':'Nagaland','OD':'Odisha','OR':'Odisha','PB':'Punjab','PY':'Puducherry','RJ':'Rajasthan','SK':'Sikkim','TN':'Tamil Nadu','TR':'Tripura','TS':'Telangana','TG':'Telangana','UK':'Uttarakhand','UP':'Uttar Pradesh','WB':'West Bengal'}
def month(m,d,idvd):
    q=d['q']; f=d['funnel']; pol=d['pol']; days=31 if m=='2026-08' else 30
    o={'f':f,'days':days}
    o['fail']=int(f['Total']['calls']-f['Total']['succ'])
    o['bought']=int(pol.reg.nunique())
    qq=q[q.reg!='']
    o['calls_reg']={p:len(q[q.provider==p])/qq[qq.provider==p].reg.nunique() for p in PROVIDERS}
    o['busiest']={p:int(qq[qq.provider==p].groupby('reg').size().max()) for p in PROVIDERS}
    o['succ_rate']={p:f[p]['succ']/f[p]['calls'] for p in PROVIDERS+['Total']}
    o['failed']={p:int(f[p]['calls']-f[p]['succ']) for p in PROVIDERS+['Total']}
    # reasons per carrier
    fl=d['fail']; o['reasons']={}; o['owner']={}
    for p in PROVIDERS:
        g=fl[fl.provider==p]; t=g.groupby('err_n').size().sort_values(ascending=False)
        o['reasons'][p]=[(e,int(n),owner(g[g.err_n==e].cat.iloc[0])) for e,n in t.head(5).items()]
        ow=g.owner.value_counts(); o['owner'][p]={k:int(ow.get(k,0)) for k in ['Carrier','Fibe','Fibe Mapping','Unclassified']}
    # segments
    first=qq.sort_values('time').groupby('reg').agg(prod=('product','first'),vage=('vage','first'),rto=('rto','first'))
    first['state']=first.rto.astype(str).str[:2].map(STATE).fillna('Other')
    first['age']=pd.cut(first.vage.astype(float),[-1,3,7,200],labels=['0-3','4-7','8+']).astype(object).fillna('Unknown')
    mi={r:min(v for _,v in l) for r,l in idvd.items()}
    first['idv']=pd.Series(mi); first['idvb']=pd.cut(first.idv,[-1,1e5,3e5,5e5,1e6,1e12],labels=['<1L','1-3L','3-5L','5-10L','10L+'],right=False).astype(object).fillna('Unpriced')
    p2=pol.merge(first[['age','idvb','state']],left_on='reg',right_index=True,how='left')
    def seg(col,keys=None):
        l=first.groupby(col).size(); pc=p2.groupby(col).size(); g=p2.groupby(col).premium.sum()
        keys=keys or list(l.sort_values(ascending=False).index)
        return [(k,int(l.get(k,0)),int(pc.get(k,0)),int(round(g.get(k,0)))) for k in keys]
    pp=pol.groupby('product').agg(n=('premium','size'),g=('premium','sum'))
    ll=first.groupby('prod').size()
    o['seg_type']=[('Two-wheeler',int(ll.get('2W',0)),int(pp.n.get('2W',0)),int(round(pp.g.get('2W',0)))),('Private car / Commercial',int(ll.get('4W',0)),int(pp.n.get('4W',0)),int(round(pp.g.get('4W',0)))),('Unclassified',0,0,0)]
    o['seg_age']=seg('age'); o['seg_idv']=seg('idvb',['<1L','1-3L','3-5L','5-10L','10L+'])
    o['seg_state']=seg('state')[:8] if False else sorted(seg('state'),key=lambda x:-x[1])[:8]
    return o
M={'A':month('2026-08',A,IDV['2026-08']),'S':month('2026-09',S,IDV['2026-09'])}
M['newrep']={'A':(len(rA-rJ),len(rA&rJ)),'S':(len(rS-rJ-rA),len(rS&(rJ|rA))),'cumA':len(rJ|rA),'cumS':len(rJ|rA|rS)}
pickle.dump(M,open('deck_M.pkl','wb'))
if __name__=='__main__':
    for k in 'AS':
        m=M[k]; print('=====',k,'bought',m['bought'],'fail',m['fail']); print(pd.DataFrame(m['f']).T[['leads','priced','apps','policies','gwp','calls']].round(0))
        print('seg type',m['seg_type']); print('age',m['seg_age']); print('idv',m['seg_idv']); print('state',m['seg_state'])
        for p in PROVIDERS: print(p,m['owner'][p]); [print('   ',r) for r in m['reasons'][p]]
    print(M['newrep'])
