from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SPACING_PROPERTIES = {
    "font-size",
    "height",
    "letter-spacing",
    "line-height",
    "margin",
    "margin-block",
    "margin-block-end",
    "margin-block-start",
    "margin-bottom",
    "margin-top",
    "max-height",
    "min-height",
    "padding",
    "padding-block",
    "padding-block-end",
    "padding-block-start",
    "padding-bottom",
    "padding-top",
    "top",
    "bottom",
    "transform",
}


def audit_layout(html_text: str) -> dict:
    errors: list[dict[str, str]] = []
    style_blocks = re.findall(r"<style\b[^>]*>(.*?)</style>", html_text, flags=re.IGNORECASE | re.DOTALL)

    for style in style_blocks:
        for selector_text, declaration_text in re.findall(r"([^{}]+)\{([^{}]*)\}", style, flags=re.DOTALL):
            selector = " ".join(selector_text.split())
            properties = {
                match.group(1).casefold()
                for match in re.finditer(r"([a-zA-Z-]+)\s*:", declaration_text)
            }
            spacing = sorted(properties & SPACING_PROPERTIES)
            if not spacing:
                continue

            lowered = selector.casefold()
            if ":nth-child(" in lowered or ":nth-of-type(" in lowered:
                errors.append(
                    {
                        "code": "SELECTIVE_PRINT_SPACING",
                        "selector": selector,
                        "message": f"Structural selector changes spacing properties: {', '.join(spacing)}",
                    }
                )

            page_specific = any(token in lowered for token in ("page-2", "page-two", "second-page", "[data-page="))
            if page_specific:
                errors.append(
                    {
                        "code": "PAGE_SPECIFIC_SPACING",
                        "selector": selector,
                        "message": f"Page-specific selector changes spacing properties: {', '.join(spacing)}",
                    }
                )

            filler = any(token in lowered for token in (".filler", ".density-spacer", ".page-spacer"))
            if filler:
                errors.append(
                    {
                        "code": "LAYOUT_FILLER",
                        "selector": selector,
                        "message": f"Filler selector changes layout properties: {', '.join(spacing)}",
                    }
                )

    return {
        "schema_version": "resume-layout-source-report/v1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reject selective spacing and filler CSS in a resume draft.")
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = audit_layout(args.html.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["verdict"] == "PASS", "errors": len(report["errors"]), "output": str(args.output)}))
    raise SystemExit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
