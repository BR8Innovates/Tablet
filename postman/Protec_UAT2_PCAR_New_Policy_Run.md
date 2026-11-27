# PCAR new policy - endpoints and responses (UAT2, 27 Nov 2026)

Effective date set to 2026-11-27 (today) in every quote/proposal date field; expiry 2027-11-26T23:59:59. Environment: protecuat2 sandbox, PAT auth.

Result: quote, proposal, validate and underwriting pass; **bind succeeded (PolicyId 6000508, ProposalNo PQ-1005-26-00000088, status 2 = Bound, UW Status Success)**. Float prepayment (2.9) returns **422 UndefinedException**, so the policy is not yet issued and has no policy number.

| # | Method | Endpoint | HTTP | Result |
|---|---|---|---|---|
| 1 | POST | `` | 200 | pass |
| 2 | POST | `` | 200 | pass |
| 3 | POST | `` | 200 | pass |
| 4 | POST | `` | 200 | pass |
| 5 | POST | `` | 200 | pass |
| 6 | POST | `` | 200 | pass |
| 7 | POST | `` | 200 | pass |
| 8 | POST | `` | 200 | pass |
| 9 | POST | `` | 422 | fail: expected response to have status code 200 but got 422 |
| 10 | GET | `` | 200 | pass |

## Request and response per step

### 1. PCAR 1.1 Quotation persist
`POST `  -  HTTP 200

