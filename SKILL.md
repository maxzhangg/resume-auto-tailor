---
name: resume-auto-tailor
description: Set up a private resume master and tailoring preferences, tailor evidence-grounded resumes to job descriptions, critique drafts, and verify HTML/PDF provenance, project relevance, pagination, and ATS-readable text. Use for first-time resume setup, targeted resume generation, or resume quality and layout review.
---

# Resume Auto Tailor

Treat the designated master as evidence, tailored HTML as a draft, and the PDF as a separately verified artifact. The shared skill contains no candidate biography or personal preferences.

## First use and setup

On an installation/setup request or the first resume task, resolve the installed skill directory (`SKILL`) and the user's resume workspace (`WORKSPACE`). Keep candidate data in `WORKSPACE/private/`, separate from the shared skill where possible. Run:

```text
python <SKILL>/scripts/setup_profile.py status --workspace <WORKSPACE>
```

If not ready, read [onboarding.md](references/onboarding.md) and guide the user through providing their master resume and choosing preferences before tailoring. Explain the supported choices; a starter template is not evidence. Resume an incomplete setup without overwriting existing files. Installation alone cannot trigger a conversation in every host: when the host has no post-install hook, onboarding runs on the first invocation.

For a read-only critique of a supplied draft, inspect it without requiring a saved profile. State which truth/fit checks are unavailable without a master or JD. Do not manufacture a PASS for unavailable checks.

## Tailoring workflow

Read [workflow.md](references/workflow.md) for the ordered workflow, commands, artifacts, and revision rules. Load the candidate's `private/preferences.json` before planning. User instructions for the current application override stored preferences; save those overrides in the application's `effective-preferences.json`, without silently changing the saved defaults.

The core sequence is: exact JD -> master evidence -> requirements and plan -> draft -> provenance and project-fit gates -> read-only critique -> bounded corrections -> layout gate -> PDF -> text and visual verification.

Use these references at their relevant step:

- [template-contract.md](references/template-contract.md) when importing a master or extraction misses content.
- [evidence-and-manifest.md](references/evidence-and-manifest.md) when mapping claims or repairing provenance.
- [project-job-fit.md](references/project-job-fit.md) before selecting or assessing projects.
- [reviewer-rubric.md](references/reviewer-rubric.md) for the read-only critique.
- [layout-and-pagination.md](references/layout-and-pagination.md) before print CSS changes or multi-page rendering.

## Evidence and delivery rules

- Use the designated master, not a previous tailored resume, as the factual source. Preserve the master; edit a new application copy.
- Preserve roles, employers, dates, education, links, numbers, scope, and ownership. Every extracted claim needs direct source support. The JD guides emphasis and is never evidence.
- Every matched project must directly support a target requirement and make its strongest match visible in its first claim. Optional recent fallbacks must be labeled honestly and follow verified recency. Project count and fallback behavior come from preferences, never from page whitespace.
- Read-only review reports findings without editing. If a genuinely fresh review context is unavailable, record `independence: limited`. Do not describe self-review as independent.
- Page count, section order, summary inclusion, paper size, skill ordering, project count, and experience rules belong to the current user. No candidate-specific role or two-page/three-project default is built in.
- Maintain natural page flow and uniform typography. Density warnings are diagnostics, not targets to game with filler or selective spacing.
- Re-run affected gates after edits, regenerate hashes, and use new filenames for delivered revisions. Inspect the actual latest PNGs before claiming visual QA. Compare filename, timestamp, and SHA-256 if a reported screenshot differs.
- Deliver files and reports locally. Uploading, submitting, or sending them requires a user request for that action.
