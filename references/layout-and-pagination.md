# Layout and pagination contract

Use this contract for every multi-page resume and every layout revision.

## Length and section order

Use the candidate preferences for page target, maximum, and section order. A null page target allows natural content length; it is not a two-page default. Document justified exceptions in plan.md and pass the resolved settings to the PDF checker. Preserve useful content and never add filler to meet a target.

## Natural page flow

1. Start with one global print typography and spacing system, with no manual page break added for cosmetic entry boundaries.
2. Allow sections, entries, lists, paragraphs, and individual bullets to split across pages. A paragraph may end on page two even when it began on page one.
3. Keep only short headings/title metadata with the following text. Do not apply `break-inside: avoid` or `page-break-inside: avoid` to whole entries, body paragraphs, or bullet lists, or chain `break-after: avoid` through their body content.
4. Render and inspect the bottom of page one and top of page two. If a whole block was pushed forward and left a large blank area, remove the blocking break rule or explicit marker before changing content or font sizes.
5. Retain useful secondary evidence and remove redundancy; make only small, uniform global spacing adjustments if needed. Preserve the required section order.
6. Run `audit_layout.py`, provenance audit, PDF verification, and PNG review again.

Adapt these print rules to the existing template, editing only the tailored copy:

```css
@media print {
  section, .entry, ul.bullets, p, li {
    break-inside: auto;
    page-break-inside: auto;
  }
  h2, .entry-head, .entry-subhead {
    break-after: avoid;
    page-break-after: avoid;
  }
  .entry-summary {
    break-after: auto;
    page-break-after: auto;
  }
  p, li {
    orphans: 2;
    widows: 2;
  }
}
```

Short heading protection and two-line widow/orphan control may leave a small gap; they must not keep an entire long paragraph or entry together. Do not force page two to begin with a heading.

Do not make selected entries or a selected page taller merely to move the last text downward. A density heuristic measures the bottom-most character; it does not measure visual quality.

## Forbidden density fixes

- `:nth-child(...)` or `:nth-of-type(...)` selectors that change print spacing;
- page-two-only bullet margins, line height, font size, padding, transforms, or entry gaps;
- hidden text, transparent text, filler elements, oversized empty blocks, or decorative footer text added only to move the density boundary;
- adding weak or redundant projects solely to fill space;
- shrinking page one while enlarging page two without a semantic hierarchy reason.

Natural whitespace at the end of the final page is allowed when its content remains useful. Large avoidable whitespace on page one while text continues on page two needs correction, not spacing inflation.

## Page-transition QA

- Accept page two beginning inside an entry, paragraph, or bullet; preserve reading order and continuation indentation.
- Do not strand a section or entry heading at the bottom of page one without following body text.
- Inspect the full pages side by side at the same zoom.
- Inspect a high-resolution crop spanning the last lines on page one and the first lines on page two; check that no text is missing, duplicated, or clipped at the split.
- Compare bullet-to-bullet gaps, title-to-summary gaps, entry gaps, left indents, font sizes, and rule weights.
- Confirm no entry summary or bullet becomes visually inline because of print fragmentation.
- The PDF checker warns with `PREMATURE_PAGE_BREAK` when a non-final page has more than 20% bottom whitespace. Inspect the actual cause and fix avoidable keep-together/forced-break gaps; the threshold is a diagnostic, not a target to game.
- `LOW_PAGE_DENSITY` diagnoses more than 30% bottom whitespace on the final continuation page; preserve natural final-page whitespace over visibly stretched vertical rhythm. Document any accepted warning.
- `PAGE_COUNT_PREFERENCE` flags a deviation from the configured page count. Improve relevant content selection or document the permitted exception, then verify with the appropriate expected page count.

## Cache-safe delivery

After a user has opened a PDF, never test a revision by overwriting only that filename. Write a new artifact and matching evidence paths:

```text
resume-company-role-layout-v2.pdf
pdf-report-layout-v2.json
rendered-layout-v2/page-1.png
rendered-layout-v2/page-2.png
```

Report the new filename and optionally its SHA-256. If the user's screenshot shows a different page boundary than the latest PNG, verify filename, timestamp, and hash before changing layout again.
