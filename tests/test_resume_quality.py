from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_draft import audit  # noqa: E402
from audit_layout import audit_layout  # noqa: E402
from audit_project_fit import audit as configurable_project_audit  # noqa: E402
from create_project_fit import create as create_project_fit  # noqa: E402
from extract_evidence import extract  # noqa: E402
from verify_pdf import verify  # noqa: E402


def audit_project_fit(requirements, evidence, draft, mapping, raw):
    return configurable_project_audit(requirements, evidence, draft, mapping, raw, project_count=3, fallback_policy="recent")


MASTER = """<!doctype html>
<html><body><main>
<section aria-labelledby="profile-title"><h2 id="profile-title">Profile</h2>
<p class="additional">QA analyst focused on transaction validation.</p></section>
<section><h2>Technical Skills</h2><ul class="skills">
<li><strong>Testing:</strong> regression testing, Playwright, SQL</li></ul></section>
<section><h2>Experience</h2><article class="entry">
<div class="entry-head"><div class="entry-title">QA Tester</div><div class="entry-meta">2026-present</div></div>
<div class="entry-subhead"><em>Example Co</em><span>Remote</span></div>
<ul class="bullets"><li>Documented 40+ defects with reproduction evidence.</li></ul>
</article></section></main></body></html>"""


PROJECT_MASTER = """<!doctype html>
<html><body><main>
<section><h2>Technical Skills</h2><ul class="skills">
<li><strong>Testing:</strong> API validation, SQL</li></ul></section>
<section><h2>Projects</h2><article class="entry">
<div class="entry-head"><div class="entry-title">Recovery Validator</div><div class="entry-meta">2026</div></div>
<p class="entry-summary">Built a service reliability validation tool.</p>
<ul class="bullets"><li>Validated failure and recovery behavior across API and database boundaries.</li></ul>
</article></section></main></body></html>"""


PROJECT_REQUIREMENTS = {
    "schema_version": "resume-requirements/v1",
    "important_capabilities": [
        {
            "id": "IC-01",
            "requirement": "Validate product reliability and investigate recovery issues",
            "priority": "high",
            "coverage": "strongly_supported",
        },
        {
            "id": "IC-02",
            "requirement": "Own unsupported warranty analysis",
            "priority": "high",
            "coverage": "unsupported_gap",
        },
    ],
}


def manifest_for(evidence: dict, draft: dict, draft_bytes: bytes) -> dict:
    source_by_text = {claim["text"]: claim["id"] for claim in evidence["claims"]}
    return {
        "schema_version": "resume-provenance-manifest/v1",
        "evidence_source_sha256": evidence["source"]["sha256"],
        "draft_sha256": hashlib.sha256(draft_bytes).hexdigest(),
        "claims": [
            {
                "draft_claim_id": claim["id"],
                "draft_text": claim["text"],
                "source_ids": [source_by_text.get(claim["text"], next(iter(source_by_text.values())))],
                "rationale": "Test mapping",
            }
            for claim in draft["claims"]
        ],
    }


