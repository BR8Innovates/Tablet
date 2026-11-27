# Protec UAT2 - sequenced API list

Total requests: 142

### 0 Authentication (1)
- POST Get token (ProtecPortalUser, protecuat2)

### 1 Reference data (6)
- POST A15.1 Datatable PayMethod
- POST A16.1 Codetable PartyStatus
- POST A16.2 Codetable CauseOfLoss
- POST A16.3 Codetable FinancierAgreementType
- POST A17.1 Ratetable PCAR_TPRate
- GET A18.1 Product schema PCAR

### 2 Party, customer and KYC (11)
- POST A02.1 Party query by PAN
- POST A02.2 Eligible customers (active, KYC verified)
- POST A02 Party query fuzzy name
- POST A02.3 Party query sales channel
- POST A02.4 Customer master search
- GET A03.1 Party load customer
- GET A03.2 Party load sales channel (agent)
- POST A05.1 KYC initiate - existing party (PTY/E, IND)
- POST A05.2 KYC initiate - proposal journey (PA/E, IND)
- POST A05.4 KYC initiate - organisation (validation: expected 422 per API list)
- POST 6.4 Unmask entity

### 3 Sales channel and agent (3)
- POST A08.1 Search sales channel (producers)
- GET A09.1 Load sales agreements
- GET A10.1 Load licence

### 4 Vehicle and IIB (10)
- POST A06.1 Vahan class check MH12XX0008
- POST A06.2 Vahan class check MH12AB1234
- POST A06.3 Vahan class check KA01AB1234
- POST A06.4 Vahan class check unknown registration
- POST A07.1 Vehicle data MH12XX0008
- POST A07.2 Vehicle data MH12AB1234
- POST A07.3 Vehicle data KA01AB1234
- POST A07.4 Vehicle data - registration missing (expect rejection)
- POST 6.5 IIB reference retrieve
- POST 6.6 IIB enquiry receive

### 5.1 Issuance - PCAR (quote to float prepayment) (10)
- POST PCAR 1.1 Quotation persist
- POST PCAR 1.2 Quotation calculate
- POST PCAR 2.1 Proposal create
- POST PCAR 2.2 Proposal save
- POST PCAR 2.3 Proposal calculate
- POST PCAR 2.4 Proposal validate
- POST PCAR 2.5 Proposal send underwriting
- POST PCAR 2.6 Proposal bind
- POST PCAR 2.9 Proposal send prepayment (float, PayMode 120)
- GET PCAR 3.1 Load proposal/policy (issued)

### 5.2 Issuance - P2W (quote to float prepayment) (10)
- POST P2W 1.1 Quotation persist
- POST P2W 1.2 Quotation calculate
- POST P2W 2.1 Proposal create
- POST P2W 2.2 Proposal save
- POST P2W 2.3 Proposal calculate
- POST P2W 2.4 Proposal validate
- POST P2W 2.5 Proposal send underwriting
- POST P2W 2.6 Proposal bind
- POST P2W 2.9 Proposal send prepayment (float, PayMode 120)
- GET P2W 3.1 Load proposal/policy (issued)

### 5.3 Issuance - PCV (quote to float prepayment) (10)
- POST PCV 1.1 Quotation persist
- POST PCV 1.2 Quotation calculate
- POST PCV 2.1 Proposal create
- POST PCV 2.2 Proposal save
- POST PCV 2.3 Proposal calculate
- POST PCV 2.4 Proposal validate
- POST PCV 2.5 Proposal send underwriting
- POST PCV 2.6 Proposal bind
- POST PCV 2.9 Proposal send prepayment (float, PayMode 120)
- GET PCV 3.1 Load proposal/policy (issued)

### 5.4 Issuance - GCV (quote to float prepayment) (10)
- POST GCV 1.1 Quotation persist
- POST GCV 1.2 Quotation calculate
- POST GCV 2.1 Proposal create
- POST GCV 2.2 Proposal save
- POST GCV 2.3 Proposal calculate
- POST GCV 2.4 Proposal validate
- POST GCV 2.5 Proposal send underwriting
- POST GCV 2.6 Proposal bind
- POST GCV 2.9 Proposal send prepayment (float, PayMode 120)
- GET GCV 3.1 Load proposal/policy (issued)

