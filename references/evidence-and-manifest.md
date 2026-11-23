# Evidence and manifest contract

## Evidence library

`extract_evidence.py` assigns stable IDs to the master resume's profile, skill, experience, and project claims. IDs depend on role identity and claim text. Rebuilding an unchanged master produces the same IDs.

Treat the following fields as immutable facts:

- company, project, and institution names;
- role titles and dates;
- numbers, money, percentages, counts, durations, and GPA;
- named tools or domains when their ownership is material to a claim.

## Manifest

Each tailored claim has one manifest entry:

```json
{
  "draft_claim_id": "claim-experience-...",
  "draft_text": "Validated ...",
  "source_ids": ["claim-experience-..."],
  "rationale": "Reframes the same reconciliation work using the JD's validation language."
}
```

Use the smallest sufficient set of sources. A source from another role cannot support an experience or project bullet. Profile and skill claims may combine sources from multiple roles.

The deterministic audit proves identity, role alignment, traceability, and metric preservation. It does not prove semantic entailment; the read-only Reviewer must reject overclaiming that passes lexical checks.

Never satisfy the audit by mapping an unrelated source that happens to contain the same number.

## Separate project-fit gate

The provenance manifest answers **is this claim supported by the master?** It does not answer **does this project directly strengthen this application?** Use `project-fit.json` and `audit_project_fit.py` for the second question. Keep the two mappings separate so a valid evidence source cannot be mistaken for job relevance.

Project-fit mappings distinguish `matched` projects from `recent_fallback` projects. Matched summaries and bullets bind to stable requirement IDs and directness levels; recent fallbacks bind to the master resume and verified project recency without inventing a requirement match. The deterministic audit rejects incomplete mappings, unsupported-gap mappings, weak matched claims, non-foregrounded matches, the wrong project count, stale fallback choices, and selection justified by page or layout goals. The independent Reviewer remains responsible for checking whether each declared match is credible from the visible text.