class ResumeQualityTests(unittest.TestCase):
    def write_html(self, directory: Path, name: str, text: str) -> Path:
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_evidence_ids_are_stable_and_profile_is_captured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_html(Path(temp), "master.html", MASTER)
            first = extract(path)
            second = extract(path)
            self.assertEqual([c["id"] for c in first["claims"]], [c["id"] for c in second["claims"]])
            self.assertTrue(any(c["kind"] == "profile" for c in first["claims"]))

    def test_unchanged_draft_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_html(Path(temp), "master.html", MASTER)
            evidence = extract(path)
            draft = extract(path)
            raw = path.read_bytes()
            report = audit(evidence, draft, manifest_for(evidence, draft, raw), raw)
            self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=2))

    def test_changed_metric_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            master_path = self.write_html(directory, "master.html", MASTER)
            draft_text = MASTER.replace("40+ defects", "400+ defects")
            draft_path = self.write_html(directory, "draft.html", draft_text)
            evidence = extract(master_path)
            draft = extract(draft_path)
            raw = draft_path.read_bytes()
            manifest = manifest_for(evidence, draft, raw)
            source_bullet = next(c["id"] for c in evidence["claims"] if "40+ defects" in c["text"])
            draft_bullet = next(c for c in draft["claims"] if "400+ defects" in c["text"])
            for item in manifest["claims"]:
                if item["draft_claim_id"] == draft_bullet["id"]:
                    item["source_ids"] = [source_bullet]
            report = audit(evidence, draft, manifest, raw)
            self.assertIn("UNSUPPORTED_METRIC", {item["code"] for item in report["errors"]})

    def test_changed_role_title_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            master_path = self.write_html(directory, "master.html", MASTER)
            draft_path = self.write_html(directory, "draft.html", MASTER.replace("QA Tester", "Senior QA Lead"))
            evidence = extract(master_path)
            draft = extract(draft_path)
            raw = draft_path.read_bytes()
            report = audit(evidence, draft, manifest_for(evidence, draft, raw), raw)
            self.assertIn("UNSUPPORTED_ROLE", {item["code"] for item in report["errors"]})

    def test_global_layout_spacing_passes(self) -> None:
        html = """<html><head><style>
        @media print {
          .entry { margin-top: 2mm; break-inside: auto; }
          ul.bullets li { margin: 0.7mm 0; }
          h2, .entry-head { break-after: avoid; }
          p, li { break-inside: auto; orphans: 2; widows: 2; }
        }
        </style></head><body></body></html>"""
        self.assertEqual(audit_layout(html)["verdict"], "PASS")

    def test_selective_layout_spacing_fails(self) -> None:
        html = """<html><head><style>
        @media print {
          .projects article:nth-of-type(n+3) { margin-top: 7mm; }
          .projects article:nth-of-type(n+3) li { line-height: 2; }
        }
        </style></head><body></body></html>"""
        report = audit_layout(html)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("SELECTIVE_PRINT_SPACING", {item["code"] for item in report["errors"]})

    def test_page_specific_spacing_fails(self) -> None:
        html = """<html><head><style>
        @media print { .page-two ul.bullets li { margin: 4mm 0; } }
        </style></head><body></body></html>"""
        report = audit_layout(html)
        self.assertIn("PAGE_SPECIFIC_SPACING", {item["code"] for item in report["errors"]})