Request body (excerpt):
```json
{
 "@type": "Policy-POLICY",
 "AgentCode": "IA000001",
 "BookCurrencyCode": "INR",
 "BusinessCateCode": "1",
 "BusinessObjectId": 1184366522,
 "EffectiveDate": "2026-11-27",
 "ExpiryDate": "2027-11-26T23:59:59",
 "IsRenewable": "Y",
 "IsTakeUpPolicy": "N",
 "LocalCurrencyCode": "INR",
 "OrgCode": "90000",
 "PolicyType": "1",
 "PremiumBookExchangeRate": 1,
 "PremiumCurrencyCode": "INR",
 "PremiumLocalExchangeRate": 1,
 "ProductCode": "PCAR",
 "ProductId": 1184370116,
 "ProductVersion": "1.0",
 "ProposalDate": "2026-11-27",
 "SchemaVersion": 2,
 "SumInsured": 9999999999,
 "TechProductCode": "PCAR_TECH",
 "TechProductId": 1184321284,
 "VersionSeq": 1,
 "AgentName": "Ravi Teja Bhogavalli",
 "Age ...
```
Response (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"ChannelType":"AP","CompanyChannelType":"DIRECT_AGENCY","EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","IN_StateOfficeCode":"27","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsRenewable":"Y","IsTakeUpPolicy":"N","LOBCode":"31","LocalCurrencyCode":"INR","OrgCode":"90000","PolicyAgentList":[{"AgentCode":"IA000001","BusinessObjectId":370854223,"IsLeader":"Y","PolicyStatus":2,"SequenceNumber":1,"ShareRate":1}],"PolicyCustomerList":[{"AddressLine1":"18-137 Aswaraopet Road","AddressLine2":"Near Union Bank","AnnualIncome":1234567,"BusinessObjectId":1000000290,"BusinessTel":"9876543210","CustomerName":"Ravi Teja Bhogavalli","Custome ...
```

### 2. PCAR 1.2 Quotation calculate
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"ChannelType":"AP","CompanyChannelType":"DIRECT_AGENCY","EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","IN_StateOfficeCode":"27","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsRenewable":"Y","IsTakeUpPolicy":"N","LOBCode":"31","LocalCurrencyCode":"INR","OrgCode":"90000","PolicyAgentList":[{"AgentCode":"IA000001","BusinessObjectId":370854223,"IsLeader":"Y","PolicyStatus":2,"SequenceNumber":1,"ShareRate":1}],"PolicyCustomerList":[ ...
```
Response (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatMinusGrossPremium":0,"BeforeVatMinusGrossPremiumDelta":0,"BeforeVatPremium":3791,"BeforeVatPremiumDelta":0,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"CGSTDelta":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CompanyChannelType":"DIRECT_AGENCY","DueMinusBeforeVatPremium":682,"DueMinusBeforeVatPremiumDelta":0,"DuePremium":4473,"DuePremiumDelta":0,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","GrossPremium":3791,"GrossPremiumDelta":0,"IGST":682,"IGSTDelta":0,"IN_StateOfficeCode":"27","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsPremiumCalcSuccess":"Y","IsRenewable":"Y","IsTakeUpPolicy" ...
```

### 3. PCAR 2.1 Proposal create
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"QuotationNo":"QPCAR000000000198"}
```
Response (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"ChannelType":"AP","CompanyChannelType":"DIRECT_AGENCY","EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","IN_StateOfficeCode":"27","InsertBy":10000000970439,"InsertTime":"2026-11-27T11:28:01","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsRenewable":"Y","IsTakeUpPolicy":"N","LOBCode":"31","LocalCurrencyCode":"INR","OldPrimaryKey":6000508,"OrgCode":"90000","PolicyAgentList":[{"AgentCode":"IA000001","BusinessObjectId":370854223,"IsLeader":"Y","ParentElementType":"POLICY","ParentPolicyElementId":6000508,"PolicyElementId":6445523,"PolicyId":6000508,"PolicyStatus":2,"SequenceNumber":1,"Sha ...
```

### 4. PCAR 2.2 Proposal save
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"ChannelType":"AP","CompanyChannelType":"DIRECT_AGENCY","EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","IN_StateOfficeCode":"27","InsertBy":10000000970439,"InsertTime":"2026-11-27T11:28:01","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsRenewable":"Y","IsTakeUpPolicy":"N","LOBCode":"31","LocalCurrencyCode":"INR","OldPrimaryKey":6000508,"OrgCode":"90000","PolicyAgentList":[{"AgentCode":" ...
```
Response (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"ChannelType":"AP","CompanyChannelType":"DIRECT_AGENCY","EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","IN_StateOfficeCode":"27","InsertBy":10000000970439,"InsertTime":"2026-11-27T11:28:01","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsRenewable":"Y","IsTakeUpPolicy":"N","LOBCode":"31","LocalCurrencyCode":"INR","OldPrimaryKey":6000508,"OrgCode":"90000","PolicyAgentList":[{"AgentCode":"IA000001","BusinessObjectId":370854223,"IsLeader":"Y","ParentElementType":"POLICY","ParentPolicyElementId":6000508,"PolicyElementId":6445523,"PolicyId":6000508,"PolicyStatus":2,"SequenceNumber":1,"Sha ...
```

### 5. PCAR 2.3 Proposal calculate
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"ChannelType":"AP","CompanyChannelType":"DIRECT_AGENCY","EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","IN_StateOfficeCode":"27","InsertBy":10000000970439,"InsertTime":"2026-11-27T11:28:01","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsRenewable":"Y","IsTakeUpPolicy":"N","LOBCode":"31","LocalCurrencyCode":"INR","OldPrimaryKey":6000508,"OrgCode":"90000","PolicyAgentList":[{"AgentCode":" ...
```
Response (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatMinusGrossPremium":0,"BeforeVatMinusGrossPremiumDelta":0,"BeforeVatPremium":3791,"BeforeVatPremiumDelta":0,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"CGSTDelta":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","DueMinusBeforeVatPremium":682,"DueMinusBeforeVatPremiumDelta":0,"DuePremium":4473,"DuePremiumDelta":0,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","GrossPremium":3791,"GrossPremiumDelta":0,"IGST":682,"IGSTDelta":0,"IN_StateOfficeCode":"27","InsertBy":10000000970439,"InsertTime":"2026-11-27T11:28:01","InsurerPr ...
```

### 6. PCAR 2.4 Proposal validate
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatMinusGrossPremium":0,"BeforeVatMinusGrossPremiumDelta":0,"BeforeVatPremium":3791,"BeforeVatPremiumDelta":0,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"CGSTDelta":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","DueMinusBeforeVatPremium":682,"DueMinusBeforeVatPremiumDelta":0,"DuePremium":4473,"DuePremiumDelta":0,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","FirstD ...
```
Response (excerpt):
```json
{}
```

### 7. PCAR 2.5 Proposal send underwriting
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","BeforeVatMinusGrossPremium":0,"BeforeVatMinusGrossPremiumDelta":0,"BeforeVatPremium":3791,"BeforeVatPremiumDelta":0,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"CGSTDelta":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","DueMinusBeforeVatPremium":682,"DueMinusBeforeVatPremiumDelta":0,"DuePremium":4473,"DuePremiumDelta":0,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","FirstD ...
```
Response (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","AutoUwResultCode":"1","BeforeVatMinusGrossPremium":0,"BeforeVatPremium":3791,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","CurUwLevelCode":"1","DueMinusBeforeVatPremium":682,"DuePremium":4473,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","GrossPremium":3791,"IGST":682,"IN_StateOfficeCode":"27","InsertBy":10000000970439,"InsertTime":"2026-11-27T11:28:01","InsurerProductCode":"1005","InterestRate":0,"InvoiceNo":"PV-26-00000018","IsLockedByRi":"N","IsPremiumCalcSuccess":"Y","IsRenewable ...
```

### 8. PCAR 2.6 Proposal bind
`POST `  -  HTTP 200

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","AutoUwResultCode":"1","BeforeVatMinusGrossPremium":0,"BeforeVatPremium":3791,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","CurUwLevelCode":"1","DueMinusBeforeVatPremium":682,"DuePremium":4473,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","GrossPremium":3791,"IGST":682,"IN_StateOfficeCode ...
```
Response (excerpt):
```json
{"PolicyObject":{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","AutoUwResultCode":"1","BeforeVatMinusGrossPremium":0,"BeforeVatMinusGrossPremiumDelta":0,"BeforeVatPremium":3791,"BeforeVatPremiumDelta":0,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"CGSTDelta":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","CurUwLevelCode":"1","DueMinusBeforeVatPremium":682,"DueMinusBeforeVatPremiumDelta":0,"DuePremium":4473,"DuePremiumDelta":0,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDateBeforeCancel":"2027-11-26T23:59:59","FirstDataEntryDate":"2026-11-27T11:28:01","GrossPremium":3791,"GrossPremiumDelta":0,"IGST":682,"IGSTDelta":0,"IN_StateOfficeCode":"27","InsertBy": ...
```

### 9. PCAR 2.9 Proposal send prepayment (float, PayMode 120)
`POST `  -  HTTP 422

Request body (excerpt):
```json
{"AgentCode":"IA000001","AgentName":"Ravi Teja Bhogavalli","AgentPartyCategory":"13","AutoUwResultCode":"1","BeforeVatMinusGrossPremium":0,"BeforeVatMinusGrossPremiumDelta":0,"BeforeVatPremium":3791,"BeforeVatPremiumDelta":0,"BeforeVatPremiumForRI":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessFrom":"NewBusiness","BusinessObjectId":1184366522,"CGST":0,"CGSTDelta":0,"ChannelType":"AP","Commission":-568.65,"CommissionDelta":0,"CommissionRate":0.1,"CompanyChannelType":"DIRECT_AGENCY","CurUwLevelCode":"1","DueMinusBeforeVatPremium":682,"DueMinusBeforeVatPremiumDelta":0,"DuePremium":4473,"DuePremiumDelta":0,"EffectiveDate":"2026-11-27","ExpiryDate":"2027-11-26T23:59:59","ExpiryDat ...
```
Response (excerpt):
```json
{"timestamp":"2026-11-27T11:28:14","timestampServer":"2026-11-27T05:58:14","traceId":"72d86083c2bf34584be8446044c4f522","env":"aws_in_protec_sandbox","tenant":"protecuat2","status":422,"code":"UndefinedException","message":"UndefinedException"}
```

### 10. PCAR 3.1 Load proposal/policy (issued)
`GET `  -  HTTP 200

Response (excerpt):
```json
{"@pk":6000029,"@type":"Policy-POLICY","AgentCode":"IA000001","AutoUwResultCode":"1","BeforeVatPremium":3791,"BookCurrencyCode":"INR","BusinessCateCode":"1","BusinessObjectId":1184366522,"Commission":-568.65,"CurUwLevelCode":"1","DuePremium":4473,"EffectiveDate":"2026-11-26","ExpiryDate":"2027-11-25T23:59:59","FirstDataEntryDate":"2026-11-26T11:45:26","GrossPremium":3791,"InsertBy":10000000970439,"InsertTime":"2026-11-26T11:45:26","IsIssueAfterPay":"Y","IsLockedByRi":"N","IsPremiumCalcSuccess":"Y","IsRenewable":"Y","IsTakeUpPolicy":"N","IssueDate":"2026-11-26T11:45:40","IssueUserId":10000000970439,"IssueUserRealName":"protecuat2.admin","LocalCurrencyCode":"INR","MaxUwLevelCode":"1","OrgCode":"90000","PolicyElementId":6000029,"PolicyId":6000029,"PolicyNo":"PP-1005-26-00000024-00","PolicyStatus":2,"PolicyStatusForDisplay":2,"PolicyType":"1","PremCalcFactorHash":"{V3,5944382}roQZ+iDYsdRyfuc ...
```

