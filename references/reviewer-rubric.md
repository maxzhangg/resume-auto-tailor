# Read-only reviewer rubric

Read the candidate preferences alongside the exact JD, requirements, master evidence, and draft. Return a JSON-compatible report. Do not rewrite the resume.

## Release gates

1. **Truth and scope**: every claim is supported by its cited evidence; agency, ownership, seniority, production status, and scale are not inflated.
2. **Requirement relevance**: prioritize supported hard requirements within the candidate-configured section order; unsupported gaps remain explicit outside the resume.
3. **Project job fit and fallback**: assess every retained project from the visible draft, without reading the Writer's plan or project-fit rationale. Matched projects must directly demonstrate a supported requirement, foreground the strongest match in the summary or first visible claim, and add distinct evidence. When recent fallback is enabled and fewer than the configured project count matches exist, confirm that remaining projects are the newest unused master projects and that they are presented honestly without fake JD framing. Reject any project selected for page balance, density, or filler.
4. **Specificity**: bullets name an action, object, method, and result where evidence permits. Reject vague responsibility lists.
5. **Signal density**: remove repetition, generic soft skills, keyword inventories, and low-relevance projects before shrinking typography.
6. **Human voice**: reject canned summaries, excessive superlatives, repetitive action verbs, and phrases that could describe any candidate.
7. **Recruiter scan**: title, strongest fit evidence, employers, dates, and core tools are clear in a 10-second scan.
8. **ATS safety**: one-column reading order, literal contact text, conventional headings, extractable characters, the candidate-configured section order, and no keyword stuffing. Accept `Technical Skills` as the Skills heading.
9. **Visual rhythm**: the candidate-configured page target, with any length exception justified; consistent typography, bullet spacing, entry spacing, indentation, and hierarchy. Accept readable entry/paragraph/bullet continuations across pages. Reject orphaned headings, avoidable large blank areas on page one caused by keeping whole blocks together, page-specific spacing inflation, filler, visually stretched page-two content, or a cached/stale artifact presented as the latest revision.

## Project assessment

For each visible project, report:

- whether its `selection_mode` is `matched` or `recent_fallback`;
- for a matched project, the supported requirement IDs it directly demonstrates;
- a `directness` judgment of `direct`, `adjacent`, `weak`, or `recent_fallback` based only on visible draft text and master evidence;
- whether its strongest job signal is explicit or requires recruiter inference;
- whether its evidence is distinct from the Experience section and other projects;
- for a fallback, whether it is one of the newest unused master projects;
- a match score from 0 to 5 for matched projects, or `null` for recent fallbacks, plus a bounded fix when invalid.

A matched project cannot receive 4 or 5 when its only match is a technology keyword, general engineering background, or a capability described only in the Writer's rationale. If any matched project scores below 4, `project_job_fit` cannot exceed 3 and the verdict must be `REVISE` or `REJECT`. Do not penalize an honest recent fallback merely for lacking JD fit; reject it only when a newer unused project exists, its content is weakly or falsely reframed as a match, or the configured project-count policy is violated.

## Output

```json
{
  "schema_version": "resume-review/v1",
  "independence": "independent|limited",
  "verdict": "PASS|REVISE|REJECT",
  "scores": {
    "truth_and_scope": 0,
    "requirement_relevance": 0,
    "project_job_fit": 0,
    "specificity": 0,
    "signal_density": 0,
    "human_voice": 0,
    "recruiter_scan": 0,
    "ats_safety": 0,
    "visual_rhythm": 0
  },
  "project_assessments": [
    {
      "project_identity": "project title and date",
      "selection_mode": "matched|recent_fallback",
      "match_score": 0,
      "directness": "direct|adjacent|weak|recent_fallback",
      "direct_requirement_ids": ["IC-03"],
      "signal_is_explicit": false,
      "distinct_evidence": false,
      "newest_unused_fallback": null,
      "problem": "one concrete project-fit problem or null",
      "required_fix": "bounded correction or null"
    }
  ],
  "findings": [
    {
      "severity": "error|warning|suggestion",
      "claim_id": "claim-id-or-null",
      "problem": "one concrete problem",
      "evidence": "the exact conflicting or weak text",
      "required_fix": "bounded correction; do not provide replacement prose"
    }
  ],
  "review_scope": {
    "job_description": "job-description.txt",
    "requirements": "requirements.json",
    "master_evidence": "evidence.json",
    "draft": "resume.html",
    "writer_rationale_withheld": true,
    "project_fit_mapping_withheld": true
  }
}
```

Use `null` for `match_score`, `signal_is_explicit`, and `distinct_evidence` when `selection_mode` is `recent_fallback`; use `true|false` for `newest_unused_fallback`. Score each overall dimension from 0 to 5. PASS requires no errors, every overall score at least 4, every matched-project score at least 4, valid newest-project fallbacks meeting the configured count when needed, and both rationale-withholding fields set to `true`. ATS keyword percentage, provenance validity, strong Experience evidence, or attractive pagination cannot override a project-selection failure.
