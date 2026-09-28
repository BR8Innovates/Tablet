#!/usr/bin/env python3
"""Attach real, captured trialx responses as saved Postman examples.

This does NOT invent anything: every example it writes is a response that
trialx itself returned during the live run recorded in run-live.json
(28 Sep 2026, Machine User ravi.teja@insuremo.com, tenant trialx). Any
access_token seen in a body is redacted before it is written anywhere.

Requests that were deliberately excluded from that run (Upload Document,
FNOL, SMS/Email sends - see README.md) get no example: there is no real
response to attach, and none is fabricated to fill the gap.

Run after build_collections.py, pointing at the Newman JSON report:
  python3 attach_live_examples.py /path/to/run-live.json
"""
import json
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NS = uuid.UUID("5b1f3c0e-7a51-4d0c-9d44-7f1e0c2b9a10")
RUN_DATE = "28 Sep 2026"
RUN_LABEL = f"Captured from trialx, {RUN_DATE} (real Machine User run)"


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def redact(body: str) -> str:
    return re.sub(r'"access_token"\s*:\s*"[^"]*"', '"access_token":"<redacted>"', body)


def build_example(item, ex):
    """originalRequest MUST come from the collection item's own templated request
    ({{username}}, {{password}}, ...) - never from ex["request"], which is what
    Newman actually sent after resolving every variable, so it contains the real
    plaintext password and would leak it straight into the committed collection."""
    resp = ex.get("response") or {}
    code = resp.get("code")
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
        "name": f"{RUN_LABEL} — {code} {status}".strip(),
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
            ex = examples_by_id.get(it["id"])
            if ex is not None:
                it["response"] = [build_example(it, ex)]
                stats["attached"] += 1
            else:
                stats["skipped"] += 1


def main(run_path):
    coll_path = os.path.join(HERE, "Trialx-Portal-APIs.postman_collection.json")
    coll = json.load(open(coll_path, encoding="utf-8"))
    run = json.load(open(run_path, encoding="utf-8"))["run"]

    examples_by_id = {}
    for ex in run["executions"]:
        item_id = ex["item"]["id"]
        # keep the last execution per id if a request ran more than once
        examples_by_id[item_id] = ex

    stats = {"attached": 0, "skipped": 0}
    attach(coll["item"], examples_by_id, stats)

    coll["info"]["description"] += (
        f"\n\n**{stats['attached']} of {stats['attached'] + stats['skipped']} requests carry a saved example "
        f"captured from a real trialx call on {RUN_DATE}** (credentials/tokens redacted). The "
        f"{stats['skipped']} without one are either write/side-effect requests deliberately excluded from "
        "that run (Upload Document, FNOL, SMS/Email sends), or the folder/table requests where real "
        "business data (a real customerId, attachFileId, businessType, table name...) was not available "
        "in this run. No example anywhere in this collection was invented.")

    json.dump(coll, open(coll_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(coll_path, "a", encoding="utf-8").write("\n")
    print(f"attached {stats['attached']} real examples, {stats['skipped']} requests have none (see reason above)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "run-live.json")
