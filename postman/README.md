# Protec UAT - Postman / Newman test suite

Files
- `Protec_UAT_Test_Suite.postman_collection.json` - 160+ requests with test scripts, self-chaining via collection variables
- `Protec_UAT.postman_environment.json` - environment (baseUrl, tenantCode, accessToken, username, password)
- `sample_upload.pdf` - file used by the document upload requests

Authentication (pick one)
1. Machine user: set `username` and `password` in the environment. Folder `0 Auth` calls `POST /cas/get-token` and stores `accessToken`.
2. Preset token: set `accessToken` (for example the PAT). `0 Auth` is then skipped.

Run
```
npm i -g newman
newman run Protec_UAT_Test_Suite.postman_collection.json \
  -e Protec_UAT.postman_environment.json \
  --env-var accessToken=<token> \
  --working-dir . \
  --reporters cli,junit --reporter-junit-export results.xml
```
`--working-dir .` (run from this folder) is needed so `sample_upload.pdf` is found.
Run a single folder with `--folder "5 Claims (FNOL on the PCAR policy)"`.

Folders
| Folder | What it tests |
|---|---|
| 0 Auth | A01 get token (machine user) |
| 1 Party, agent and reference reads | A02-A18, A23, A35 |
| 3 Policy issuance | quote -> proposal -> bind -> float issuance for PCAR, P2W, PCV, GCV (A19-A31) |
| 4 Float checks | A12-A14, float debit per policy |
| 5 Claims | FNOL (A42), claim searches (A43), detail (A44), claim policy (A45), survey (A46) |
| 6 Endorsements | E1-E7 per product (A48), history (A49) |
| 7 Policy reads and documents | A33, A34, A47, upload/query/download (A36-A41) |
| 99 Known issues | tests for open bugs - EXPECTED TO FAIL until fixed |

Test data (UAT, tenant protecuat)
- Agent `PTY00000000000003`, customer `CUS26000022`, float collection `532527` - change in the collection variables for another environment.
- Folders 4-7 use `policyNo_*` / `policyId_*`. Folder 3 overwrites them with freshly issued policies; if folder 3 cannot issue, the defaults (policies issued on 28 Oct 2026) are used.

Known behaviour worth knowing
- FNOL `AccidentTime` must be inside the cover period, otherwise the error is the misleading `MO-Claim-Info-E0002 The policy does not exist!`.
- `proposalBind` returns `{PolicyObject, UnderwritingResult}`; `proposalSendPrepayment` must be given the `PolicyObject`.
- Vehicle make/fuel/model must exist in the PCAR_TECH_* code tables (fuel `PETROL`, make 107 / 201 / 401 / 501 per product).
- New vehicles (`RegistrationNo` NEW, `IsNewVehicle` Y) avoid the Vahan lookup, which fails for registered vehicles (BUG-02).
- Since 28 Oct 2026 validation also requires nominee details for individual policyholders (BUG-06, folder 3 fails until the `PersonRelation` code table / nominee payload is resolved).
