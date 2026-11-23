#!/usr/bin/env python3
"""Create a provenance manifest skeleton for a tailored HTML resume."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from extract_evidence import SCHEMA_VERSION, extract


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--evidence", required=True, type=Path)
    argp.add_argument("--draft", required=True, type=Path)
    argp.add_argument("--output", required=True, type=Path)
    args = argp.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit("Unsupported evidence schema")
    draft = extract(args.draft)
    source_by_text: dict[str, list[str]] = {}
    for claim in evidence["claims"]:
        source_by_text.setdefault(claim["text"], []).append(claim["id"])
    mappings = []
    for claim in draft["claims"]:
        mappings.append({
            "draft_claim_id": claim["id"],
            "draft_text": claim["text"],
            "source_ids": source_by_text.get(claim["text"], []),
            "rationale": "Unchanged from master." if claim["text"] in source_by_text else "",
        })
    raw_draft = args.draft.read_bytes()
    payload = {
        "schema_version": "resume-provenance-manifest/v1",
        "evidence_source_sha256": evidence["source"]["sha256"],
        "draft_sha256": hashlib.sha256(raw_draft).hexdigest(),
        "claims": mappings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    empty = sum(not item["source_ids"] for item in mappings)
    print(json.dumps({"ok": True, "claims": len(mappings), "unmapped": empty, "output": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
