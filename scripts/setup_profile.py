"""Initialize a private workspace without overwriting it, or check onboarding readiness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from extract_evidence import extract, ResumeHTMLParser
from preferences import load_preferences

SKILL = Path(__file__).resolve().parents[1]


def initialize(workspace: Path) -> list[str]:
    private = workspace / "private"
    private.mkdir(parents=True, exist_ok=True)
    created = []
    for source, target in (("master-template.html", "master.html"), ("preferences.example.json", "preferences.json")):
        destination = private / target
        try:
            with destination.open("x", encoding="utf-8") as stream:
                stream.write((SKILL / "assets" / source).read_text(encoding="utf-8"))
            created.append(str(destination))
        except FileExistsError:
            pass
    ignore = workspace / ".gitignore"
    current = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    missing = [line for line in ("/private/", "/output/") if line not in current.splitlines()]
    if missing:
        with ignore.open("a", encoding="utf-8") as stream:
            stream.write(("\n" if current and not current.endswith("\n") else "") + "\n".join(missing) + "\n")
    return created


def status(workspace: Path) -> dict:
    issues = []
    private = workspace / "private"
    preferences = None
    try:
        preferences = load_preferences(private / "preferences.json")
        if not preferences["setup_complete"]:
            issues.append("Confirm the converted master and preferences with the user, then set setup_complete=true.")
        if not preferences["section_order"]:
            issues.append("Choose the actual section headings and their order.")
    except (OSError, ValueError) as exc:
        issues.append(f"Preferences: {exc}")
    try:
        master = private / "master.html"
        raw = master.read_text(encoding="utf-8")
        if "{{" in raw or "}}" in raw:
            issues.append("Replace or remove every starter placeholder in master.html.")
        evidence = extract(master)
        if not evidence["claims"]:
            issues.append("The master has no extractable evidence; adapt its HTML to the template contract.")
        parser = ResumeHTMLParser()
        parser.feed(raw)
        if preferences:
            from verify_pdf import normalize_heading
            headings = [normalize_heading(s) for s in parser.headings]
            missing = [s for s in preferences["section_order"] if normalize_heading(s) not in headings]
            if missing:
                issues.append("Configured sections absent from master: " + ", ".join(missing))
    except (OSError, ValueError) as exc:
        issues.append(f"Master: {exc}")
    return {"ready": not issues, "issues": issues, "workspace": str(workspace.resolve())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "status"])
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "init":
        print(json.dumps({"created": initialize(args.workspace), "next": "Follow references/onboarding.md; starter files are not candidate evidence."}))
        return 0
    report = status(args.workspace)
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
