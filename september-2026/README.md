# September 2026 — Fibe × InsureMO

* `Fibe_Carrier_Error_Analysis_September_2026.xlsx` — carrier error analysis (same structure as August) plus Cumulative (Aug+Sep), 2W, 4W, Policy Issuance (Go Digit: PolicyNo + CarrierPolicyNo; others: CarrierPolicyNo), Funnel & GWP, Daily Trend and Data Verification tabs.
* `FIBE_x_insureMO_-_MBR_September_2026.pptx` — monthly business review deck (September vs August) with added 2W, 4W and Cumulative slides.
* `scripts/` — extraction and build code. Data is pulled from `queryTransactionPaged` with `clientRequestTimeFrom/To` (`yyyy/MM/dd`), day by day. Set `INSUREMO_USER` / `INSUREMO_PASS` to run `pull.py`. Raw API data is intentionally not committed (contains customer PII).
