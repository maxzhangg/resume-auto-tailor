#!/usr/bin/env python3
"""Create a fail-closed project-to-JD fit skeleton for a tailored resume."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from extract_evidence import extract


SCHEMA_VERSION = "resume-project-fit/v2"


def create(evidence: dict, draft: dict, draft_bytes: bytes) -> dict:
    project_roles = {
        role["role_identity"]: role
        for role in draft.get("roles", [])
        if role.get("section") == "projects"
    }
    project_claims: dict[str, list[dict]] = {identity: [] for identity in project_roles}
    for claim in draft.get("claims", []):
        if claim.get("section") == "projects" and claim.get("role_identity") in project_claims:
            project_claims[claim["role_identity"]].append(claim)

    projects = []
    for identity, role in project_roles.items():
        projects.append({
            "role_identity": identity,
            "title": role.get("title", ""),
            "selection_mode": "",
            "fit_level": "",
            "selection_reason": "",
            "requirement_ids": [],
            "claims": [
                {
                    "draft_claim_id": claim["id"],
                    "draft_text": claim["text"],
                    "fit_level": "",
                    "requirement_ids": [],
                    "recruiter_signal": "",
                }
                for claim in project_claims[identity]
            ],
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_source_sha256": evidence.get("source", {}).get("sha256", ""),
        "draft_sha256": hashlib.sha256(draft_bytes).hexdigest(),
        "projects": projects,
    }


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--evidence", required=True, type=Path)
    argp.add_argument("--draft", required=True, type=Path)
    argp.add_argument("--output", required=True, type=Path)
    args = argp.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    draft_bytes = args.draft.read_bytes()
    payload = create(evidence, extract(args.draft), draft_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    claim_count = sum(len(project["claims"]) for project in payload["projects"])
    print(json.dumps({
        "ok": True,
        "projects": len(payload["projects"]),
        "claims": claim_count,
        "output": str(args.output.resolve()),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
