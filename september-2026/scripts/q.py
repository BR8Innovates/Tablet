import requests,json,sys
TOK=open('tok.txt').read().strip()
U='https://fibein-in-2.insuremo.com/api/platform/platform-pub/inteadapter/v1/queryTransactionPaged'
def q(body,page=1,size=5):
    r=requests.post(U,params={'pageNum':page,'pageSize':size},json=body,headers={'Authorization':'Bearer '+TOK},timeout=120)
    try: return r.status_code,r.json()
    except Exception: return r.status_code,r.text[:300]
if __name__=='__main__':
    tests=[{},{'ProviderCode':'DIGIT'},{'CountryCode':'IND-4W'},{'ClientRequestTimeFrom':'2026-09-01T00:00:00','ClientRequestTimeTo':'2026-09-30T23:59:59'},
    {'StartTime':'2026-09-01','EndTime':'2026-09-30'},{'ClientRequestTime':'2026-09-01'},{'ClientRequestStartTime':'2026-09-01T00:00:00','ClientRequestEndTime':'2026-09-30T23:59:59'},
    {'TraceId':'ca4e5d773bb753bfb4db63db213e1793'},{'ClientRequestId':'0ea5866c-0f28-40d4-89f4-00670ea625ad'},{'TransactionType':1001}]
    for t in tests:
        s,d=q(t)
        print(t,s,d.get('TotalElements') if isinstance(d,dict) else d)