class ProjectFitTests(unittest.TestCase):
    def build(self, directory: Path) -> tuple[dict, dict, dict, bytes]:
        path = directory / "draft.html"
        path.write_text(PROJECT_MASTER, encoding="utf-8")
        draft_bytes = path.read_bytes()
        evidence = extract(path)
        draft = extract(path)
        project_fit = create_project_fit(evidence, draft, draft_bytes)
        for project in project_fit["projects"]:
            project["selection_mode"] = "matched"
            project["fit_level"] = "direct"
            project["selection_reason"] = "Directly demonstrates the high-priority reliability validation duty."
            project["requirement_ids"] = ["IC-01"]
            for claim in project["claims"]:
                claim["fit_level"] = "direct"
                claim["requirement_ids"] = ["IC-01"]
                claim["recruiter_signal"] = "Makes reliability validation explicit in the visible project text."
        return evidence, draft, project_fit, draft_bytes

    def projects_html(self, projects: list[tuple[str, str]]) -> str:
        articles = []
        for index, (title, meta) in enumerate(projects):
            articles.append(f"""<article class="entry">
            <div class="entry-head"><div class="entry-title">{title}</div><div class="entry-meta">{meta}</div></div>
            <p class="entry-summary">Delivered verified project capability {index}.</p>
            </article>""")
        return "<!doctype html><html><body><main><section><h2>Projects</h2>" + "".join(articles) + "</section></main></body></html>"

    def fill_recent_fallbacks(self, project_fit: dict) -> None:
        for project in project_fit["projects"]:
            project["selection_mode"] = "recent_fallback"
            project["fit_level"] = "recent_fallback"
            project["selection_reason"] = "Newest unused project from the verified master resume."
            project["requirement_ids"] = []
            for claim in project["claims"]:
                claim["fit_level"] = "recent_fallback"
                claim["requirement_ids"] = []
                claim["recruiter_signal"] = "Shows the candidate's most recent verified project work."

    def test_direct_project_fit_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, draft, project_fit, draft_bytes = self.build(Path(temp))
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=2))

    def test_blank_project_fit_skeleton_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = directory / "draft.html"
            path.write_text(PROJECT_MASTER, encoding="utf-8")
            draft_bytes = path.read_bytes()
            evidence = extract(path)
            draft = extract(path)
            project_fit = create_project_fit(evidence, draft, draft_bytes)
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            codes = {item["code"] for item in report["errors"]}
            self.assertIn("PROJECT_FIT_LEVEL", codes)
            self.assertIn("SELECTION_MODE", codes)
            self.assertIn("NO_SELECTION_REASON", codes)
            self.assertIn("NO_RECRUITER_SIGNAL", codes)

    def test_weak_project_claim_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, draft, project_fit, draft_bytes = self.build(Path(temp))
            project_fit["projects"][0]["claims"][0]["fit_level"] = "weak"
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertIn("WEAK_PROJECT_CLAIM", {item["code"] for item in report["errors"]})

    def test_matched_project_must_foreground_fit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, draft, project_fit, draft_bytes = self.build(Path(temp))
            project_fit["projects"][0]["claims"][0]["fit_level"] = "adjacent"
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertIn("MATCH_NOT_FOREGROUNDED", {item["code"] for item in report["errors"]})

    def test_unsupported_requirement_mapping_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, draft, project_fit, draft_bytes = self.build(Path(temp))
            project = project_fit["projects"][0]
            project["requirement_ids"] = ["IC-02"]
            for claim in project["claims"]:
                claim["requirement_ids"] = ["IC-02"]
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertIn("UNSUPPORTED_REQUIREMENT_MAPPING", {item["code"] for item in report["errors"]})

    def test_layout_driven_selection_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, draft, project_fit, draft_bytes = self.build(Path(temp))
            project_fit["projects"][0]["selection_reason"] = "Balances page two and fills whitespace."
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertIn("LAYOUT_DRIVEN_PROJECT_SELECTION", {item["code"] for item in report["errors"]})

    def test_no_matches_uses_newest_three_projects(self) -> None:
        source_projects = [
            ("Current Platform", "2026.05 - Present"),
            ("Recent Agent", "2026.03"),
            ("Recent Analytics", "2025.12"),
            ("Older Controller", "2024.01"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            master_path = directory / "master.html"
            draft_path = directory / "draft.html"
            master_path.write_text(self.projects_html(source_projects), encoding="utf-8")
            draft_path.write_text(self.projects_html(source_projects[:3]), encoding="utf-8")
            evidence = extract(master_path)
            draft = extract(draft_path)
            draft_bytes = draft_path.read_bytes()
            project_fit = create_project_fit(evidence, draft, draft_bytes)
            self.fill_recent_fallbacks(project_fit)
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=2))
            self.assertEqual(report["recent_fallback_count"], 3)

    def test_fallback_rejects_older_project_when_newer_is_unused(self) -> None:
        source_projects = [
            ("Current Platform", "2026.05 - Present"),
            ("Recent Agent", "2026.03"),
            ("Recent Analytics", "2025.12"),
            ("Older Controller", "2024.01"),
        ]
        selected = [source_projects[0], source_projects[2], source_projects[3]]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            master_path = directory / "master.html"
            draft_path = directory / "draft.html"
            master_path.write_text(self.projects_html(source_projects), encoding="utf-8")
            draft_path.write_text(self.projects_html(selected), encoding="utf-8")
            evidence = extract(master_path)
            draft = extract(draft_path)
            draft_bytes = draft_path.read_bytes()
            project_fit = create_project_fit(evidence, draft, draft_bytes)
            self.fill_recent_fallbacks(project_fit)
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertIn("RECENT_FALLBACK_SELECTION", {item["code"] for item in report["errors"]})

    def test_one_match_is_followed_by_two_newest_unused_projects(self) -> None:
        source_projects = [
            ("Current Platform", "2026.05 - Present"),
            ("Recent Agent", "2026.03"),
            ("Recent Analytics", "2025.12"),
            ("Matched Controller", "2024.01"),
        ]
        selected = [source_projects[3], source_projects[0], source_projects[1]]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            master_path = directory / "master.html"
            draft_path = directory / "draft.html"
            master_path.write_text(self.projects_html(source_projects), encoding="utf-8")
            draft_path.write_text(self.projects_html(selected), encoding="utf-8")
            evidence = extract(master_path)
            draft = extract(draft_path)
            draft_bytes = draft_path.read_bytes()
            project_fit = create_project_fit(evidence, draft, draft_bytes)
            matched = project_fit["projects"][0]
            matched["selection_mode"] = "matched"
            matched["fit_level"] = "direct"
            matched["selection_reason"] = "Directly demonstrates the reliability validation requirement."
            matched["requirement_ids"] = ["IC-01"]
            for claim in matched["claims"]:
                claim["fit_level"] = "direct"
                claim["requirement_ids"] = ["IC-01"]
                claim["recruiter_signal"] = "Foregrounds the supported reliability match."
            fallback_fit = {"projects": project_fit["projects"][1:]}
            self.fill_recent_fallbacks(fallback_fit)
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=2))
            self.assertEqual(report["matched_project_count"], 1)
            self.assertEqual(report["recent_fallback_count"], 2)

    def test_more_than_three_projects_fails(self) -> None:
        source_projects = [(f"Validator {index}", f"202{index}.01") for index in range(3, 7)]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "draft.html"
            path.write_text(self.projects_html(source_projects), encoding="utf-8")
            evidence = extract(path)
            draft = extract(path)
            draft_bytes = path.read_bytes()
            project_fit = create_project_fit(evidence, draft, draft_bytes)
            self.fill_recent_fallbacks(project_fit)
            report = audit_project_fit(PROJECT_REQUIREMENTS, evidence, draft, project_fit, draft_bytes)
            self.assertIn("PROJECT_COUNT", {item["code"] for item in report["errors"]})


