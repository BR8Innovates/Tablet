#!/usr/bin/env python3
"""Turn a Newman JSON report into a per-request PASS / error / doc-update table (Markdown).

  newman run Trialx-Portal-APIs.postman_collection.json \
      -e Trialx.postman_environment.json \
      --env-var username=<machine user> --env-var password=<password> \
      --reporters cli,json --reporter-json-export run.json
  python3 summarize_run.py run.json > run-result.md

Every row's data (HTTP code, failed checks, response body) comes only from that
Newman run against the real trialx tenant - nothing here is invented or backfilled
from the spec.

Verdicts and what to do about each:
  ROUTE MISSING   gateway 404 (wrong path or unpublished API)         -> confirm the path with the platform/InsureMO team; if correct, the spec's endpoint is wrong and the doc needs updating.
  NO TOKEN        401 (credentials missing or wrong)                  -> check username/password in the environment; not a doc issue.
  NO PERMISSION   403 (API not granted to the tenant / user)          -> ask the API provider to grant the API to trialx; not a doc issue.
  REJECTED        other 4xx/5xx (request structure or data rejected)  -> read the response body; if trialx rejects a field the spec marks valid, the doc needs updating.
  STRUCTURE FAIL  2xx but a structure test failed                     -> the live response shape differs from the spec; the doc needs updating.
  OK              2xx and every structure test passed                 -> works as documented, no action needed.
"""
import json
import sys

NEXT_ACTION = {
    "ROUTE MISSING": "Confirm path with platform team; likely doc fix",
    "NO TOKEN": "Check username/password - not a doc issue",
    "NO PERMISSION": "Ask API owner to grant the API to trialx - not a doc issue",
    "REJECTED": "Read response body; may be a doc fix",
    "STRUCTURE FAIL": "Response differs from spec - doc fix likely needed",
    "OK": "-",
    "NO RESPONSE": "Request did not complete - re-run",
}


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
    rows = []
    print("| Request | HTTP | Verdict | Next action | Failed checks | Response (first 160 chars) |")
    print("|---|---|---|---|---|---|")
    for ex in run["executions"]:
        resp = ex.get("response") or {}
        code = resp.get("code")
        failed = [a["assertion"] for a in ex.get("assertions", []) if a.get("error")]
        struct_failed = [f for f in failed if "structure" in f]
        body = ""
        stream = resp.get("stream")
        if isinstance(stream, dict) and stream.get("data"):
            body = bytes(stream["data"]).decode("utf-8", "replace")
        body = body.replace("\n", " ").replace("|", "\\|")[:160]
        v = verdict(code, struct_failed)
        rows.append(v)
        print(f"| {ex['item']['name']} | {code} | {v} | {NEXT_ACTION[v]} | "
              f"{'; '.join(struct_failed) or '-'} | `{body}` |")
    from collections import Counter
    counts = Counter(rows)
    print()
    print("**Summary:** " + ", ".join(f"{v} {n}" for v, n in counts.most_common()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "run.json")
