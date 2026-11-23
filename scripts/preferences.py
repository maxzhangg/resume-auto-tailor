"""Load candidate-owned settings; no bundled candidate or layout defaults."""
from __future__ import annotations

import json
from pathlib import Path


def load_preferences(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema_version") != "resume-preferences/v1":
        raise ValueError("Expected resume-preferences/v1")
    for key in ("expected_pages", "max_pages", "project_count"):
        value = data.get(key)
        minimum = 0 if key == "project_count" else 1
        if value is not None and (type(value) is not int or value < minimum):
            raise ValueError(f"{key} must be null or an integer >= {minimum}")
    if data.get("expected_pages") and data.get("max_pages") and data["expected_pages"] > data["max_pages"]:
        raise ValueError("expected_pages cannot exceed max_pages")
    sections = data.get("section_order")
    if not isinstance(sections, list) or not all(isinstance(s, str) and s.strip() for s in sections):
        raise ValueError("section_order must be a list of nonempty heading strings")
    if len({s.casefold().strip() for s in sections}) != len(sections):
        raise ValueError("section_order contains duplicate headings")
    if data.get("fallback_policy") not in {"matched_only", "recent"}:
        raise ValueError("Choose fallback_policy: matched_only or recent")
    for key in ("language", "paper_size"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Choose {key}")
    if data["paper_size"] not in {"A4", "Letter"}:
        raise ValueError("paper_size must be A4 or Letter")
    for key in ("include_summary", "setup_complete"):
        if type(data.get(key)) is not bool:
            raise ValueError(f"{key} must be boolean")
    if not isinstance(data.get("experience_rules"), list) or not all(isinstance(r, str) for r in data["experience_rules"]):
        raise ValueError("experience_rules must be a list of instructions")
    if not isinstance(data.get("skill_order"), str):
        raise ValueError("skill_order must be a string instruction")
    return data
