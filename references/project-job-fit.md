# Project-to-job fit contract

Project selection has two jobs: **foreground the strongest project evidence for this JD**, then **keep the section current with the newest projects when recent fallback is enabled and fewer than the configured project count matches exist**. Never turn a recent fallback into a fake match.

## Requirement records

Every requirement that resume content may target needs a stable ID and explicit priority in `requirements.json`:

```json
{
  "id": "IC-03",
  "requirement": "Validate product quality and investigate reliability issues",
  "priority": "high",
  "coverage": "strongly_supported",
  "evidence": "Verified validation claims from the candidate master"
}
```

Use `high` for must-have or repeatedly emphasized duties, `medium` for meaningful supporting capabilities, and `low` for optional differentiators. `unsupported_gap` records cannot support resume claims.

## Directness

- `direct`: the visible claim itself demonstrates the required action, object, responsibility, or result. The recruiter does not need an unstated bridge.
- `adjacent`: the claim supports a nearby capability, but the recruiter must make one reasonable inference. Adjacent claims may support a project but cannot be the project's only value.
- `weak`: the match is based mainly on a shared keyword, broad domain, technology inventory, education topic, or two or more inference steps. Omit it from a matched project's tailored content.
- `recent_fallback`: the project is retained because fewer than the configured project count matched projects exist and it is one of the newest unused projects in the master. This does not claim JD relevance.

Technology overlap alone is not direct job fit. A feature inventory such as “built React pages and APIs” is direct only when implementation is itself a prioritized duty. For product, consulting, systems, or quality roles, make the supported decision, requirement, validation, stakeholder, reliability, or result signal visible.

## Selection rules

1. Rank requirements before choosing projects.
2. Select directly matching projects first, ordered by strength of supported JD coverage and then by recency.
3. When fallback_policy is recent, fill the configured count with the newest unused master projects, capped by source availability. With matched_only, retain only direct matches; surface a count conflict instead of inventing relevance. With project_count=null, choose useful projects for content relevance and record the count in plan.md; no fixed quota applies.
4. A matched project must contain at least one direct claim. Its summary or first visible claim must foreground that match; other retained claims may be adjacent when useful and non-redundant.
5. For matched projects, remove generic stack lists, low-value domain overlap, duplicate evidence, and claims whose relevance appears only in the Writer's rationale.
6. Keep recent-fallback projects concise, current, and factual. Do not add JD keywords or requirement mappings that the visible evidence does not support.
7. Never select a project to reach a page target, reduce whitespace, balance pages, or clear a density warning. Recency is the only fallback rule.

## Visible project story

For a matched project, where evidence permits, order project content as:

1. job-relevant problem, user, or requirement;
2. candidate action, decision, validation, or tradeoff;
3. concrete artifact or method;
4. supported result, operating state, or learning.

Do not force this shape when the master lacks the facts. Instead, identify the missing project evidence that should be verified and added to the master later: users, constraints, ownership boundary, alternatives considered, success criteria, validation method, adoption, production status, or measurable outcome. Recent-fallback projects do not need artificial JD framing.

## `project-fit.json`

Generate the skeleton after the tailored draft, then fill it manually:

```json
{
  "schema_version": "resume-project-fit/v2",
  "evidence_source_sha256": "...",
  "draft_sha256": "...",
  "projects": [
    {
      "role_identity": "projects | example project | 2026 |",
      "title": "Example Project",
      "selection_mode": "matched",
      "fit_level": "direct",
      "selection_reason": "Directly demonstrates the JD's high-priority product-validation duty.",
      "requirement_ids": ["IC-03"],
      "claims": [
        {
          "draft_claim_id": "claim-projects-...",
          "draft_text": "Validated failure and recovery behavior across service boundaries.",
          "fit_level": "direct",
          "requirement_ids": ["IC-03"],
          "recruiter_signal": "Makes reliability validation and cross-service investigation explicit."
        }
      ]
    }
  ]
}
```

For a recent fallback, use `selection_mode` and `fit_level` of `recent_fallback`; requirement ID lists may be empty, and every claim must also use `recent_fallback`. Its `selection_reason` should state that it is one of the newest unused projects, not that it matches the JD.

The deterministic audit verifies completeness, IDs, master/draft binding, matched-project directness, the configured project-count policy, and whether fallback entries are actually the newest unused master projects. It cannot prove semantic fit. The read-only Reviewer must independently challenge every matched-project mapping from the visible draft text.
