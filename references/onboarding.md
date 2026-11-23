# First-use onboarding for the coding agent

The outcome is one verified candidate-owned HTML master and one explicit preference file. Speak in the user's language. Use the files and answers already supplied, and ask only about missing information.

## 1. Locate or initialize the private workspace

Use the user's chosen directory, otherwise a `resume-workspace` directory in the current project. Run `python <SKILL>/scripts/setup_profile.py init --workspace <WORKSPACE>`. It creates `private/master.html`, `private/preferences.json`, and ignore entries for private/output data, preserving existing files. Keep private inputs and outputs out of shared archives. Ignore rules do not remove files already tracked by Git.

## 2. Ask for the master and explain the options

An opening prompt may say:

> I can tailor your resume to a job description, trace claims to your original experience, review project relevance, and check the PDF. First, point me to your complete current resume (HTML, Word, PDF, or text), or provide the content you want to use. We will save a private master and choose the layout and tailoring preferences below.

Explain the choices in a compact table or a short grouped question. Offer preserving their existing layout as a starting point; do not carry over the skill author's settings.

| Preference | What to ask / how it works |
| --- | --- |
| `language` | Resume language. Separate from the language used to chat. |
| `paper_size` | Letter or A4; the renderer uses this setting. |
| `expected_pages`, `max_pages` | Preferred length and optional hard limit. `null` means no fixed target/limit; never pad content to meet a target. |
| `section_order` | Actual visible headings in the desired order. Preserve existing sections if requested; do not require Projects or Additional Information without content. |
| `include_summary` | Include a factual Profile/Summary or start directly with another section. If true, include that heading in section_order. |
| `project_count` | Fixed count, `0` to omit projects, or `null` to let relevance determine count. A fixed count is capped by master availability. |
| `fallback_policy` | `matched_only`: only direct job matches. `recent`: after matched projects, retain newest unused projects up to the chosen count. With an automatic count, choose a concrete count in the application plan before using recent fallbacks. |
| `skill_order` | JD-relevant verified skills first, preserve original ordering, or another explicit ordering instruction. |
| `experience_rules` | Optional include/omit conditions for the user's own roles, e.g. only include a named role for customer-facing jobs. Empty means no special conditions. |

If a fixed count cannot be met under `matched_only`, surface the conflict and resolve the application count with the user; never relabel a weak match or silently enable fallback. A zero-project choice must omit Projects from the effective section list. These preferences guide the agent's writing; page count, section order, and project count/fallback also drive deterministic checkers. They do not relax the truth/provenance gates.

## 3. Import and verify the master

Preserve the original supplied file. Copy or convert its content to `private/master.html` using [template-contract.md](template-contract.md). The bundled template is a new generic scaffold, with no real employers, projects, or contact information. Delete unused entries and sections; replace every placeholder using the user's evidence.

Use the host's available document/PDF tools to read Word/PDF sources. If extraction is unavailable or the source is an image, request readable text or verified transcription. Do not guess missing facts. Compare all names, contacts, dates, titles, numbers, links, and claims against the original. Check the extracted evidence to ensure every visible claim is covered; successful parsing alone is insufficient.

The parser supports the semantic HTML contract and English canonical section headings, with content in the chosen language. If translated or custom headings are needed, explicitly adapt and test the parser mapping before using them; otherwise explain the limitation. No silent unsupported heading that hides content from provenance checks.

## 4. Confirm the user's settings and readiness

Show the proposed preference choices, the private file locations, and any conversion uncertainty. Use choices already given; do not ask the same questions twice. Set `setup_complete: true` only once the master content and choices are confirmed. Then run:

```text
python <SKILL>/scripts/setup_profile.py status --workspace <WORKSPACE>
python <SKILL>/scripts/extract_evidence.py --html <WORKSPACE>/private/master.html --output <WORKSPACE>/private/evidence-check.json
```

Resolve all status issues. Read the extracted claims and roles against the master and render a sample if conversion changed the layout. Readiness checks are structural, not proof that every fact or preference is correct. Complete setup when the files are usable and the user knows where they live. If a JD was already provided, continue directly into tailoring; otherwise explain they can provide a JD or URL next.

## Runtime setup

Use Python 3.11+ and Node.js with npm. In the installed skill directory, install Python requirements, run `npm ci` (or `npm install` if no lockfile), and `npx playwright install chromium`. Use an existing virtual environment or create `.venv` if appropriate. The PDF page-image renderer is Poppler's `pdftoppm`, which must be on PATH. Check these dependencies before generation, and resolve missing tools using the host's installation conventions and permissions. Run tests with `python -m unittest discover -s <SKILL>/tests -v`.

Use `python` below to mean the selected environment's Python executable; on Windows it may be `py -3.11`. Quote real paths containing spaces. Resolve scripts relative to the installed skill, not the user's current working directory.
