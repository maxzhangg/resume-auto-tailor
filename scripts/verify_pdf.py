#!/usr/bin/env python3
"""Verify ATS-readable PDF text and optionally render pages for visual QA."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path


from preferences import load_preferences

DEFAULT_REQUIRED_SECTIONS: list[str] = []


def normalize_heading(text: str) -> str:
    heading = " ".join(text.split()).casefold()
    return "technical skills" if heading == "skills" else heading


def resolve_pdftoppm() -> str | None:
    discovered = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
    if discovered is None:
        return None
    path = Path(discovered)
    if path.suffix.casefold() not in {".cmd", ".bat"}:
        return str(path)
    candidates = []
    if len(path.parents) >= 3:
        candidates.append(path.parents[2] / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe")
    if len(path.parents) >= 2:
        candidates.append(path.parent.parent / "Library" / "bin" / "pdftoppm.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return str(path)


def verify(
    pdf_path: Path,
    required_text: list[str],
    required_sections: list[str] | None,
    max_pages: int | None,
    min_chars: int,
    render_dir: Path | None,
    expected_pages: int | None = None,
) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    rendered: list[str] = []
    try:
        import pdfplumber
        from pypdf import PdfReader
    except ImportError as exc:
        return {"schema_version": "resume-pdf-report/v1", "verdict": "FAIL", "errors": [{"code": "DEPENDENCY", "message": str(exc)}], "warnings": [], "rendered_pages": []}

    reader = PdfReader(str(pdf_path))
    pages = len(reader.pages)
    if pages == 0:
        errors.append({"code": "NO_PAGES", "message": "PDF has no pages"})
    if max_pages is not None and pages > max_pages:
        errors.append({"code": "PAGE_LIMIT", "message": f"PDF has {pages} pages; maximum is {max_pages}"})
    if expected_pages is not None and pages != expected_pages:
        warnings.append({"code": "PAGE_COUNT_PREFERENCE", "message": f"PDF has {pages} pages; expected {expected_pages}. Review relevant content and document any length exception."})

    page_texts = [(page.extract_text() or "") for page in reader.pages]
    full_text = "\n".join(page_texts)
    if len(full_text.strip()) < min_chars:
        errors.append({"code": "TEXT_TOO_SHORT", "message": f"Extracted only {len(full_text.strip())} characters"})
    if "\ufffd" in full_text or "�" in full_text:
        errors.append({"code": "BROKEN_GLYPH", "message": "Extracted text contains replacement glyphs"})
    for value in required_text:
        if value.casefold() not in full_text.casefold():
            errors.append({"code": "MISSING_REQUIRED_TEXT", "message": f"Required text not found: {value}"})

    if not required_sections:
        warnings.append({"code": "SECTION_CHECK_NOT_CONFIGURED", "message": "Pass the candidate section order to check missing headings and reading order"})

    heading_lines = [normalize_heading(line) for line in full_text.splitlines()]
    positions = []
    for section in DEFAULT_REQUIRED_SECTIONS if required_sections is None else required_sections:
        target = normalize_heading(section)
        position = next((index for index, line in enumerate(heading_lines) if line == target), -1)
        if position == -1:
            errors.append({"code": "MISSING_SECTION", "message": f"Required section not found: {section}"})
        positions.append(position)
    present_positions = [position for position in positions if position >= 0]
    if present_positions != sorted(present_positions):
        errors.append({"code": "SECTION_ORDER", "message": "Required sections are not in the expected reading order"})

    for index, text in enumerate(page_texts, start=1):
        if len(text.strip()) < 40:
            errors.append({"code": "BLANK_PAGE", "message": f"Page {index} has almost no extractable text"})

    normalized_lines = [" ".join(line.split()).casefold() for line in full_text.splitlines() if len(" ".join(line.split())) >= 24]
    repeats = [line for line, count in Counter(normalized_lines).items() if count >= 3]
    if repeats:
        warnings.append({"code": "REPEATED_LINES", "message": f"Found {len(repeats)} long lines repeated three or more times"})

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                edge_chars = [char for char in page.chars if char["x0"] < 3 or char["x1"] > page.width - 3 or char["top"] < 3 or char["bottom"] > page.height - 3]
                if edge_chars:
                    warnings.append({"code": "EDGE_TEXT", "message": f"Page {page_number} has {len(edge_chars)} characters within 3pt of a page edge"})
                visible_chars = [char for char in page.chars if char.get("text", "").strip()]
                if visible_chars:
                    # Indentation at the page start can be a valid paragraph/bullet continuation.
                    bottom_blank_ratio = max(0.0, (page.height - max(char["bottom"] for char in visible_chars)) / page.height)
                    if page_number < pages and bottom_blank_ratio > 0.20:
                        warnings.append({"code": "PREMATURE_PAGE_BREAK", "message": f"Page {page_number} leaves {bottom_blank_ratio:.0%} bottom whitespace while content continues. Check for forced breaks or whole-block keep-together rules."})
                    elif page_number == pages and page_number > 1 and bottom_blank_ratio > 0.30:
                        warnings.append({"code": "LOW_PAGE_DENSITY", "message": f"Page {page_number} leaves {bottom_blank_ratio:.0%} of the page empty"})
    except Exception as exc:  # text extraction remains authoritative for the automated gate
        warnings.append({"code": "LAYOUT_SCAN", "message": f"Could not inspect character bounds: {exc}"})

    if render_dir is not None:
        renderer = resolve_pdftoppm()
        if renderer is None:
            errors.append({"code": "NO_RENDERER", "message": "pdftoppm is not available for mandatory visual QA"})
        else:
            render_dir.mkdir(parents=True, exist_ok=True)
            prefix = render_dir / "page"
            command = [renderer, "-png", "-r", "144", str(pdf_path), str(prefix)]
            if Path(renderer).suffix.casefold() in {".cmd", ".bat"}:
                command = ["cmd.exe", "/d", "/c", *command]
            completed = subprocess.run(command, capture_output=True, text=True)
            if completed.returncode != 0:
                errors.append({"code": "RENDER_FAILED", "message": completed.stderr.strip() or "pdftoppm failed"})
            else:
                rendered = [str(path.resolve()) for path in sorted(render_dir.glob("page-*.png"))]
                if len(rendered) != pages:
                    errors.append({"code": "RENDER_COUNT", "message": f"Rendered {len(rendered)} images for {pages} PDF pages"})

    return {
        "schema_version": "resume-pdf-report/v1",
        "verdict": "PASS" if not errors else "FAIL",
        "pdf": str(pdf_path.resolve()),
        "pages": pages,
        "expected_pages": expected_pages,
        "text_characters": len(full_text.strip()),
        "errors": errors,
        "warnings": warnings,
        "rendered_pages": rendered,
    }


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--pdf", required=True, type=Path)
    argp.add_argument("--output", required=True, type=Path)
    argp.add_argument("--required-text", action="append", default=[])
    argp.add_argument("--required-section", action="append", help="Override configured section order; repeat for each heading")
    argp.add_argument("--expected-pages", type=int, help="Override preferred page count")
    argp.add_argument("--preferences", type=Path)
    argp.add_argument("--max-pages", type=int)
    argp.add_argument("--min-chars", type=int, default=500)
    argp.add_argument("--render-dir", type=Path)
    args = argp.parse_args()
    prefs = load_preferences(args.preferences) if args.preferences else {}
    expected = args.expected_pages if args.expected_pages is not None else prefs.get("expected_pages")
    maximum = args.max_pages if args.max_pages is not None else prefs.get("max_pages")
    sections = args.required_section if args.required_section is not None else prefs.get("section_order")
    if any(value is not None and value < 1 for value in (expected, maximum)):
        argp.error("Page counts must be positive")
    report = verify(args.pdf, args.required_text, sections, maximum, args.min_chars, args.render_dir, expected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["verdict"] == "PASS", "pages": report.get("pages"), "errors": len(report["errors"]), "output": str(args.output.resolve())}))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
