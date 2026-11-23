#!/usr/bin/env python3
"""Fail-closed provenance and metric audit for a tailored HTML resume."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from extract_evidence import SCHEMA_VERSION, extract


MANIFEST_VERSION = "resume-provenance-manifest/v1"
SAME_ROLE_SECTIONS = {"experience", "projects", "education"}


def audit(evidence: dict, draft: dict, manifest: dict, draft_bytes: bytes) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    def error(code: str, message: str, claim_id: str | None = None) -> None:
        errors.append({"code": code, "claim_id": claim_id, "message": message})

    if evidence.get("schema_version") != SCHEMA_VERSION:
        error("EVIDENCE_SCHEMA", "Unsupported evidence schema")
    if manifest.get("schema_version") != MANIFEST_VERSION:
        error("MANIFEST_SCHEMA", "Unsupported manifest schema")
    if manifest.get("evidence_source_sha256") != evidence.get("source", {}).get("sha256"):
        error("EVIDENCE_DIGEST", "Manifest is not bound to this master resume")
    actual_draft_hash = hashlib.sha256(draft_bytes).hexdigest()
    if manifest.get("draft_sha256") != actual_draft_hash:
        error("DRAFT_DIGEST", "Manifest is stale or belongs to another draft")

    if not evidence.get("claims") or not draft.get("claims"):
        error("NO_EXTRACTED_CLAIMS", "Master and draft must contain extractable evidence; check the HTML contract")

    source_by_id = {claim["id"]: claim for claim in evidence.get("claims", [])}
    draft_by_id = {claim["id"]: claim for claim in draft.get("claims", [])}
    mappings = manifest.get("claims")
    if not isinstance(mappings, list):
        error("MANIFEST_CLAIMS", "Manifest claims must be a list")
        mappings = []
    mapping_by_id: dict[str, dict] = {}
    for item in mappings:
        if not isinstance(item, dict) or not isinstance(item.get("draft_claim_id"), str):
            error("MANIFEST_ENTRY", "Malformed manifest claim entry")
            continue
        claim_id = item["draft_claim_id"]
        if claim_id in mapping_by_id:
            error("DUPLICATE_MAPPING", "Draft claim appears more than once", claim_id)
        mapping_by_id[claim_id] = item

    source_roles = {role["role_identity"] for role in evidence.get("roles", [])}
    for role in draft.get("roles", []):
        if role.get("role_identity") not in source_roles:
            error("UNSUPPORTED_ROLE", f"Role metadata changed or was invented: {role.get('role_identity')}")

    for claim_id, claim in draft_by_id.items():
        item = mapping_by_id.get(claim_id)
        if item is None:
            error("UNMAPPED_CLAIM", "Draft claim has no manifest entry", claim_id)
            continue
        if item.get("draft_text") != claim["text"]:
            error("CLAIM_TEXT_MISMATCH", "Manifest text differs from draft", claim_id)
        source_ids = item.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            error("NO_PROVENANCE", "Draft claim has no evidence source", claim_id)
            continue
        if not isinstance(item.get("rationale"), str) or not item.get("rationale", "").strip():
            error("NO_RATIONALE", "Draft claim has no tailoring rationale", claim_id)
        sources = []
        for source_id in source_ids:
            source = source_by_id.get(source_id)
            if source is None:
                error("UNKNOWN_SOURCE", f"Unknown evidence ID: {source_id}", claim_id)
            else:
                sources.append(source)
        if not sources:
            continue
        if claim["section"] in SAME_ROLE_SECTIONS:
            for source in sources:
                if source.get("role_identity") != claim.get("role_identity"):
                    error("CROSS_ROLE_SOURCE", f"Source {source['id']} belongs to another role/project", claim_id)
        supported_metrics = {metric for source in sources for metric in source.get("metrics", [])}
        for metric in claim.get("metrics", []):
            if metric not in supported_metrics:
                error("UNSUPPORTED_METRIC", f"Metric {metric!r} is absent from mapped evidence", claim_id)

    for claim_id in mapping_by_id:
        if claim_id not in draft_by_id:
            error("STALE_MAPPING", "Manifest contains a claim absent from the draft", claim_id)

    coverage = 1.0 if not draft_by_id else (len(draft_by_id) - sum(1 for cid in draft_by_id if cid not in mapping_by_id)) / len(draft_by_id)
    return {
        "schema_version": "resume-provenance-report/v1",
        "verdict": "PASS" if not errors else "FAIL",
        "draft_sha256": actual_draft_hash,
        "claim_count": len(draft_by_id),
        "manifest_count": len(mapping_by_id),
        "coverage": round(coverage, 4),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--evidence", required=True, type=Path)
    argp.add_argument("--draft", required=True, type=Path)
    argp.add_argument("--manifest", required=True, type=Path)
    argp.add_argument("--output", required=True, type=Path)
    args = argp.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    draft_bytes = args.draft.read_bytes()
    draft = extract(args.draft)
    report = audit(evidence, draft, manifest, draft_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["verdict"] == "PASS", "errors": len(report["errors"]), "output": str(args.output.resolve())}))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
