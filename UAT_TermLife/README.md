# Term Life (TL001) UAT – deliverables

| File | Purpose |
|---|---|
| `TermLife_UAT_Test_Report.docx` | Test report: verdict, results, defects, observations, clarifications |
| `TermLife_UAT_TestCases_and_Results.xlsx` | 213 executed test cases with expected/actual/status, 24 UI cases (not executed), defect register, spec clarifications |
| `results.json` | Raw machine-readable results |
| `evidence/` | Generated PDFs / feed file used as evidence |
| `scripts/` | Re-runnable API test suite (`python3 suite2.py`) |

## Re-running
```
pip install requests openpyxl python-docx
export UAT_USER=<user> UAT_PASS=<password>   # credentials are not stored in this repo
cd scripts && python3 suite2.py      # ~5 min; writes results.json
python3 verify.py                    # targeted re-tests used to confirm doubtful results
```
Note: the run creates ~150 proposals and ~20 policies in the UAT tenant.
