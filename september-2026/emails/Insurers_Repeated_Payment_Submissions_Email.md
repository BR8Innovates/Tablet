**To:** Go Digit; ICICI Lombard; Tata AIG – Motor issuance / integration support
**Cc:** InsureMO Support; Fibe team
**Subject:** Repeated payment submissions on failed policy issuance (same payment, multiple days) – refund process and controls

Hi team,

In the InsureMO integration logs for Fibe motor policies we see the same payment transaction submitted to the insurer repeatedly after issuance has failed, in several cases across multiple days. We want to understand why the insurer platform accepts this and what the refund process is when the payment is taken but no policy is issued.

**Data reviewed:** last 90 days (31 Jul – 29 Oct 2026), issuance/payment calls (ICICI: proposal call carrying the payment transaction id; Digit and Tata: issue-policy call).

| Insurer | Calls | Unique payment txns | Never issued | Txns retried (>1 attempt) | Txns on >1 day | Multi-day and never issued | Most attempts on one txn |
|---|---|---|---|---|---|---|---|
| ICICI Lombard | 156 | 51 | 17 | 43 | 8 | 1 | 13 (5 days) |
| Go Digit | 159 | 60 | 6 | 48 | 2 | 1 | 22 (5 days) |
| Tata AIG | 128 | 28 | 7 | 22 | 6 | 3 | 36 (7 days) |

**Cases that need attention (paid, no policy, retried across days):**
- **Go Digit** – `FIB_pay_TqDRsBy73eocFy`, INR 10,530: 22 attempts, 20 Oct 21:13 → 27 Oct 10:06 (5 days). 21 × "As per current status of Quote, issuance is not allowed", 1 × "Too Many Requests". First TraceId `67f1f9c651c7a4419f88f52c93b78b26`.
- **ICICI Lombard** – `pay_TsAGZVlGVYSXCO`, INR 6,082: 9 attempts, 25 → 27 Oct, no CarrierPolicyNo. Across the window ICICI also shows many attempts ending in "KYC PENDING" and "This Transaction is already in process. Please retry after some time".
- **Tata AIG** – `TkaX6vgQx4ofxv`, INR 4,473: 36 attempts, 6 → 18 Oct (7 days); `TkU44gMPZdKhsQ`, INR 1,612: 9 attempts, 6 → 12 Oct; `TlgSOgjoqiI0YK`, INR 1,374: 7 attempts, 9 → 19 Oct. All "Product Name is Invalid, Please verify it once again." (HTTP 400) since 6 Oct. Issuance started succeeding again from 25 Oct, so please confirm what changed and whether these three pending payments can now be issued.

Also observed: repeat submissions of a payment that had already produced a policy (e.g. Tata `TpEnyJe3LxuQ1g`, six successful calls on 25 Oct; ICICI "Policy already issued.").

**Questions (for each insurer):**
1. Why is the same payment/transaction id accepted for submission repeatedly, including across multiple days, when issuance has already failed or the quote is not in an issuable state? Is there a validation or idempotency control on the transaction id that should reject it up front?
2. What does each error mean for these cases ("issuance is not allowed" – Digit; "KYC PENDING" and "already in process" – ICICI; "Product Name is Invalid" – Tata) and what is needed to move the case to an issuable state?
3. What is the refund process when premium is collected but no policy is issued? Please share timelines and the data you need from us (payment transaction no., application/proposal no., amount, dates).
4. For the cases above, is the payment held or received on your side, and can it be refunded or the policy issued? Is any amount being retained or double-counted when the same payment is submitted several times?
5. Are there retry limits or throttling we should follow (Digit returned "Too Many Requests")? Please advise the recommended retry behaviour for failed issuance.

Please reply with the plan and an expected resolution date. Customer details can be shared over a secure channel.

Regards,
[Name]
[Fibe / insureMO]

*Attachments:* All_Insurers_Payment_Resubmissions_90d.xlsx; Digit_IssuePolicy_FIB_pay_TqDRsBy73eocFy_Logs.xlsx
