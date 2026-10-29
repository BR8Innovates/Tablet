**To:** Go Digit – Motor Issuance / Integration Support
**Cc:** InsureMO Support; Fibe team
**Subject:** Repeated payment submissions on failed policy issuance (same transaction across multiple days) – refund process and controls

Hi team,

While reviewing InsureMO integration logs for Fibe motor policies (issue-policy call, Digit `postIssueContract` via `digit.motor.issuepolicy.url`), we found that Digit accepts the same payment submission repeatedly after the issuance has failed, in one case across several days. We would like to understand the reason and the refund process.

**Data reviewed:** last 90 days (31 Jul – 29 Oct 2026; first call in the window 4 Aug, last 27 Oct)
- 159 Digit issue-policy calls, 60 unique payment transaction numbers.
- 6 payment transactions never resulted in a policy (CarrierPolicyNo / policy number).
- Only 2 transactions were submitted on more than one day; one of them never succeeded.

**Case that needs attention (open):**
- Payment TransactionNo `FIB_pay_TqDRsBy73eocFy`, amount INR 10,530.
- Same payment and the same application id (`CarrierProposalNo`) submitted **22 times** between **20 Oct 2026 21:13** and **27 Oct 2026 10:06** (dates: 20, 21, 22, 23 and 27 Oct; 4, 3, 5, 6 and 4 calls).
- 21 calls returned *"As per current status of Quote, issuance is not allowed"* (HTTP 400); 1 returned *"Too Many Requests"*. No policy was issued.
- First TraceId `67f1f9c651c7a4419f88f52c93b78b26` (ClientRequestId `d72426b1-16f9-46c9-ab46-b864140f95a7`). All 22 calls are in the attached Excel.

**Other unresolved payments (same-day retries):** `FIB_pay_TQKceBc0yxjRM0` (INR 844, 9 attempts on 16 Aug, "Premium mismatch while Policy issuance"), `FIB_pay_TZpOZzoe5iKVAg` (INR 8,190, 6 attempts on 9 Sep), `FIB_pay_TXsE2mjOK8oXBG` (INR 5,537, 5 attempts on 4 Sep), `FIB_pay_TYg45RhZem2Cu7` (INR 3,063, 1 attempt on 6 Sep), `FIB_pay_TM4YTMIty0ser0` (INR 844, 1 attempt on 5 Aug). Also seen: *"The required data (Contract …) are being edited in another file"* and *"The case … has been changed in the meantime by another user"* on a few calls.

**Questions:**
1. Why does Digit allow a payment to be submitted again, repeatedly and across multiple days, for a quote that is in a state where issuance is not allowed? Is there a validation that should reject the payment up front (instead of at issuance)?
2. What does the quote status "issuance is not allowed" mean for these cases (e.g. expired, already referred, premium or IDV changed), and what is needed to move it to an issuable state?
3. What is the refund process when payment has been taken but the policy cannot be issued? Please share the timelines and the information Digit needs from us (payment transaction number, application id, amount, dates).
4. Is the payment from `FIB_pay_TqDRsBy73eocFy` (INR 10,530) held or received on Digit's side, and can it be refunded or the policy issued?
5. Are there retry limits or idempotency controls on `transactionId` that we should rely on? Please also share the cause behind the "Too Many Requests" response, and the contract-lock errors above.

Please let us know the plan and the date by which these will be resolved. Customer details can be shared on a secure channel if required.

Regards,
[Name]
[Fibe / insureMO]

*Attachment:* Digit_IssuePolicy_FIB_pay_TqDRsBy73eocFy_Logs.xlsx