### 5.5 Quotation and proposal (all products) (4)
- POST A21.1 Quotation print (existing quote)
- GET 6.1 Load quote details
- GET 6.2 Load proposal/policy (alternate path)
- POST 6.3 Proposal requote (WRITE, not executed)

### 6 Policy and endorsement queries (13)
- GET PCAR A33.1 Load proposal/policy
- GET PCAR A49.1 Endorsement history
- GET P2W A33.1 Load proposal/policy
- GET P2W A49.1 Endorsement history
- GET PCV A33.1 Load proposal/policy
- GET PCV A49.1 Endorsement history
- GET GCV A33.1 Load proposal/policy
- GET GCV A49.1 Endorsement history
- POST A34.1 Policy query by CustomerNo
- POST A34.2 Policy query by AgentCode
- POST A34.3 Policy query by PolicyNo (PCAR)
- POST A23.1 Quotation query
- POST 6.15 Endorsement list by agent code

### 7 Endorsements - PCAR  (8)
- GET PCAR Query policy latest version (A47.1)
- POST PCAR E1 Engine number correction
- POST PCAR E2 Chassis number correction
- POST PCAR E3 Owner-driver DOB / gender (party master)
- POST PCAR E4 Nominee change - CPA (PCAR, P2W)
- POST PCAR E5 Hypothecation addition
- POST PCAR E6 Change of financier (run after E5)
- POST PCAR E7 Hypothecation deletion (run after E6)

### 7 Endorsements - P2W  (8)
- GET P2W Query policy latest version (A47.1)
- POST P2W E1 Engine number correction
- POST P2W E2 Chassis number correction
- POST P2W E3 Owner-driver DOB / gender (party master)
- POST P2W E4 Nominee change - CPA (PCAR, P2W)
- POST P2W E5 Hypothecation addition
- POST P2W E6 Change of financier (run after E5)
- POST P2W E7 Hypothecation deletion (run after E6)

### 7 Endorsements - PCV  (7)
- GET PCV Query policy latest version (A47.1)
- POST PCV E1 Engine number correction
- POST PCV E2 Chassis number correction
- POST PCV E3 Owner-driver DOB / gender (party master)
- POST PCV E5 Hypothecation addition
- POST PCV E6 Change of financier (run after E5)
- POST PCV E7 Hypothecation deletion (run after E6)

### 7 Endorsements - GCV  (7)
- GET GCV Query policy latest version (A47.1)
- POST GCV E1 Engine number correction
- POST GCV E2 Chassis number correction
- POST GCV E3 Owner-driver DOB / gender (party master)
- POST GCV E5 Hypothecation addition
- POST GCV E6 Change of financier (run after E5)
- POST GCV E7 Hypothecation deletion (run after E6)

### 8 Claims (4)
- POST A43.1 Claims of policy
- POST 6.7 Submit FNOL (register claim) (WRITE, not executed)
- GET 6.8 Load claim case detail
- GET 6.9 Load claim policy

### 9 Documents (7)
- POST A37.1 Query policy files
- POST A39.1 Policy document tree
- GET A40.1 Document checklist
- POST 6.13 Attachment info (files and document tree)
- GET 6.11 Load all document versions
- GET 6.12 Download document / policy PDF
- POST 6.10 Upload document (WRITE, not executed)

### 10 Commission (9)
- POST C1 Query commission (agent)
- GET C2 Agreement by code (commission rates)
- GET C3 Agreement load by channel (agent)
- GET C4 Agent party load
- GET C5 PCAR policy commission (from policy load)
- GET C5 P2W policy commission (from policy load)
- GET C5 PCV policy commission (from policy load)
- GET C5 GCV policy commission (from policy load)
- POST A11.1 Query commission (agent)

### 11 Float account (4)
- POST A12.1 Float search collections
- GET A13.1 Float load collection (balance)
- GET A14.1 Float transaction history
- POST 6.14 Query float accounts
