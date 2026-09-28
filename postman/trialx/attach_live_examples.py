#!/usr/bin/env python3
"""Attach real, captured trialx responses as saved Postman examples - clearly
labeled with what actually happened, not just that something was captured -
and reorder the collection so working requests come first everywhere.

A saved example existing does NOT mean the call succeeded: this script tags
every item's own name with " (Pending)" whenever the real verdict (computed
the same way summarize_run.py computes it) is anything other than OK, and
leaves a working request's name plain. It then reorders every folder's items,
and the top-level folders themselves, so requests/folders with fewer pending
results sort first - working APIs first, pending ones at the end, in every
folder. Nothing is invented: every example is a response trialx itself
returned during the live run recorded in the given Newman report. Any
access_token seen in a body is redacted before it is written anywhere.

Requests that were deliberately excluded from that run (Upload Document,
FNOL, SMS/Email sends - see README.md) get no example and are tagged
"(Pending)" too: there is no real response to attach, and none is
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
PENDING_SUFFIX = " (Pending)"
_PENDING_RE = re.compile(re.escape(PENDING_SUFFIX) + r"\s*$")


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
        "name": f"{v} {code} {status} — real trialx response, {RUN_DATE}".strip(),
        "originalRequest": {"method": req.get("method"), "header": req.get("header", []),
                             "url": req.get("url"), "body": req.get("body")},
        "status": status,
        "code": code,
        "_postman_previewlanguage": "json",
        "header": headers,
        "body": body,
    }


def attach(items, examples_by_id, stats):
    """Tags names, attaches examples, then sorts this level so working items come
    first. Sorted by the fraction pending, not the raw count - otherwise a folder
    that is 96% working (e.g. 4 pending of 101) would sort after a 2-item folder
    that is 100% broken, just because 4 > 2. Ties keep their original relative
    order (Python's sort is stable). Returns (reordered items, pending count,
    total count at this level) so a parent folder can compute its own fraction."""
    entries = []
    for it in items:
        if "item" in it:
            new_children, pending_count, total_count = attach(it["item"], examples_by_id, stats)
            it["item"] = new_children
            entries.append((it, pending_count, total_count))
        else:
            base_name = _PENDING_RE.sub("", it["name"])
            ex = examples_by_id.get(it["id"])
            if ex is not None:
                v, code = real_verdict(ex)
                it["response"] = [build_example(it, ex, v, code)]
                pending = 0 if v == "OK" else 1
                stats[v] = stats.get(v, 0) + 1
            else:
                it["response"] = []
                pending = 1
                stats["NOT RUN"] = stats.get("NOT RUN", 0) + 1
            it["name"] = base_name + (PENDING_SUFFIX if pending else "")
            entries.append((it, pending, 1))
    entries.sort(key=lambda e: e[1] / e[2] if e[2] else 0)  # fraction pending, working (0.0) first
    total_pending = sum(p for _, p, _ in entries)
    total = sum(t for _, _, t in entries)
    return [it for it, _, _ in entries], total_pending, total


def main(run_path):
    coll_path = os.path.join(HERE, "Trialx-Portal-APIs.postman_collection.json")
    coll = json.load(open(coll_path, encoding="utf-8"))
    run = json.load(open(run_path, encoding="utf-8"))["run"]

    examples_by_id = {ex["item"]["id"]: ex for ex in run["executions"]}  # last one wins if re-run

    stats = {}
    coll["item"], _, _ = attach(coll["item"], examples_by_id, stats)
    total = sum(stats.values())
    ok = stats.get("OK", 0)

    coll["info"]["description"] += (
        f"\n\n**A saved example does not mean the request succeeded, and a plain name does not mean it is untested.** "
        f"Every non-OK request's name ends in \"{PENDING_SUFFIX.strip()}\"; a plain name means it returned a real 2xx response "
        f"matching the spec on {RUN_DATE} (real Machine User run). Working requests are sorted first in every folder, and "
        f"folders with fewer pending requests sort before folders with more, so the collection reads working-first top to bottom. "
        + ", ".join(f"**{v}** {n}" for v, n in sorted(stats.items(), key=lambda kv: -kv[1]))
        + f". Only the {ok} plain-named requests (of {total}) passed. "
        "\"(Pending)\" requests without an example are the write/side-effect ones deliberately excluded from that run "
        "(Upload Document, FNOL, SMS/Email sends) - no example is invented for them. Every other \"(Pending)\" request carries the "
        "real response trialx sent back, credentials/tokens redacted; open its Examples tab to read it.")

    json.dump(coll, open(coll_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(coll_path, "a", encoding="utf-8").write("\n")
    print("tagged", total, "requests:", dict(sorted(stats.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "run-live.json")
