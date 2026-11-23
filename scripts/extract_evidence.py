#!/usr/bin/env python3
"""Extract stable, source-bound resume claims from one HTML master."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path


SCHEMA_VERSION = "resume-evidence/v1"
AUDITED_SECTIONS = {"profile", "technical skills", "skills", "experience", "projects", "education", "additional information"}
METRIC_RE = re.compile(
    r"(?<![A-Za-z])(?:[$€£¥]\s*)?[+-]?\d[\d,]*(?:\.\d+)?(?:\s*(?:%|x|×|\+|/\d+[A-Za-z]?))?",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split()).strip()


def slug(text: str, limit: int = 38) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return (value[:limit].rstrip("-") or "claim")


def metrics(text: str) -> list[str]:
    return [normalize(match.group(0)) for match in METRIC_RE.finditer(text)]


class ResumeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section = ""
        self.headings: list[str] = []
        self.section_id = ""
        self.article: dict | None = None
        self.articles: list[dict] = []
        self.claims: list[dict] = []
        self.links: list[dict] = []
        self._captures: list[dict] = []
        self._ul_classes: list[set[str]] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = self._attrs(attrs)
        classes = set(data.get("class", "").split())
        if tag == "article" and "entry" in classes:
            self.article = {"title": "", "meta": "", "subhead": "", "section": self.section}
        if tag == "ul":
            self._ul_classes.append(classes)
        if tag == "a" and data.get("href"):
            self.links.append({"href": data["href"], "text": ""})
            self._captures.append({"tag": tag, "kind": "link", "parts": [], "target": self.links[-1]})
        if tag == "h2":
            self._captures.append({"tag": tag, "kind": "section", "parts": [], "id": data.get("id", "")})
        elif tag == "div" and classes.intersection({"entry-title", "entry-meta", "entry-subhead"}):
            kind = next(name for name in ("entry-title", "entry-meta", "entry-subhead") if name in classes)
            self._captures.append({"tag": tag, "kind": kind, "parts": []})
        elif tag == "li":
            list_classes = self._ul_classes[-1] if self._ul_classes else set()
            kind = "skill" if "skills" in list_classes else "bullet"
            self._captures.append({"tag": tag, "kind": kind, "parts": []})
        elif tag == "p" and self.section == "profile":
            self._captures.append({"tag": tag, "kind": "profile", "parts": []})
        elif tag == "p" and classes.intersection({"entry-summary", "additional"}):
            kind = next(name for name in ("entry-summary", "additional") if name in classes)
            self._captures.append({"tag": tag, "kind": kind, "parts": []})
        elif tag == "p" and self.section in AUDITED_SECTIONS:
            self._captures.append({"tag": tag, "kind": "bullet", "parts": []})
        elif tag == "section" and data.get("aria-labelledby") == "profile-title":
            self.section_id = "profile-title"

    def handle_data(self, data: str) -> None:
        for capture in self._captures:
            capture["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        completed = [capture for capture in self._captures if capture["tag"] == tag]
        for capture in reversed(completed):
            self._captures.remove(capture)
            text = normalize("".join(capture["parts"]))
            kind = capture["kind"]
            if kind == "link":
                capture["target"]["text"] = text
            elif kind == "section":
                self.headings.append(text)
                self.section = "profile" if text.casefold() == "summary" else text.casefold()
                self.section_id = capture.get("id", "")
                if self.article:
                    self.article["section"] = self.section
            elif kind in {"entry-title", "entry-meta", "entry-subhead"} and self.article is not None:
                self.article[kind.removeprefix("entry-")] = text
            elif kind == "entry-summary" and self.article is not None:
                self.article["summary"] = text
                if text and self.section in AUDITED_SECTIONS:
                    self.claims.append({
                        "section": self.section,
                        "kind": kind,
                        "text": text,
                        "article": dict(self.article),
                    })
            elif text and self.section in AUDITED_SECTIONS and kind in {"skill", "bullet", "entry-summary", "profile", "additional"}:
                self.claims.append({
                    "section": self.section,
                    "kind": kind,
                    "text": text,
                    "article": dict(self.article) if self.article else None,
                })
        if tag == "article" and self.article is not None:
            self.articles.append(self.article)
            self.article = None
        if tag == "ul" and self._ul_classes:
            self._ul_classes.pop()


def role_identity(article: dict | None) -> str | None:
    if not article:
        return None
    values = [article.get(key, "") for key in ("section", "title", "meta", "subhead")]
    return " | ".join(normalize(value).casefold() for value in values)


def extract(path: Path) -> dict:
    raw = path.read_bytes()
    parser = ResumeHTMLParser()
    parser.feed(raw.decode("utf-8"))
    claims = []
    seen_ids: set[str] = set()
    for claim in parser.claims:
        identity = role_identity(claim["article"])
        seed = "\n".join([claim["section"], identity or "", claim["kind"], claim["text"]])
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
        claim_id = f"claim-{slug(claim['section'])}-{digest}"
        if claim_id in seen_ids:
            raise ValueError(f"Duplicate claim identity: {claim_id}")
        seen_ids.add(claim_id)
        claims.append({
            "id": claim_id,
            "section": claim["section"],
            "kind": claim["kind"],
            "role_identity": identity,
            "text": claim["text"],
            "metrics": metrics(claim["text"]),
        })
    roles = []
    for article in parser.articles:
        if article.get("section") in {"experience", "projects", "education"}:
            roles.append({**article, "role_identity": role_identity(article)})
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()},
        "roles": roles,
        "links": parser.links,
        "claims": claims,
    }


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--html", required=True, type=Path)
    argp.add_argument("--output", required=True, type=Path)
    args = argp.parse_args()
    payload = extract(args.html)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "claims": len(payload["claims"]), "roles": len(payload["roles"]), "output": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
