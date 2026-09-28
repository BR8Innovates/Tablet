#!/usr/bin/env python3
"""Turn a Newman JSON report into a per-request structure table (Markdown).

  newman run Trialx-Portal-APIs-Mandatory.postman_collection.json \
      -e Trialx.postman_environment.json \
      --env-var username=<machine user> --env-var password=<password> \
      --reporters cli,json --reporter-json-export run.json
  python3 summarize_run.py run.json > run-result.md

Verdicts:
  ROUTE MISSING   gateway 404 (wrong path or unpublished API)
  NO TOKEN        401 (credentials missing or wrong)
  NO PERMISSION   403 (API not granted to the tenant / user)
  REJECTED        other 4xx/5xx (request structure or data rejected - see body)
  STRUCTURE FAIL  2xx but a structure test failed (response differs from spec)
  OK              2xx and all structure tests passed
"""
import json
import sys


def verdict(code, failed):
    if code is None:
        return "NO RESPONSE"
    if code == 404:
        return "ROUTE MISSING"
    if code == 401:
        return "NO TOKEN"
    if code == 403:
        return "NO PERMISSION"
    if not 200 <= code < 300:
        return "REJECTED"
    return "STRUCTURE FAIL" if failed else "OK"


def main(path):
    run = json.load(open(path))["run"]
    print("| Request | HTTP | Verdict | Failed checks | Response (first 120 chars) |")
    print("|---|---|---|---|---|")
    for ex in run["executions"]:
        resp = ex.get("response") or {}
        code = resp.get("code")
        failed = [a["assertion"] for a in ex.get("assertions", []) if a.get("error")]
        struct_failed = [f for f in failed if "structure" in f]
        body = ""
        stream = resp.get("stream")
        if isinstance(stream, dict) and stream.get("data"):
            body = bytes(stream["data"]).decode("utf-8", "replace")
        body = body.replace("\n", " ").replace("|", "\\|")[:120]
        print(f"| {ex['item']['name']} | {code} | {verdict(code, struct_failed)} | "
              f"{'; '.join(struct_failed) or '-'} | `{body}` |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "run.json")
