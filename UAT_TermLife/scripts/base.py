import copy
def proposal(sub=1,plan=1,mode=2,term=1,**kw):
    cov={1:[("DTH",10000),("PTD",10000),("PPD",10000),("TRV",0),("REX",1000)]}
    b={"ApplicationNo":"UAT-0001","EffectiveDate":"2026-10-13","ExpiryDate":"2027-10-12T23:59:59","UserName":"Salman","ApplyDate":"2026-10-13","BranchCode":"001","DiscountAmount":0,"StaffId":"76",
    "PolicyCustomerList":[{"CIFNumber":"45678","CustomerType":"1"}],
    "PolicyLobList":[{"PolicyRiskList":[{"Gender":"1","IdNo":"123456789","IdType":"1","Salutation":"1","InsuredName":"Mohamed","DateOfBirth":"1988-10-01","ResidentStatus":"1","Email":"Mohamed@gmail.com","MaritalStatus":"1","PostCode":"100345","Mobile":"9989374444","Address":"Oman","MonthSalaryIncome":"10000",
      "PlanList":[{"PolicyCoverageList":[{"ProductElementCode":c,"SumInsured":s} for c,s in cov[1]],"PlanId":plan}],
      "BeneficiaryList":[{"BeneficaryName":"Sayyed","RelationshipCode":"1","Share":"100","BeneficarySequence":"1"}],"ProductElementCode":"R00001"}],"ProductCode":"TL001","DuePremium":216}],
    "PolicyPaymentInfoList":[{"LGCode":"23","LCCode":45,"IsInstallment":"N","DebitAccountNo":"896236508","DebitRefNo":"wer455","TransactionDate":"2026-10-13"}],
    "PolicyType":"1","ProductCode":"TL001","PremiumModeCode":mode,"ProductSubcode":sub,"ChannelCode":"SOHAR","PlanId":plan,"PolicyTerm":term,"DuePremium":153}
    return b
