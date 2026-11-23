# Master HTML contract

Keep original source content in `WORKSPACE/private/`. `master.html` is both the candidate's evidence source and starting layout. The generic starter in `assets/master-template.html` shows the required structure; it is not a prefilled resume.

The extractor recognizes:

- `h2` section headings: Skills or Technical Skills, Experience, Projects, Education, Additional Information, Profile or Summary. Case is ignored. Preserve the heading text consistently in master/draft; Skills and Technical Skills are equivalent for PDF order checks, but changing them during drafting can change evidence IDs.
- `article.entry` for each role, education record, or project.
- `div.entry-title`, `div.entry-meta` (dates), and `div.entry-subhead` (organization/location). Together with section they define immutable role identity. Keep these containers as siblings or under a separate wrapper; do not nest identity containers inside each other.
- `ul.skills > li` for skills; `ul.bullets > li` for claims; `p.entry-summary` for project/role summaries; paragraphs under recognized sections for other claims.
- Literal contact text in the header and normal `a href` links.

All supported section claim text (including Education and Additional Information) is extracted. Header/contact fidelity, link fidelity, complete extraction, and semantic entailment still require comparison to the original; the provenance gate alone does not certify those. Never accept empty evidence as success. Custom sections, complex nested lists, tables, text in arbitrary divs, external CSS, or image-only content need adaptation and explicit coverage review before use. The layout-source checker examines inline style blocks, not an entire CSS/browser model.

The project recency checker understands years, numeric `YYYY.MM`, `YYYY-MM`, `YYYY/MM`, and `Present`; ties use master order. During import, preserve the actual dates while normalizing their display to a supported numeric form if recent fallback is selected. Confirm ambiguous or missing dates; never infer project recency from marketing claims or reorder projects merely to defeat a recency check.

Use a single column, normal text flow, consistent global spacing, and short heading protection. Choose paper size in preferences, not a fixed `@page size` in the template. The renderer uses the configured size and half-inch margins; edit a private template/renderer copy if a different margin design is explicitly needed. After layout changes, rerun extraction, affected audits, PDF generation, and visual QA.
