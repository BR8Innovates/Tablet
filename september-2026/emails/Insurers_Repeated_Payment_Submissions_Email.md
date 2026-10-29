**To:** Go Digit; ICICI Lombard; Tata AIG – Motor issuance / integration support
**Cc:** InsureMO Support; Fibe team
**Subject:** Payment details submitted multiple times across multiple days on failed issuance – reason and refund process

Hi team,

In the InsureMO integration logs for Fibe motor policies, we see the same payment details submitted to the insurer multiple times after issuance has returned an error, in several cases across multiple days.

Could you please explain:
1. **Why is a payment submission allowed multiple times, across multiple days, for the same payment/transaction when issuance has failed with an error?**
2. **What is the refund process** when the payment is received but the policy is not issued (timelines, and the information you need from us)?

**Data – last 90 days (31 Jul – 29 Oct 2026)**

| Insurer | Issuance calls with payment | Unique payment transactions | Never issued | Resubmitted (>1 attempt) | Resubmitted on more than 1 day | Multi-day and never issued |
|---|---|---|---|---|---|---|
| ICICI Lombard | 156 | 51 | 17 | 43 | 8 | 1 |
| Go Digit | 159 | 60 | 6 | 48 | 2 | 1 |
| Tata AIG | 128 | 28 | 7 | 22 | 6 | 3 |

**Examples – payment received, retried across days, no policy issued**

| Insurer | Payment transaction no. | Amount (INR) | Attempts | Dates | Error returned |
|---|---|---|---|---|---|
| Go Digit | FIB_pay_TqDRsBy73eocFy | 10,530 | 22 | 20 Oct 21:13 → 27 Oct 10:06 (5 days) | As per current status of Quote, issuance is not allowed |
| ICICI Lombard | pay_TsAGZVlGVYSXCO | 6,082 | 9 | 25 → 27 Oct (3 days) | No policy number returned |
| Tata AIG | TkaX6vgQx4ofxv | 4,473 | 36 | 6 → 18 Oct (7 days) | Product Name is Invalid, Please verify it once again. |
| Tata AIG | TkU44gMPZdKhsQ | 1,612 | 9 | 6 → 12 Oct (4 days) | Product Name is Invalid, Please verify it once again. |
| Tata AIG | TlgSOgjoqiI0YK | 1,374 | 7 | 9 → 19 Oct (4 days) | Product Name is Invalid, Please verify it once again. |

The complete list of payments submitted on more than one day, with every call (date and time, TraceId, ClientRequestId, result), is in the attached Excel. For Go Digit, the full request/response logs for the first example are also attached.

Please share your response and the refund timeline for the pending payments above.

Regards,
[Name]
[Fibe / insureMO]

*Attachments:* All_Insurers_Payment_Resubmissions_90d.xlsx; Digit_IssuePolicy_FIB_pay_TqDRsBy73eocFy_Logs.xlsx
