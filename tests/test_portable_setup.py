from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from setup_profile import initialize, status
from preferences import load_preferences
from extract_evidence import extract
from audit_draft import audit
from audit_project_fit import audit as project_audit
from create_project_fit import create
from verify_pdf import verify
from test_resume_quality import MASTER, PROJECT_REQUIREMENTS, manifest_for
import test_resume_quality as fixtures


def preferences() -> dict:
    return {
        "schema_version": "resume-preferences/v1", "setup_complete": True,
        "language": "English", "paper_size": "A4", "expected_pages": None,
        "max_pages": None, "section_order": ["Profile", "Technical Skills", "Experience"],
        "include_summary": True, "project_count": 0, "fallback_policy": "matched_only",
        "skill_order": "Match the JD", "experience_rules": [],
    }


class PortableSetupTests(unittest.TestCase):
    def test_first_run_is_not_ready_and_reinitialization_preserves_user_files(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.assertEqual(len(initialize(workspace)), 2)
            self.assertFalse(status(workspace)["ready"])
            master = workspace / "private/master.html"
            prefs = workspace / "private/preferences.json"
            master.write_text(MASTER, encoding="utf-8")
            prefs.write_text(json.dumps(preferences()), encoding="utf-8")
            before = (master.read_bytes(), prefs.read_bytes(), (workspace / ".gitignore").read_bytes())
            self.assertEqual(initialize(workspace), [])
            self.assertEqual(before, (master.read_bytes(), prefs.read_bytes(), (workspace / ".gitignore").read_bytes()))
            self.assertTrue(status(workspace)["ready"], status(workspace))

    def test_placeholders_and_missing_configured_sections_block_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            initialize(workspace)
            (workspace / "private/preferences.json").write_text(json.dumps(preferences()), encoding="utf-8")
            report = status(workspace)
            self.assertFalse(report["ready"])
            self.assertTrue(any("placeholder" in issue for issue in report["issues"]))
            self.assertTrue(any("absent" in issue for issue in report["issues"]))

    def test_invalid_counts_do_not_silently_use_old_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preferences.json"
            for key, value in [("project_count", -1), ("max_pages", 0), ("expected_pages", True)]:
                with self.subTest(key=key):
                    prefs = preferences()
                    prefs[key] = value
                    path.write_text(json.dumps(prefs), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_preferences(path)

    def test_additional_and_education_claims_are_audited(self):
        with tempfile.TemporaryDirectory() as temp:
            master = Path(temp) / "master.html"
            draft = Path(temp) / "draft.html"
            html = MASTER + '<h2>Education</h2><p>Completed 4 research modules.</p><h2>Additional Information</h2><p class="additional">Mentored 2 students.</p>'
            master.write_text(html, encoding="utf-8")
            draft.write_text(html.replace("2 students", "20 students"), encoding="utf-8")
            evidence, result = extract(master), extract(draft)
            self.assertEqual(len(evidence["claims"]), 5)
            report = audit(evidence, result, manifest_for(evidence, result, draft.read_bytes()), draft.read_bytes())
            self.assertIn("UNSUPPORTED_METRIC", {item["code"] for item in report["errors"]})

    def test_empty_extraction_cannot_pass_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "master.html"
            path.write_text("<p>Unrecognized layout</p>", encoding="utf-8")
            evidence = extract(path)
            report = audit(evidence, evidence, manifest_for(evidence, evidence, path.read_bytes()), path.read_bytes())
            self.assertIn("NO_EXTRACTED_CLAIMS", {item["code"] for item in report["errors"]})

    def test_zero_project_preference_is_consumed_by_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            initialize(workspace)
            master = workspace / "private/master.html"
            prefs = workspace / "private/preferences.json"
            master.write_text(MASTER, encoding="utf-8")
            prefs.write_text(json.dumps(preferences()), encoding="utf-8")
            evidence = extract(master)
            mapping = create(evidence, evidence, master.read_bytes())
            for name, content in (("evidence", evidence), ("mapping", mapping), ("requirements", PROJECT_REQUIREMENTS)):
                (workspace / f"{name}.json").write_text(json.dumps(content), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPTS / "audit_project_fit.py"),
                "--requirements", str(workspace / "requirements.json"), "--evidence", str(workspace / "evidence.json"),
                "--draft", str(master), "--project-fit", str(workspace / "mapping.json"), "--preferences", str(prefs),
                "--output", str(workspace / "report.json")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads((workspace / "report.json").read_text())["target_project_count"], 0)

    def test_custom_pdf_sections_and_length_are_consumed_by_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pdf = directory / "resume.pdf"
            fixtures.ResumePdfTests().write_pdf(pdf, [[(36, 750, "Experience"), (36, 720, "Candidate verified work and enough readable supporting text.")]])
            prefs = preferences()
            prefs.update(section_order=["Experience"], expected_pages=1, max_pages=1)
            prefs_path = directory / "preferences.json"
            prefs_path.write_text(json.dumps(prefs), encoding="utf-8")
            report_path = directory / "report.json"
            result = subprocess.run([sys.executable, str(SCRIPTS / "verify_pdf.py"), "--pdf", str(pdf),
                "--preferences", str(prefs_path), "--min-chars", "40", "--output", str(report_path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(report_path.read_text())
            self.assertEqual(report["pages"], 1)
            self.assertEqual(report["warnings"], [])
            self.assertEqual(verify(pdf, [], ["Experience"], None, 40, None)["warnings"], [])

    def test_nonlegacy_project_count_and_fallback_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "master.html"
            path.write_text('<h2>Projects</h2><article class="entry"><div class="entry-title">Example</div><div class="entry-meta">2025</div><p class="entry-summary">Built a verified tool.</p></article>', encoding="utf-8")
            evidence = extract(path)
            mapping = create(evidence, evidence, path.read_bytes())
            project = mapping["projects"][0]
            project.update(selection_mode="recent_fallback", fit_level="recent_fallback", selection_reason="Newest verified source project.")
            for claim in project["claims"]:
                claim.update(fit_level="recent_fallback", recruiter_signal="Recent verified work.")
            allowed = project_audit(PROJECT_REQUIREMENTS, evidence, evidence, mapping, path.read_bytes(), 1, "recent")
            self.assertEqual(allowed["verdict"], "PASS", allowed)
            blocked = project_audit(PROJECT_REQUIREMENTS, evidence, evidence, mapping, path.read_bytes(), 1, "matched_only")
            self.assertIn("FALLBACK_DISABLED", {item["code"] for item in blocked["errors"]})


if __name__ == "__main__":
    unittest.main()