class ResumePdfTests(unittest.TestCase):
    def page_lines(self, skills_heading: str = "Technical Skills") -> list[list[tuple[int, int, str]]]:
        return [
            [
                (36, 756, skills_heading),
                (36, 734, "Python, SQL, and evidence-based API testing."),
                (36, 690, "Education"),
                (36, 668, "Example University, Bachelor of Engineering."),
                (36, 620, "Experience"),
                (36, 598, "QA Tester at Example Co, regression and integration testing."),
                (36, 500, "Projects"),
                (36, 478, "Example Project, a local validation tool."),
                (60, 40, "This project paragraph begins on the first page"),
            ],
            [
                (60, 756, "and continues naturally on the second page with the same indentation."),
                (60, 734, "The continuation preserves the original paragraph reading order."),
                (36, 680, "Additional Information"),
                (36, 658, "Supporting details from the verified master resume."),
                (36, 180, "Relevant additional information ends here."),
            ],
        ]

    def write_pdf(self, path: Path, pages: list[list[tuple[int, int, str]]]) -> None:
        writer = PdfWriter()
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        for lines in pages:
            page = writer.add_blank_page(width=612, height=792)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
            })
            operations = []
            for x, y, text in lines:
                escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                operations.append(f"BT /F1 10 Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET")
            stream = DecodedStreamObject()
            stream.set_data("\n".join(operations).encode("ascii"))
            # PDF streams must be indirect objects for both PDF readers to parse them.
            page[NameObject("/Contents")] = writer._add_object(stream)
        with path.open("wb") as output:
            writer.write(output)

    def verify_pages(self, pages: list[list[tuple[int, int, str]]], expected_pages: int = 2) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            pdf_path = Path(temp) / "resume.pdf"
            self.write_pdf(pdf_path, pages)
            return verify(pdf_path, [], ["Skills", "Education", "Experience", "Projects", "Additional Information"], 2, 40, None, expected_pages)

    def test_pdf_accepts_natural_continuation_and_both_skills_headings(self) -> None:
        for heading in ("Technical Skills", "Skills"):
            with self.subTest(heading=heading):
                report = self.verify_pages(self.page_lines(heading))
                self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=2))
                self.assertEqual(report["warnings"], [])

    def test_pdf_rejects_wrong_section_order(self) -> None:
        pages = self.page_lines()
        swaps = {"Education": "Experience", "Experience": "Education"}
        pages[0] = [(x, y, swaps.get(text, text)) for x, y, text in pages[0]]
        report = self.verify_pages(pages)
        self.assertIn("SECTION_ORDER", {item["code"] for item in report["errors"]})

    def test_pdf_requires_additional_information_when_configured(self) -> None:
        pages = self.page_lines()
        pages[1] = [(x, y, text) for x, y, text in pages[1] if text != "Additional Information"]
        report = self.verify_pages(pages)
        self.assertIn("MISSING_SECTION", {item["code"] for item in report["errors"]})

    def test_pdf_warns_about_large_gap_before_continuing_page(self) -> None:
        pages = self.page_lines()
        x, _, text = pages[0][-1]
        pages[0][-1] = (x, 400, text)
        report = self.verify_pages(pages)
        self.assertEqual(report["verdict"], "PASS", json.dumps(report, indent=2))
        self.assertIn("PREMATURE_PAGE_BREAK", {item["code"] for item in report["warnings"]})

    def test_pdf_single_page_requires_length_review_unless_expected(self) -> None:
        pages = [self.page_lines()[0][:-1] + [
            (36, 120, "Additional Information"),
            (36, 98, "Relevant supporting details from the master resume."),
        ]]
        default_report = self.verify_pages(pages)
        self.assertEqual(default_report["verdict"], "PASS")
        self.assertIn("PAGE_COUNT_PREFERENCE", {item["code"] for item in default_report["warnings"]})
        exception_report = self.verify_pages(pages, expected_pages=1)
        self.assertEqual(exception_report["verdict"], "PASS")
        self.assertNotIn("PAGE_COUNT_PREFERENCE", {item["code"] for item in exception_report["warnings"]})


if __name__ == "__main__":
    unittest.main()
