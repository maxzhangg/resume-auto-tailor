# Tailoring workflow and commands

`SKILL` is the installed skill directory, `WORKSPACE` holds private data, and `APP` is a new application directory under `WORKSPACE/output/`. Replace the angle-bracket placeholders with absolute, quoted paths. Commands use the selected Python environment.

## 1. Inputs and plan

Require a designated HTML master, an exact JD (or URL with retrievable full text), and a new output directory. Save the JD as `job-description.txt`; reject navigation, CAPTCHA, or upload-page text masquerading as a JD. Without a full JD, label any broader role-targeted draft as such and identify missing requirements rather than inventing a posting.

Copy current preferences to `APP/effective-preferences.json`. Apply explicit per-application user overrides there. Resolve automatic project count in `plan.md`, and set its effective value when using recent fallbacks. Remove unused sections from the effective section list when legitimately omitted; preserve user-selected order for retained sections. Do not modify the master or stored defaults.

```text
python <SKILL>/scripts/extract_evidence.py --html <WORKSPACE>/private/master.html --output <APP>/evidence.json
```

Compare extracted evidence with visible source text. Create `requirements.json` grouping hard requirements, important and preferred capabilities, responsibilities, domain language, and unsupported gaps. Each targetable requirement needs stable `id`, `priority` (`high|medium|low`), and `coverage` (`strongly_supported|supported|partially_supported|unsupported_gap`). Read [project-job-fit.md](project-job-fit.md).

Write `plan.md` before drafting: selected evidence IDs, requirement IDs, directness (`direct|adjacent|weak`), relevance, selection/reordering/condensation/truthful reframing, matched versus recent-fallback projects, chosen counts, section order, and any length exception. Apply experience rules by actual JD duties. Prefer supported JD-relevant skills; do not adopt a keyword solely because the employer lists it.

## 2. Draft and provenance

Copy the master to `APP/resume.html`, then edit only the copy. Preserve facts, role metadata, education, links, metrics, and scope. For matched projects, foreground the strongest supported job signal in the summary or first visible claim. Keep recent fallbacks honest and concise. Apply summary, section, language, skills, and experience preferences.

```text
python <SKILL>/scripts/create_manifest.py --evidence <APP>/evidence.json --draft <APP>/resume.html --output <APP>/manifest.json
python <SKILL>/scripts/audit_draft.py --evidence <APP>/evidence.json --draft <APP>/resume.html --manifest <APP>/manifest.json --output <APP>/provenance-report.json
```

Between these commands, fill every empty source list and rationale using [evidence-and-manifest.md](evidence-and-manifest.md). Confirm auto-mapped sources belong to the same role where required. Every number must appear in the mapped evidence. Stop on errors; fix content or genuine mappings without weakening checks. A passing structural gate does not prove semantic support.

## 3. Project fit

```text
python <SKILL>/scripts/create_project_fit.py --evidence <APP>/evidence.json --draft <APP>/resume.html --output <APP>/project-fit.json
python <SKILL>/scripts/audit_project_fit.py --requirements <APP>/requirements.json --evidence <APP>/evidence.json --draft <APP>/resume.html --project-fit <APP>/project-fit.json --preferences <APP>/effective-preferences.json --output <APP>/project-fit-report.json
```

Complete the skeleton before the audit. Map every visible project summary/bullet. Matched projects need a direct first claim and supported requirement mappings; recent fallbacks use verified recency and never imply unsupported relevance. Respect configured count/fallback policy. Run this gate with an empty mapping when Projects is omitted; the effective count should be zero. Stop on errors.

## 4. Read-only review and corrections

Use [reviewer-rubric.md](reviewer-rubric.md). Give the reviewer only the exact JD, requirements, master evidence, draft, and effective preferences. Withhold plan, manifest, project-fit mapping, and writer rationale. Use a fresh review context when available and authorized; otherwise label `independence: limited`. The reviewer reports and cannot edit. Save `review.json` with per-project assessments.

Apply only named fixes, at most two review/fix rounds. Re-run provenance and project-fit gates after semantic changes. Unresolved errors remain visible and block a ready-to-use delivery; do not silently lower the rubric. A critique-only request ends with the report and does not mutate the draft.

## 5. Layout, PDF, and delivery

Read [layout-and-pagination.md](layout-and-pagination.md). Keep natural page flow, short heading protection, uniform print spacing, and no filler.

```text
python <SKILL>/scripts/audit_layout.py --html <APP>/resume.html --output <APP>/layout-source-report.json
node <SKILL>/scripts/render_pdf.cjs <APP>/resume.html <APP>/resume.pdf <APP>/effective-preferences.json
python <SKILL>/scripts/verify_pdf.py --pdf <APP>/resume.pdf --preferences <APP>/effective-preferences.json --output <APP>/pdf-report.json --render-dir <APP>/rendered --required-text "<candidate name>"
```

The PDF checker uses configured page target/limit and section order, plus text extraction, glyph, blank-page, repeated-text, bounds, density, and page-image checks. Explicit CLI page/section/project settings override the preference file; document any override in the plan. With no preferred page target, no two-page assumption applies. Review every warning, including large premature breaks and sparse final pages; document accepted natural whitespace instead of stretching the layout.

Inspect every latest rendered PNG at full-page scale and high-resolution crops around each page transition. Check missing/clipped text, collisions, orphan headings, broken glyphs, reading order, indentation, font sizes, bullet gaps, and cross-page rhythm. An automated PASS is not visual QA. If rendering or image inspection is unavailable, report that verification is incomplete.

After any HTML change, regenerate/reconcile manifests and project mappings, update hashes, and rerun applicable audits. Semantic tag changes can alter extracted claims without changing visible text. Re-render and verify the final PDF after any HTML edit. After delivery, write new revision filenames for HTML, PDF, reports, and image directories; the renderer refuses to overwrite an existing PDF. If a screenshot disagrees, compare the precise filename, timestamp, and SHA-256 before changing layout again.

Deliver the PDF and editable HTML with concise validation results, unsupported hard requirements, review independence, and any unresolved warnings. Keep the JD, requirements, plan, preferences snapshot, evidence, mappings, review, HTML, PDF, and reports together in APP. Never include these private artifacts in the distributable skill.
