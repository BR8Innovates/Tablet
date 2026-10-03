import sys,json,gzip,time,datetime,requests,os
from q import U
def token():
    return requests.post('https://fibein-in-2.insuremo.com/cas/ebao/v2/json/tickets',json={"username":os.environ["INSUREMO_USER"],"password":os.environ["INSUREMO_PASS"]},timeout=30).json()['access_token']
TOK=token(); t0=time.time()
def post(body,page,size):
    global TOK
    for a in range(6):
        try:
            r=requests.post(U,params={'pageNum':page,'pageSize':size},json=body,headers={'Authorization':'Bearer '+TOK},timeout=180)
            if r.status_code==200: return r.json()
            if r.status_code in(401,403): TOK=token()
        except Exception as e: pass
        time.sleep(2*(a+1))
    raise RuntimeError('fail %s %s'%(body,page))
month=sys.argv[1]; y,m=map(int,month.split('-'))
d=datetime.date(y,m,1); out=f'raw_{month}'; os.makedirs(out,exist_ok=True)
summary={}
while d.month==m:
    ds=d.strftime('%Y/%m/%d'); body={'clientRequestTimeFrom':ds,'clientRequestTimeTo':ds}
    first=post(body,1,1000); tot=first['TotalElements']; n=0; ids=set()
    with gzip.open(f'{out}/{d.isoformat()}.jsonl.gz','wt') as f:
        page=1; res=first
        while True:
            els=res.get('ElementsInCurrentPage',[])
            for e in els: f.write(json.dumps(e)+'\n'); n+=1; ids.add(e['ListId'])
            if page*1000>=tot or not els: break
            page+=1; res=post(body,page,1000)
    summary[d.isoformat()]=(tot,n,len(ids)); print(d,tot,n,len(ids),round(time.time()-t0),flush=True)
    d+=datetime.timedelta(days=1)
json.dump(summary,open(f'{out}/summary.json','w'))
print('DONE')
