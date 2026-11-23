#!/usr/bin/env python3
"""Fail-closed structural audit for project-to-job fit mappings."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from create_project_fit import SCHEMA_VERSION
from extract_evidence import extract
from preferences import load_preferences


ALLOWED_FIT_LEVELS = {"direct", "adjacent", "weak", "recent_fallback"}
ALLOWED_SELECTION_MODES = {"matched", "recent_fallback"}
LAYOUT_SELECTION_RE = re.compile(
    r"\b(?:page|pages|pagination|layout|density|whitespace|white\s+space|fill|filler|balance|overflow)\b",
    re.IGNORECASE,
)


def requirement_index(requirements: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            requirement_id = value.get("id")
            if isinstance(requirement_id, str) and requirement_id.strip():
                found[requirement_id] = value
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(requirements)
    return found


def project_recency_key(role: dict, index: int) -> tuple[int, int, int, int]:
    meta = str(role.get("meta", ""))
    dates = [
        (int(match.group(1)), int(match.group(2) or 0))
        for match in re.finditer(r"(?<!\d)(20\d{2})(?:[.\-/](\d{1,2}))?", meta)
    ]
    newest_year, newest_month = max(dates, default=(0, 0))
    is_present = 1 if re.search(r"\bpresent\b", meta, re.IGNORECASE) else 0
    return (is_present, newest_year, newest_month, -index)


def audit(requirements: dict, evidence: dict, draft: dict, project_fit: dict, draft_bytes: bytes, project_count: int | None = None, fallback_policy: str = "matched_only") -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []

    def error(code: str, message: str, identity: str | None = None, claim_id: str | None = None) -> None:
        errors.append({
            "code": code,
            "project_identity": identity,
            "claim_id": claim_id,
            "message": message,
        })

    if project_fit.get("schema_version") != SCHEMA_VERSION:
        error("PROJECT_FIT_SCHEMA", "Unsupported project-fit schema")
    if project_fit.get("evidence_source_sha256") != evidence.get("source", {}).get("sha256"):
        error("EVIDENCE_DIGEST", "Project-fit mapping is not bound to this master resume")

    actual_draft_hash = hashlib.sha256(draft_bytes).hexdigest()
    if project_fit.get("draft_sha256") != actual_draft_hash:
        error("DRAFT_DIGEST", "Project-fit mapping is stale or belongs to another draft")

    requirement_by_id = requirement_index(requirements)
    if not requirement_by_id:
        error("NO_REQUIREMENT_IDS", "requirements.json must assign stable IDs to its requirement records")

    draft_projects = {
        role["role_identity"]: role
        for role in draft.get("roles", [])
        if role.get("section") == "projects"
    }
    source_projects = [
        role for role in evidence.get("roles", [])
        if role.get("section") == "projects"
    ]
    source_project_identities = {role.get("role_identity") for role in source_projects}
    if project_count is not None and (type(project_count) is not int or project_count < 0):
        raise ValueError("project_count must be null or a nonnegative integer")
    if fallback_policy not in {"recent", "matched_only"}:
        raise ValueError("Unknown fallback policy")
    target_project_count = min(project_count, len(source_projects)) if project_count is not None else len(draft_projects)
    if len(draft_projects) != target_project_count:
        error(
            "PROJECT_COUNT",
            f"Draft must retain {target_project_count} projects: matched projects first, then newest unused projects as fallback",
        )
    draft_claims = {
        claim["id"]: claim
        for claim in draft.get("claims", [])
        if claim.get("section") == "projects"
    }
    projects = project_fit.get("projects")
    if not isinstance(projects, list):
        error("PROJECTS_LIST", "project-fit projects must be a list")
        projects = []

    mapped_projects: dict[str, dict] = {}
    mapped_claims: dict[str, dict] = {}
    for project in projects:
        if not isinstance(project, dict) or not isinstance(project.get("role_identity"), str):
            error("PROJECT_ENTRY", "Malformed project-fit project entry")
            continue
        identity = project["role_identity"]
        if identity in mapped_projects:
            error("DUPLICATE_PROJECT", "Project appears more than once in project-fit mapping", identity)
        mapped_projects[identity] = project
        if identity not in draft_projects:
            error("STALE_PROJECT", "Project-fit mapping contains a project absent from the draft", identity)
        if identity not in source_project_identities:
            error("UNKNOWN_SOURCE_PROJECT", "Draft project is absent from the master resume", identity)

        selection_mode = project.get("selection_mode")
        if selection_mode not in ALLOWED_SELECTION_MODES:
            error("SELECTION_MODE", "selection_mode must be matched or recent_fallback", identity)

        fit_level = project.get("fit_level")
        if fit_level not in ALLOWED_FIT_LEVELS:
            error("PROJECT_FIT_LEVEL", "Project fit_level must be direct, adjacent, weak, or recent_fallback", identity)
        elif selection_mode == "matched" and fit_level != "direct":
            error("NON_DIRECT_MATCH", "Matched projects must directly support the target job", identity)
        elif selection_mode == "recent_fallback" and fit_level != "recent_fallback":
            error("FALLBACK_FIT_LEVEL", "Recent fallback projects must use fit_level recent_fallback", identity)

        selection_reason = project.get("selection_reason")
        if not isinstance(selection_reason, str) or not selection_reason.strip():
            error("NO_SELECTION_REASON", "Project requires a recruiter-visible selection reason", identity)
        elif LAYOUT_SELECTION_RE.search(selection_reason):
            error("LAYOUT_DRIVEN_PROJECT_SELECTION", "Project selection cannot be justified by page or layout goals", identity)

        project_requirement_ids = project.get("requirement_ids")
        if not isinstance(project_requirement_ids, list):
            error("PROJECT_REQUIREMENTS", "Project requirement_ids must be a list", identity)
            project_requirement_ids = []
        if selection_mode == "matched" and not project_requirement_ids:
            error("NO_PROJECT_REQUIREMENTS", "Matched project must map to at least one supported target requirement", identity)
        valid_project_requirement_ids: set[str] = set()
        has_supported_requirement = False
        for requirement_id in project_requirement_ids:
            requirement = requirement_by_id.get(requirement_id)
            if requirement is None:
                error("UNKNOWN_REQUIREMENT", f"Unknown requirement ID: {requirement_id}", identity)
                continue
            valid_project_requirement_ids.add(requirement_id)
            if requirement.get("coverage") == "unsupported_gap":
                error("UNSUPPORTED_REQUIREMENT_MAPPING", f"Project cannot claim unsupported requirement: {requirement_id}", identity)
            else:
                has_supported_requirement = True
        if selection_mode == "matched" and project_requirement_ids and not has_supported_requirement:
            error("NO_SUPPORTED_MATCH", "Matched project must directly support at least one non-gap requirement", identity)

        claim_entries = project.get("claims")
        if not isinstance(claim_entries, list):
            error("PROJECT_CLAIMS", "Project claims must be a list", identity)
            claim_entries = []
        direct_claims = 0
        for item in claim_entries:
            if not isinstance(item, dict) or not isinstance(item.get("draft_claim_id"), str):
                error("PROJECT_CLAIM_ENTRY", "Malformed project claim mapping", identity)
                continue
            claim_id = item["draft_claim_id"]
            if claim_id in mapped_claims:
                error("DUPLICATE_CLAIM", "Project claim appears more than once", identity, claim_id)
            mapped_claims[claim_id] = item
            claim = draft_claims.get(claim_id)
            if claim is None:
                error("STALE_PROJECT_CLAIM", "Mapped project claim is absent from the draft", identity, claim_id)
                continue
            if claim.get("role_identity") != identity:
                error("CROSS_PROJECT_CLAIM", "Claim mapping belongs to another project", identity, claim_id)
            if item.get("draft_text") != claim.get("text"):
                error("CLAIM_TEXT_MISMATCH", "Project-fit text differs from the draft", identity, claim_id)

            claim_fit = item.get("fit_level")
            if claim_fit not in ALLOWED_FIT_LEVELS:
                error("CLAIM_FIT_LEVEL", "Claim fit_level must be direct, adjacent, weak, or recent_fallback", identity, claim_id)
            elif selection_mode == "matched":
                if claim_fit == "weak" or claim_fit == "recent_fallback":
                    error("WEAK_PROJECT_CLAIM", "Matched-project claims must be direct or adjacent", identity, claim_id)
                elif claim_fit == "direct":
                    direct_claims += 1
            elif selection_mode == "recent_fallback" and claim_fit != "recent_fallback":
                error("FALLBACK_CLAIM_LEVEL", "Fallback-project claims must use fit_level recent_fallback", identity, claim_id)

            claim_requirement_ids = item.get("requirement_ids")
            if not isinstance(claim_requirement_ids, list):
                error("CLAIM_REQUIREMENTS", "Claim requirement_ids must be a list", identity, claim_id)
                claim_requirement_ids = []
            if selection_mode == "matched" and not claim_requirement_ids:
                error("NO_CLAIM_REQUIREMENTS", "Every matched-project claim must map to a target requirement", identity, claim_id)
            for requirement_id in claim_requirement_ids:
                if requirement_id not in requirement_by_id:
                    error("UNKNOWN_REQUIREMENT", f"Unknown requirement ID: {requirement_id}", identity, claim_id)
                elif requirement_id not in valid_project_requirement_ids:
                    error("CLAIM_REQUIREMENT_SCOPE", f"Claim requirement {requirement_id} is absent from the project mapping", identity, claim_id)
                elif requirement_by_id[requirement_id].get("coverage") == "unsupported_gap":
                    error("UNSUPPORTED_REQUIREMENT_MAPPING", f"Claim cannot map to unsupported requirement: {requirement_id}", identity, claim_id)

            recruiter_signal = item.get("recruiter_signal")
            if not isinstance(recruiter_signal, str) or not recruiter_signal.strip():
                error("NO_RECRUITER_SIGNAL", "State what job-relevant signal the claim makes visible without inference", identity, claim_id)

        if selection_mode == "matched":
            if direct_claims == 0:
                error("NO_DIRECT_PROJECT_CLAIM", "Matched project must contain at least one directly relevant claim", identity)
            else:
                first_claim = next((item for item in claim_entries if isinstance(item, dict)), None)
                if first_claim is not None and first_claim.get("fit_level") != "direct":
                    error("MATCH_NOT_FOREGROUNDED", "The summary or first visible claim must foreground the project's direct job match", identity, first_claim.get("draft_claim_id"))

    for identity in draft_projects:
        if identity not in mapped_projects:
            error("UNMAPPED_PROJECT", "Draft project has no project-fit entry", identity)
    for claim_id, claim in draft_claims.items():
        if claim_id not in mapped_claims:
            error("UNMAPPED_PROJECT_CLAIM", "Draft project claim has no project-fit mapping", claim.get("role_identity"), claim_id)

    matched_identities = {
        identity for identity, project in mapped_projects.items()
        if project.get("selection_mode") == "matched" and identity in draft_projects
    }
    fallback_identities = {
        identity for identity, project in mapped_projects.items()
        if project.get("selection_mode") == "recent_fallback" and identity in draft_projects
    }
    fallback_seen = False
    for identity in draft_projects:
        selection_mode = mapped_projects.get(identity, {}).get("selection_mode")
        if selection_mode == "recent_fallback":
            fallback_seen = True
        elif selection_mode == "matched" and fallback_seen:
            error("MATCHED_PROJECT_ORDER", "Matched projects must appear before recent fallback projects", identity)
    if fallback_policy == "matched_only" and fallback_identities:
        error("FALLBACK_DISABLED", "Candidate preferences allow only directly matched projects")
    required_fallback_count = max(0, target_project_count - len(matched_identities)) if fallback_policy == "recent" else 0
    if len(fallback_identities) != required_fallback_count:
        error(
            "FALLBACK_COUNT",
            f"Expected {required_fallback_count} recent fallback projects after {len(matched_identities)} matched projects",
        )
    newest_unused = [
        role.get("role_identity")
        for index, role in sorted(
            enumerate(source_projects),
            key=lambda item: project_recency_key(item[1], item[0]),
            reverse=True,
        )
        if role.get("role_identity") not in matched_identities
    ][:required_fallback_count]
    if fallback_identities != set(newest_unused):
        error(
            "RECENT_FALLBACK_SELECTION",
            "Fallback projects must be the newest unused projects from the master resume",
        )

    return {
        "schema_version": "resume-project-fit-report/v2",
        "verdict": "PASS" if not errors else "FAIL",
        "draft_sha256": actual_draft_hash,
        "project_count": len(draft_projects),
        "target_project_count": target_project_count,
        "matched_project_count": len(matched_identities),
        "recent_fallback_count": len(fallback_identities),
        "project_claim_count": len(draft_claims),
        "requirement_count": len(requirement_by_id),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--requirements", required=True, type=Path)
    argp.add_argument("--evidence", required=True, type=Path)
    argp.add_argument("--draft", required=True, type=Path)
    argp.add_argument("--project-fit", required=True, type=Path)
    argp.add_argument("--output", required=True, type=Path)
    argp.add_argument("--preferences", type=Path)
    argp.add_argument("--project-count", type=int, help="Exact count capped by available source projects; omit for no fixed count")
    argp.add_argument("--fallback-policy", choices=["matched_only", "recent"])
    args = argp.parse_args()
    requirements = json.loads(args.requirements.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    project_fit = json.loads(args.project_fit.read_text(encoding="utf-8"))
    draft_bytes = args.draft.read_bytes()
    prefs = load_preferences(args.preferences) if args.preferences else {}
    count = args.project_count if args.project_count is not None else prefs.get("project_count")
    policy = args.fallback_policy or prefs.get("fallback_policy", "matched_only")
    report = audit(requirements, evidence, extract(args.draft), project_fit, draft_bytes, count, policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": report["verdict"] == "PASS",
        "errors": len(report["errors"]),
        "output": str(args.output.resolve()),
    }))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
