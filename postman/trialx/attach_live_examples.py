#!/usr/bin/env python3
"""Attach real, captured trialx responses as saved Postman examples - clearly
labeled with what actually happened, not just that something was captured.

A saved example existing does NOT mean the call succeeded: this script tags
every item's own name and its example's name with the real verdict (OK,
STRUCTURE FAIL, REJECTED, ROUTE MISSING, ...) computed the same way
summarize_run.py computes it, so pass vs fail is visible in the Postman
sidebar without opening the request. Nothing is invented: every example is a
response trialx itself returned during the live run recorded in run-live.json
(28 Sep 2026, Machine User ravi.teja@insuremo.com, tenant trialx). Any
access_token seen in a body is redacted before it is written anywhere.

Requests that were deliberately excluded from that run (Upload Document,
FNOL, SMS/Email sends - see README.md) get no example and are tagged
[NOT RUN] instead: there is no real response to attach, and none is
fabricated to fill the gap.

Run after build_collections.py, pointing at the Newman JSON report:
  python3 attach_live_examples.py /path/to/run-live.json
"""
import json
import os
import re
import sys
import uuid

from summarize_run import verdict

HERE = os.path.dirname(os.path.abspath(__file__))
NS = uuid.UUID("5b1f3c0e-7a51-4d0c-9d44-7f1e0c2b9a10")
RUN_DATE = "28 Sep 2026"

TAG = {
    "OK": "[OK]",
    "STRUCTURE FAIL": "[STRUCTURE FAIL]",
    "REJECTED": "[REJECTED]",
    "ROUTE MISSING": "[ROUTE MISSING]",
    "NO TOKEN": "[NO TOKEN]",
    "NO PERMISSION": "[NO PERMISSION]",
    "NO RESPONSE": "[NO RESPONSE]",
}


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def redact(body: str) -> str:
    return re.sub(r'"access_token"\s*:\s*"[^"]*"', '"access_token":"<redacted>"', body)


def real_verdict(ex):
    resp = ex.get("response") or {}
    code = resp.get("code")
    struct_failed = [a["assertion"] for a in ex.get("assertions", [])
                      if a.get("error") and "structure" in a["assertion"]]
    return verdict(code, struct_failed), code


def build_example(item, ex, v, code):
    """originalRequest MUST come from the collection item's own templated request
    ({{username}}, {{password}}, ...) - never from ex["request"], which is what
    Newman actually sent after resolving every variable, so it contains the real
    plaintext password and would leak it straight into the committed collection."""
    resp = ex.get("response") or {}
    status = resp.get("status") or ""
    stream = resp.get("stream")
    body = ""
    if isinstance(stream, dict) and stream.get("data"):
        body = bytes(stream["data"]).decode("utf-8", "replace")
    body = redact(body)
    headers = [{"key": h.get("key", ""), "value": h.get("value", "")}
               for h in (resp.get("header") or []) if h.get("key", "").lower() != "set-cookie"]
    req = item["request"]
    return {
        "id": uid(item["id"], "live-example"),
        "name": f"{TAG.get(v, '['+v+']')} {code} {status} — real trialx response, {RUN_DATE}".strip(),
        "originalRequest": {"method": req.get("method"), "header": req.get("header", []),
                             "url": req.get("url"), "body": req.get("body")},
        "status": status,
        "code": code,
        "_postman_previewlanguage": "json",
        "header": headers,
        "body": body,
    }


def attach(items, examples_by_id, stats):
    for it in items:
        if "item" in it:
            attach(it["item"], examples_by_id, stats)
        else:
            base_name = re.sub(r"^\[[^\]]+\]\s*", "", it["name"])
            ex = examples_by_id.get(it["id"])
            if ex is not None:
                v, code = real_verdict(ex)
                it["response"] = [build_example(it, ex, v, code)]
                it["name"] = f"{TAG.get(v, '['+v+']')} {base_name}"
                stats[v] = stats.get(v, 0) + 1
            else:
                it["response"] = []
                it["name"] = f"[NOT RUN] {base_name}"
                stats["NOT RUN"] = stats.get("NOT RUN", 0) + 1


def main(run_path):
    coll_path = os.path.join(HERE, "Trialx-Portal-APIs.postman_collection.json")
    coll = json.load(open(coll_path, encoding="utf-8"))
    run = json.load(open(run_path, encoding="utf-8"))["run"]

    examples_by_id = {ex["item"]["id"]: ex for ex in run["executions"]}  # last one wins if re-run

    stats = {}
    attach(coll["item"], examples_by_id, stats)
    total = sum(stats.values())
    ok = stats.get("OK", 0)

    coll["info"]["description"] += (
        f"\n\n**A saved example does not mean the request succeeded.** Every request's name is tagged with "
        f"what trialx actually returned on {RUN_DATE} (real Machine User run): "
        + ", ".join(f"**{v}** {n}" for v, n in sorted(stats.items(), key=lambda kv: -kv[1]))
        + f". Only **[OK]** ({ok} of {total}) means a 2xx response whose shape matched the spec. "
        "[NOT RUN] requests are the write/side-effect ones deliberately excluded from that run "
        "(Upload Document, FNOL, SMS/Email sends) - no example is invented for them. Every other tag is the "
        "real response trialx sent back, credentials/tokens redacted; open the request's Examples tab to read it.")

    json.dump(coll, open(coll_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(coll_path, "a", encoding="utf-8").write("\n")
    print("tagged", total, "requests:", dict(sorted(stats.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "run-live.json")
