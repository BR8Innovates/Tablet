# Personal Accident (PA001) UAT
- `PA_UAT_Test_Report.docx` – report; `PA_UAT_Test_Results.xlsx` – 60 test cases, defects, collection review
- `evidence/` – generated PDFs showing the wrong cover amounts
- `pa.py` – runner. It reads `items.json` (the request bodies from your Postman collection, keyed by request name; not stored here because the collection contains tokens) and needs `UAT_USER` / `UAT_PASS` env vars.
