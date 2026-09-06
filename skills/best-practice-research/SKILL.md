---
name: best-practice-research
description: Use when a technical decision needs current external best practices, primary-source comparison, and a repository-specific recommendation rather than generic advice.
---

# best-practice-research

Research current external practice and translate it into a repository-specific recommendation. Prefer primary sources, separate normative requirements from common convention, and show where evidence disagrees.

## Workflow

1. State the decision, constraints, date sensitivity, and what would count as a useful answer.
2. Inspect the repository enough to identify language, platform, deployment, compatibility, and ownership constraints.
3. Search current primary sources first: official documentation, standards, specifications, source repositories, release notes, and original research.
4. Add high-quality secondary sources only to compare real-world trade-offs or fill an explicit primary-source gap.
5. Record source date/version, scope, claim supported, and applicability to this repository.
6. Compare at least two viable approaches when a meaningful alternative exists; include costs, migration risk, and operational burden.
7. Recommend one approach, explain rejected alternatives, and identify assumptions that require local validation. Stop searching when additional evidence no longer changes the feasible options, ranking, or material risks; unresolved local behavior calls for a discriminating experiment, not another generic source sweep.

## Output contract

- **Decision and constraints**
- **Current evidence** with direct citations
- **Options and trade-offs**
- **Repository fit**
- **Recommendation**
- **Validation steps and unresolved risks**

## Hard rules

- Browse for current or niche facts; do not rely on remembered versions or policies.
- Prefer primary sources for technical claims and cite the claim where used.
- Do not copy a popular pattern without testing its fit to the target repository. Stars, benchmark wins, and vendor claims are discovery signals, not evidence of local utility.
- Reuse already-verified sources within their date/version boundary. Fetch changed claims, not an entire ecosystem again; keep source findings separate from local inferences.
- Distinguish “required by a standard”, “recommended by a vendor”, and “common practice”.
- Do not turn research into code changes unless the user also authorizes implementation.

## On-demand references

- Read [source evaluation](references/source-evaluation.md) only when sources conflict, evidence is vendor-controlled, or a recommendation depends on freshness or ecosystem adoption.
